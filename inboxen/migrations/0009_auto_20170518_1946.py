# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-05-18 19:46
from __future__ import unicode_literals

from django.db import migrations


def calc_running_total(apps, schema_editor):
    Statistic = apps.get_model("inboxen", "Statistic")
    total = 0
    last_sum = 0
    stats = Statistic.objects.order_by("date")
    for obj in stats:
        current = obj.emails.get("email_count__sum", 0)
        diff = current - last_sum
        diff = max(diff, 0)
        total += diff
        last_sum = current

    try:
        latest_stat = Statistic.objects.latest("date")
        latest_stat.emails["running_total"] = total
        latest_stat.save()
    except Statistic.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('inboxen', '0008_auto_20161018_1137'),
    ]

    operations = [
        migrations.RunPython(calc_running_total, reverse_code=lambda x, y: None),
    ]
