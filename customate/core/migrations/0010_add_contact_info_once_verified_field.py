# Generated by Django 2.2 on 2019-08-28 08:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_drop_guardian'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='contact_info_once_verified',
            field=models.BooleanField(default=False, help_text='Indicates whether the email and phone number has been ever verified', verbose_name='contact info once verified'),
        ),
        migrations.AlterField(
            model_name='user',
            name='email_verified',
            field=models.BooleanField(default=False, help_text='Indicates whether the email has been verified', verbose_name='phone number verified'),
        ),
        migrations.AlterField(
            model_name='user',
            name='phone_number_verified',
            field=models.BooleanField(default=False, help_text='Indicates whether the phone number has been verified', verbose_name='phone number verified'),
        ),
    ]