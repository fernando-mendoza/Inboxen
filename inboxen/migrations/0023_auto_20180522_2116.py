# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-05-22 21:16
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inboxen', '0022_merge_20180607_2024'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='email',
            name='flags',
        ),
        migrations.RemoveField(
            model_name='inbox',
            name='flags',
        ),
        migrations.RemoveField(
            model_name='liberation',
            name='flags',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='flags',
        ),
    ]
