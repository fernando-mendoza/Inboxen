##
#    Copyright (C) 2014 Jessica Tallon & Matt Molyneaux
#
#    This file is part of Inboxen.
#
#    Inboxen is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Inboxen is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with Inboxen.  If not, see <http://www.gnu.org/licenses/>.
##

from datetime import datetime, timedelta
from unittest import mock
import itertools

from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import override_settings
from django.utils import timezone

from inboxen import models, tasks
from inboxen.test import InboxenTestCase
from inboxen.tests import factories


class StatsTestCase(InboxenTestCase):
    def test_no_exceptions(self):
        tasks.statistics.delay()

        # run a second time, make sure fetching last stat doesn't cause errors
        tasks.statistics.delay()

    def test_all_zeroes(self):
        tasks.statistics.delay()
        stats = models.Statistic.objects.get()
        for key, value in stats.users.items():
            if key in ["oldest_user_joined"]:
                continue
            self.assertEqual(value, 0, key)

        for key, value in stats.inboxes.items():
            self.assertEqual(value, 0, key)

        for key, value in stats.emails.items():
            self.assertEqual(value, 0, key)

    def test_counts(self):
        # test all the counting is done correctly
        domain = factories.DomainFactory()

        # user 1
        user1 = factories.UserFactory()
        inbox11 = factories.InboxFactory(domain=domain, user=user1)
        inbox12 = factories.InboxFactory(domain=domain, user=user1)
        factories.EmailFactory.create_batch(2, inbox=inbox11)
        factories.EmailFactory.create_batch(2, inbox=inbox12)

        # user 2
        user2 = factories.UserFactory()
        inbox21 = factories.InboxFactory(domain=domain, user=user2)
        inbox22 = factories.InboxFactory(domain=domain, user=user2)
        factories.EmailFactory.create_batch(2, inbox=inbox21)
        factories.EmailFactory.create_batch(2, inbox=inbox22)

        # user 3
        factories.UserFactory()

        tasks.statistics.delay()
        stats = models.Statistic.objects.get()

        self.assertEqual(stats.users["count"], 3)
        self.assertEqual(stats.users["new"], 3)
        self.assertEqual(stats.users["with_inboxes"], 2)

        self.assertEqual(stats.inboxes["inbox_count__sum"], 4)
        self.assertEqual(stats.inboxes["inbox_count__max"], 2)
        self.assertEqual(stats.inboxes["inbox_count__min"], 0)
        self.assertEqual(stats.inboxes["inbox_count__avg"], 4.0/3)

        self.assertEqual(stats.emails["email_count__sum"], 8)
        self.assertEqual(stats.emails["email_count__max"], 2)
        self.assertEqual(stats.emails["email_count__min"], 2)
        self.assertEqual(stats.emails["email_count__avg"], 2)

    def test_running_total(self):
        tasks.statistics.delay()
        stats = models.Statistic.objects.get()
        self.assertEqual(stats.emails["email_count__sum"], 0)
        self.assertEqual(stats.emails["running_total"], 0)

        stats.delete()

        factories.InboxFactory()
        factories.EmailFactory.create_batch(2)

        # first count
        tasks.statistics.delay()
        stats = models.Statistic.objects.get()
        self.assertEqual(stats.emails["email_count__sum"], 2)
        self.assertEqual(stats.emails["running_total"], 2)

        # running total should not have gone down
        models.Email.objects.first().delete()
        tasks.statistics.delay()
        stats = models.Statistic.objects.latest("date")
        self.assertEqual(stats.emails["email_count__sum"], 1)
        self.assertEqual(stats.emails["running_total"], 2)

        # running total should now increase
        factories.EmailFactory()
        tasks.statistics.delay()
        stats = models.Statistic.objects.latest("date")
        self.assertEqual(stats.emails["email_count__sum"], 2)
        self.assertEqual(stats.emails["running_total"], 3)


