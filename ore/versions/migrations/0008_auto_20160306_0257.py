# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-03-06 02:57
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import ore.core.util


class Migration(migrations.Migration):

    dependencies = [
        ('versions', '0007_auto_20160305_2223'),
    ]

    operations = [
        migrations.AlterField(
            model_name='version',
            name='name',
            field=models.CharField(help_text='To ensure your versions are ordered correctly, please use a Maven-compatible version', max_length=32, validators=[django.core.validators.RegexValidator('^[a-zA-Z0-9._][a-zA-Z0-9.\\-_]*([\\w.\\-_ ]*[a-zA-Z0-9._][a-zA-Z0-9.\\-_]*)?$', 'Enter a valid version name.', 'invalid'), ore.core.util.validate_not_prohibited], verbose_name='Version name'),
        ),
        migrations.AlterUniqueTogether(
            name='file',
            unique_together=set([('version', 'file_name', 'file_extension')]),
        ),
    ]
