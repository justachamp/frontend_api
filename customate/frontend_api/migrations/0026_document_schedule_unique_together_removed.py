# Generated by Django 2.2 on 2019-08-28 17:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frontend_api', '0025_number_of_payments_made'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='document',
            unique_together=set(),
        ),
    ]
