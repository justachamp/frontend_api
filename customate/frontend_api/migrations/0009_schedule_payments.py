# Generated by Django 2.2 on 2019-08-08 20:51

import core.fields
from django.db import migrations, models
import django.db.models.deletion
import enumfields.fields
import frontend_api.fields
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ('frontend_api', '0008_schedule_backup_funding_source_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='schedule',
            name='number_of_payments',
            field=models.PositiveIntegerField(default=0, help_text='Initial number of payments in the current schedule set upon creation.'),
        ),
        migrations.RunSQL("UPDATE public.frontend_api_schedule SET number_of_payments = number_of_payments_left"),

        migrations.CreateModel(
            name='SchedulePayment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('payment_id', models.UUIDField(help_text='Original UUID from payment-api service')),
                ('parent_payment_id', models.UUIDField(help_text='In case of follow-up payments, this points to a preceding payment UUID ')),
                ('funding_source_id', models.UUIDField()),
                ('payment_status', enumfields.fields.EnumField(enum=core.fields.PaymentStatusType, max_length=10)),
                ('schedule',
                 models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='frontend_api.Schedule')),
            ],
            options={
                'abstract': False,
            },
        ),

    ]