class CleanSessionsTestCase(InboxenTestCase):
    def test_sessions_deleted(self):
        Session.objects.create(
            session_key="1234",
            session_data="{}",
            expire_date=timezone.now() - timedelta(1),
        )
        self.assertEqual(Session.objects.count(), 1)
        tasks.clean_expired_session.delay()
        self.assertEqual(Session.objects.count(), 0)


class FlagTestCase(InboxenTestCase):
    """Test flag tasks"""
    # only testing that it doesn't raise an exception atm
    # TODO: actually test
    def setUp(self):
        super(FlagTestCase, self).setUp()
        self.user = factories.UserFactory()
        self.inboxes = [
            factories.InboxFactory(user=self.user),
            factories.InboxFactory(user=self.user, new=True),
        ]
        self.emails = factories.EmailFactory.create_batch(10, inbox=self.inboxes[0])
        self.emails.extend(factories.EmailFactory.create_batch(10, inbox=self.inboxes[1]))

    def test_flags_from_unified(self):
        tasks.deal_with_flags.delay([email.id for email in self.emails], user_id=self.user.id)

    def test_flags_from_single_inbox(self):
        tasks.deal_with_flags.delay(
            [email.id for email in self.emails],
            user_id=self.user.id,
            inbox_id=self.inboxes[0].id,
        )


class DeleteTestCase(InboxenTestCase):
    def setUp(self):
        self.user = factories.UserFactory()

    def test_delete_orphans(self):
        models.Body.objects.get_or_create(data=b"this is a test")
        models.HeaderName.objects.create(name="bluhbluh")
        models.HeaderData.objects.create(data="bluhbluh", hashed="fakehash")
        tasks.clean_orphan_models.delay()

        self.assertEqual(models.Body.objects.count(), 0)
        self.assertEqual(models.HeaderData.objects.count(), 0)
        self.assertEqual(models.HeaderName.objects.count(), 0)

    def test_delete_inboxen_item(self):
        email = factories.EmailFactory(inbox__user=self.user)
        tasks.delete_inboxen_item.delay("email", email.id)

        with self.assertRaises(models.Email.DoesNotExist):
            models.Email.objects.get(id=email.id)

        # we can send off the same task, but it won't error if there's no object
        tasks.delete_inboxen_item.delay("email", email.id)

        # test with an empty list
        tasks.delete_inboxen_item.chunks([], 500)()

    @mock.patch("inboxen.tasks._create_task_queryset")
    def test_batch_delete_items_calls_create_task_queryset(self, mock_qs):
        tasks.batch_delete_items("email", args=[12, 14])
        self.assertEqual(mock_qs.call_count, 1)
        self.assertEqual(mock_qs.call_args, (("email", [12, 14], None, None, None), {}))

        tasks.batch_delete_items("email", kwargs={"a": "b"})
        self.assertEqual(mock_qs.call_count, 2)
        self.assertEqual(mock_qs.call_args, (("email", None, {"a": "b"}, None, None), {}))

        tasks.batch_delete_items("email", args=[1, 2], kwargs={"a": "b"}, skip_items=2, limit_items=8)
        self.assertEqual(mock_qs.call_count, 3)
        self.assertEqual(mock_qs.call_args, (("email", [1, 2], {"a": "b"}, 2, 8), {}))

        with mock.patch("inboxen.tasks.delete_inboxen_item") as mock_delete_task:
            result = tasks.batch_delete_items("email")
            self.assertEqual(mock_delete_task.chunks.call_count, 0)
            self.assertEqual(result, None)

            mock_qs.return_value.iterator.return_value = [mock.Mock(pk=1), mock.Mock(pk=2)]
            result = tasks.batch_delete_items("email")
            self.assertEqual(mock_delete_task.chunks.call_count, 1)
            self.assertEqual(mock_delete_task.chunks.call_args, ((([("email", 1), ("email", 2)]), 500), {}))
            self.assertNotEqual(result, None)

    @mock.patch("inboxen.tasks._create_task_queryset")
    def test_batch_mark_as_deleted_calls_update(self, mock_qs):
        # TOOD? fix this mess and just generate some objects to test against
        tasks.batch_mark_as_deleted("email")
        self.assertEqual(mock_qs.call_count, 1)
        self.assertEqual(mock_qs.call_args, (("email", None, None, None, None), {}))
        self.assertEqual(mock_qs.return_value.model.objects.filter.call_args, ((), {"pk__in": mock_qs.return_value}))
        self.assertEqual(mock_qs.return_value.model.objects.filter.return_value.update.call_count, 1)
        self.assertEqual(mock_qs.return_value.model.objects.filter.return_value.update.call_args, ((), {"deleted": True}))

    def test_batch_mark_as_deleted_does_subquery(self):
        # this would error if it tries to do a limit and an update
        tasks.batch_mark_as_deleted("email", kwargs={"pk": 12}, skip_items=1, limit_items=2)

    def test_create_task_queryset(self):
        factories.EmailFactory.create_batch(5)
        emails = list(models.Email.objects.values_list("pk", flat=True))

        result_qs = tasks._create_task_queryset("email", kwargs={"pk__isnull": False})
        self.assertEqual(list(result_qs.values_list("pk", flat=True)), emails)

        result_qs = tasks._create_task_queryset("email", kwargs={"pk__isnull": False}, skip_items=2)
        self.assertEqual(list(result_qs.values_list("pk", flat=True)), emails[2:])

        result_qs = tasks._create_task_queryset("email", kwargs={"pk__isnull": False}, limit_items=3)
        self.assertEqual(list(result_qs.values_list("pk", flat=True)), emails[:3])

        result_qs = tasks._create_task_queryset("email", kwargs={"pk__isnull": False}, skip_items=1, limit_items=2)
        self.assertEqual(list(result_qs.values_list("pk", flat=True)), emails[1:][:2])

    def test_create_task_queryset_exception(self):
        with self.assertRaises(Exception):
            tasks._create_task_queryset("email")


