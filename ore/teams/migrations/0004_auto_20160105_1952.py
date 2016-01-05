# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-05 19:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0003_auto_20160105_0431'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationteam',
            name='description',
            field=models.CharField(blank=True, default='', max_length=140, verbose_name='Description (optional)'),
        ),
        migrations.AddField(
            model_name='projectteam',
            name='description',
            field=models.CharField(blank=True, default='', max_length=140, verbose_name='Description (optional)'),
        ),
    ]