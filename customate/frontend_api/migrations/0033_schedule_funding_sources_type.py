# Generated by Django 2.2 on 2019-09-04 08:59

from django.db import migrations, connection

import core.fields
import enumfields.fields
from uuid import UUID
import external_apis.payment.service as payment_service


def fill_in_schedules_funding_source_type(apps, schema_editor):
    """
    Update newly added field with appropriate funding source type
    :return:
    """

    with connection.cursor() as c:
        c.execute("DELETE FROM frontend_api_schedule WHERE funding_source_id IS NULL")
        c.execute("SELECT DISTINCT(funding_source_id) FROM frontend_api_schedule WHERE funding_source_type IS NULL")
        for funding_source_id in c.fetchall():
            fd = payment_service.FundingSource.get(fs_id=UUID(funding_source_id[0]))
            if funding_source_id[0] is not None:
                c.execute(
                    "UPDATE frontend_api_schedule SET funding_source_type = '%s' WHERE funding_source_id = '%s'" % (
                        fd.type, funding_source_id[0]
                    ))


class Migration(migrations.Migration):
    dependencies = [
        ('frontend_api', '0032_documents_with_blank_schedule'),
    ]

    max_field_length = 50
    operations = [
        migrations.AddField(
            model_name='schedule',
            name='funding_source_type',
            field=enumfields.fields.EnumField(enum=core.fields.FundingSourceType, max_length=max_field_length,
                                              null=True),
        ),
        migrations.RunPython(fill_in_schedules_funding_source_type),
        migrations.AlterField(
            model_name='schedule',
            name='funding_source_type',
            field=enumfields.fields.EnumField(enum=core.fields.FundingSourceType, max_length=max_field_length,
                                              null=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='schedule',
            name='backup_funding_source_type',
            field=enumfields.fields.EnumField(enum=core.fields.FundingSourceType, max_length=max_field_length,
                                              null=True),
        ),
        migrations.RunSQL("""
            UPDATE frontend_api_schedule SET backup_funding_source_type = 'WALLET' WHERE backup_funding_source_id IS NOT NULL
        """)
    ]
