# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-05-19 18:11
from __future__ import unicode_literals

from django.db import migrations


def migrate_from_bitfield(apps, schema_editor):
    UserProfile = apps.get_model("inboxen.UserProfile")
    for profile in UserProfile.objects.all():
        profile.prefer_html_email = profile.flags.prefer_html_email
        profile.unified_has_new_messages = profile.flags.unified_has_new_messages
        if profile.flags.ask_images:
            profile.display_images = 0
        elif profile.flags.display_images:
            profile.display_images = 1
        else:
            profile.display_images = 2

        profile.save()

    Liberation = apps.get_model("inboxen.Liberation")
    for liberation in Liberation.objects.all():
        liberation.running = liberation.flags.running
        liberation.errored = liberation.flags.errored
        liberation.save()

    Inbox = apps.get_model("inboxen.Inbox")
    for inbox in Inbox.objects.all():
        inbox.deleted = inbox.flags.deleted
        inbox.new = inbox.flags.new
        inbox.exclude_from_unified = inbox.flags.exclude_from_unified
        inbox.disabled = inbox.flags.disabled
        inbox.pinned = inbox.flags.pinned
        inbox.save()

    Email = apps.get_model("inboxen.Email")
    for email in Email.objects.all():
        email.deleted = email.flags.deleted
        email.read = email.flags.read
        email.seen = email.flags.seen
        email.important = email.flags.important
        email.view_all_headers = email.flags.view_all_headers
        email.save()


class Migration(migrations.Migration):

    dependencies = [
        ('inboxen', '0017_userprofile_display_images'),
    ]

    operations = [
        migrations.RunPython(migrate_from_bitfield, reverse_code=migrations.RunPython.noop),
    ]
