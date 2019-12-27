# Generated by Django 2.2 on 2019-11-27 17:45

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('frontend_api', '0065_escrowoperation_unique_index_for_load_funds'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='escrow',
            field=models.BooleanField(
                default=False, null=False,
                help_text='indicates whether this Escrow is being disputed',
            )),
    ]
