# Generated by Django 2.2 on 2019-08-27 08:17

import core.fields
from django.db import migrations
import enumfields.fields


class Migration(migrations.Migration):

    dependencies = [
        ('frontend_api', '0020_remove_aborted_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedule',
            name='payee_type',
            field=enumfields.fields.EnumField(enum=core.fields.PayeeType, max_length=50),
        ),
    ]
