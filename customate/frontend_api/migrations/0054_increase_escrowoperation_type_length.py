# Generated by Django 2.2 on 2019-12-03 07:41

from django.db import migrations

import enumfields.fields
import frontend_api


class Migration(migrations.Migration):

    dependencies = [
        ('frontend_api', '0053_make_some_escrow_fields_nullable'),
    ]

    operations = [
        migrations.AlterField(
            model_name='escrowoperation',
            name='type',
            field=enumfields.fields.EnumField(enum=frontend_api.models.escrow.EscrowOperationType, max_length=20),
        ),
    ]
