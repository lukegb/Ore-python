# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-04 22:35
from __future__ import unicode_literals

from django.db import migrations, models
from django.db.models import Func

def set_lower_name(apps, schema_editor):
    Namespace = apps.get_model('core', 'Namespace')
    db_alias = schema_editor.connection.alias
    namespaces = Namespace.objects.using(db_alias).all()
    namespaces.update(lower_name=Func(F('name', function='LOWER')))


def delete_lower_name(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_auto_20160104_1808'),
    ]

    operations = [
        migrations.AddField(
            model_name='namespace',
            name='lower_name',
            field=models.CharField(null=True, blank=True, max_length=32, unique=False, verbose_name='name'),
        ),
        migrations.RunSQL("UPDATE core_namespace SET lower_name=LOWER(name)"),
        migrations.RunSQL("DELETE FROM core_namespace WHERE id IN (SELECT DISTINCT a.id FROM core_namespace a INNER JOIN core_namespace b ON a.lower_name=b.lower_name AND a.id > b.id)"),
    ]
