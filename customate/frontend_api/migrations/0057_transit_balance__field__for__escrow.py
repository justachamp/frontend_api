# Generated by Django 2.2 on 2019-12-04 14:39
import django
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('frontend_api', '0056_escrowoperation_creator_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='escrow',
            name='balance',
            field=models.IntegerField(blank=True, null=True,
                                      help_text="Escrow balance received from payment service."),
        )
    ]