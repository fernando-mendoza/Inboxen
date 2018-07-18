# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-05-13 11:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inboxen', '0016_auto_20180513_1128'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='display_images',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Always ask to display images'), (1, 'Always display images'), (2, 'Never display images')], default=0),
        ),
    ]