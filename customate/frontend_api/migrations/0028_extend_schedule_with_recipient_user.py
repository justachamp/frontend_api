# Generated by Django 2.2 on 2019-08-13 04:50

from django.conf import settings
from django.db import migrations, models, connection
import django.db.models.deletion
from frontend_api.core.client import PaymentApiClient


def fill_in_schedules_recipient_id(apps, schema_editor):
    """
    Update newly added field recipient_id with appropriate user_id according to selected payee
    :return:
    """
    payment_client = PaymentApiClient(None)
    with connection.cursor() as c:
        c.execute("SELECT DISTINCT(payee_id) FROM frontend_api_schedule WHERE payee_type = 'WALLET'")
        for payee_id in c.fetchall():
            pd = payment_client.get_payee_details(payee_id[0])
            query = """
                UPDATE
                    frontend_api_schedule
                SET
                    recipient_user_id = acc.user_id
                FROM frontend_api_account as acc
                    JOIN frontend_api_useraccount as uacc
                        ON acc.id = uacc.account_ptr_id AND uacc.payment_account_id = '%s'
                WHERE
                    payee_id = '%s'
                """ % (pd.payment_account_id, payee_id[0])
            c.execute(query)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('frontend_api', '0027_include_subuser_in_schedule_view_selection'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedule',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='schedule_payed_by_me',
                                    to=settings.AUTH_USER_MODEL),
        ),
        migrations.RenameField(
            model_name='schedule',
            old_name='user',
            new_name='origin_user',
        ),
        migrations.AddField(
            model_name='schedule',
            name='recipient_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                    related_name='schedule_payed_to_me', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(fill_in_schedules_recipient_id),
    ]
