# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-14 16:14
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    replaces = [('cms', '0001_initial'), ('cms', '0002_auto_20170215_2100'), ('cms', '0003_helpindex_description'), ('cms', '0004_auto_20170218_2137'), ('cms', '0005_auto_20170226_2309'), ('cms', '0006_peoplepage_intro_paragraph'), ('cms', '0006_setup_helpsite'), ('cms', '0007_auto_20170916_1722'), ('cms', '0008_auto_20170916_2048')]

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='HelpBasePage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('live', models.BooleanField(default=False)),
                ('in_menu', models.BooleanField(default=False)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('lft', models.PositiveIntegerField(db_index=True, editable=False)),
                ('rght', models.PositiveIntegerField(db_index=True, editable=False)),
                ('tree_id', models.PositiveIntegerField(db_index=True, editable=False)),
                ('level', models.PositiveIntegerField(db_index=True, editable=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('file', models.ImageField(height_field=b'height', upload_to='', width_field=b'width')),
                ('width', models.IntegerField(editable=False)),
                ('height', models.IntegerField(editable=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('collection', models.CharField(max_length=255, unique=True)),
                ('uploaded_by_user', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cms_images', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PersonInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ordinal', models.IntegerField(blank=True, editable=False, null=True)),
                ('name', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('image', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='cms.Image')),
            ],
            options={
                'ordering': ['ordinal'],
            },
        ),
        migrations.CreateModel(
            name='AppPage',
            fields=[
                ('helpbasepage_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='cms.HelpBasePage')),
                ('app', models.CharField(choices=[(b'tickets.urls', b'Tickets')], max_length=255, unique=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.helpbasepage',),
        ),
        migrations.CreateModel(
            name='HelpIndex',
            fields=[
                ('helpbasepage_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='cms.HelpBasePage')),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.helpbasepage',),
        ),
        migrations.CreateModel(
            name='HelpPage',
            fields=[
                ('helpbasepage_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='cms.HelpBasePage')),
                ('body', models.TextField()),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.helpbasepage',),
        ),
        migrations.CreateModel(
            name='PeoplePage',
            fields=[
                ('helpbasepage_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='cms.HelpBasePage')),
                ('intro_paragraph', models.TextField(blank=True, help_text=b'Text at the top of the page')),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.helpbasepage',),
        ),
        migrations.AddField(
            model_name='helpbasepage',
            name='content_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cms_pages', to='contenttypes.ContentType'),
        ),
        migrations.AddField(
            model_name='helpbasepage',
            name='parent',
            field=mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='cms.HelpBasePage'),
        ),
        migrations.AddField(
            model_name='personinfo',
            name='page',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='people', to='cms.PeoplePage'),
        ),
    ]
