# Generated by Django 2.2 on 2019-07-18 13:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend_api', '0003_schedule_fee_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='schedule',
            name='payee_iban',
            field=models.CharField(default='', max_length=50),
        ),
        migrations.AddField(
            model_name='schedule',
            name='payee_recipient_email',
            field=models.CharField(default='', max_length=50),
        ),
        migrations.AddField(
            model_name='schedule',
            name='payee_recipient_name',
            field=models.CharField(default='', max_length=50),
        ),
    ]