class AutoDeleteEmailsTaskTestCase(InboxenTestCase):
    def test_task_empty(self):
        tasks.auto_delete_emails.delay()

    def test_task_no_valid_users(self):
        factories.EmailFactory.create_batch(5)
        tasks.auto_delete_emails.delay()
        self.assertEqual(models.Email.objects.count(), 5)

    @mock.patch("inboxen.tasks.batch_delete_items")
    @mock.patch("inboxen.tasks.timezone.now")
    def test_batch_delete_call(self, now_mock, task_mock):
        now_mock.return_value = datetime.utcnow()
        tasks.auto_delete_emails()

        self.assertEqual(task_mock.delay.call_count, 1)
        self.assertEqual(task_mock.delay.call_args, (
            ("email",),
            {"kwargs": {"inbox__user__inboxenprofile__auto_delete": True, "important": False,
                        "received_date__lt": now_mock.return_value - timedelta(days=30)}},
        ))

    def test_task(self):
        params = [
            [True, False],  # important
            [True, False],  # read
            [True, False],  # auto-delete
            [
                # received_date
                timedelta(days=settings.INBOX_AUTO_DELETE_TIME - 1),
                timedelta(days=settings.INBOX_AUTO_DELETE_TIME),
                timedelta(days=settings.INBOX_AUTO_DELETE_TIME + 1),
            ],
        ]

        now = timezone.now()

        for args in itertools.product(*params):
            email = factories.EmailFactory(important=args[0], read=args[1], received_date=now - args[3],
                                           inbox__user=factories.UserFactory())
            email.inbox.user.inboxenprofile.auto_delete = args[2]
            email.inbox.user.inboxenprofile.save()

        self.assertEqual(models.Email.objects.count(), 24)

        tasks.auto_delete_emails.delay()

        # 2/3 of emails will be old enough
        # 1/2 not marked import
        # 1/2 users have auto-deleted enabled
        # therefore 1/6 emails can be deleted
        self.assertEqual(models.Email.objects.count(), 20)


