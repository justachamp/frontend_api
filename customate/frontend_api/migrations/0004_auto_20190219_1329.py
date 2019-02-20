# Generated by Django 2.1.7 on 2019-02-19 13:29

import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frontend_api', '0003_auto_20190214_1537'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='data',
            field=django.contrib.postgres.fields.jsonb.JSONField(default={'gbg': {}, 'version': 1}, encoder=django.core.serializers.json.DjangoJSONEncoder),
        ),
    ]