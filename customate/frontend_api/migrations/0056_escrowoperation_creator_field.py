# Generated by Django 2.2 on 2019-12-04 14:39
import django
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend_api', '0055_payee_related_fields_in_escrow'),
    ]

    sql_set_creator = """
        UPDATE frontend_api_escrowoperation
        SET creator_id = frontend_api_escrow.funder_user_id
        FROM frontend_api_escrow
        WHERE escrow_id = frontend_api_escrow.id;
    """

    operations = [
        migrations.AddField(
            model_name='escrowoperation',
            name='creator',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                    related_name='operations_created_by_me', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunSQL(sql_set_creator),
        migrations.AlterField(
            model_name='escrowoperation',
            name='creator',
            field=models.ForeignKey(blank=False, null=False, on_delete=django.db.models.deletion.DO_NOTHING,
                                    related_name='operations_created_by_me', to=settings.AUTH_USER_MODEL),
        ),
    ]