class CalculateQuotaTaskTestCase(InboxenTestCase):
    def test_task_empty(self):
        tasks.calculate_quota.delay()

    @mock.patch("inboxen.tasks.calculate_user_quota")
    @mock.patch("inboxen.tasks.task_group_skew")
    def test_skip_subtask_generation(self, skew_mock, task_mock):
        # check default value
        self.assertEqual(settings.PER_USER_EMAIL_QUOTA, 0)
        tasks.calculate_quota.delay()
        # tasks should be skipped
        self.assertEqual(task_mock.chunks.call_count, 0)

        with override_settings(PER_USER_EMAIL_QUOTA=10):
            # if there are no suers, skip skewing the group
            task_mock.chunks.return_value.group.return_value = []
            tasks.calculate_quota.delay()
            self.assertEqual(task_mock.chunks.call_count, 1)
            self.assertEqual(task_mock.chunks.return_value.group.call_count, 1)
            self.assertEqual(skew_mock.call_count, 0)

    @override_settings(PER_USER_EMAIL_QUOTA=10)
    def test_full_run(self):
        # create users and emails, check user profiles
        user1 = factories.UserFactory()
        user2 = factories.UserFactory()

        user1_email_count = 11
        user2_email_count = 4
        other_users_email_count = 9

        factories.EmailFactory.create_batch(user1_email_count, inbox__user=user1)
        factories.EmailFactory.create_batch(user2_email_count, inbox__user=user2)
        factories.EmailFactory.create_batch(other_users_email_count)

        models.Email.objects.update(seen=True)
        models.Inbox.objects.update(new=True)
        user1.inboxenprofile.unified_has_new_messages = True
        user1.inboxenprofile.save()
        user2.inboxenprofile.unified_has_new_messages = True
        user2.inboxenprofile.save()

        tasks.calculate_quota.delay()

        user1.inboxenprofile.refresh_from_db()
        user2.inboxenprofile.refresh_from_db()
        self.assertEqual(user1.inboxenprofile.quota_percent_usage, 100)
        self.assertEqual(user1.inboxenprofile.unified_has_new_messages, True)
        self.assertEqual(user2.inboxenprofile.quota_percent_usage, 40)
        self.assertEqual(user2.inboxenprofile.unified_has_new_messages, True)
        self.assertEqual(models.Email.objects.filter(inbox__user=user1).count(), user1_email_count)
        self.assertEqual(models.Email.objects.filter(inbox__user=user2).count(), user2_email_count)
        # flags only get changed if there was deleting
        self.assertEqual(models.Inbox.objects.filter(new=True).count(), user1_email_count + user2_email_count + other_users_email_count)

        # now enable deleting
        models.UserProfile.objects.update(quota_options=models.UserProfile.DELETE_MAIL)
        tasks.calculate_quota.delay()

        user1.inboxenprofile.refresh_from_db()
        user2.inboxenprofile.refresh_from_db()
        self.assertEqual(user1.inboxenprofile.quota_percent_usage, 100)
        self.assertEqual(user1.inboxenprofile.unified_has_new_messages, False)
        self.assertEqual(user2.inboxenprofile.quota_percent_usage, 40)
        self.assertEqual(user2.inboxenprofile.unified_has_new_messages, True)
        self.assertEqual(models.Email.objects.filter(inbox__user=user1).count(), user1_email_count - 1)
        self.assertEqual(models.Email.objects.filter(inbox__user=user2).count(), user2_email_count)
        self.assertEqual(models.Inbox.objects.count(), user1_email_count + user2_email_count + other_users_email_count)
        self.assertEqual(models.Inbox.objects.filter(new=True).count(),
                         user1_email_count + user2_email_count + other_users_email_count - 1)

    def test_user_deleted(self):
        # check that calculate_user_quota can cope with a deleted user
        user_id = "this can never be a user id, (hopefully)"
        tasks.calculate_user_quota(user_id)
