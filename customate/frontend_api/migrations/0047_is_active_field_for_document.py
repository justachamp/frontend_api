# Generated by Django 2.2 on 2019-10-17 09:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend_api', '0046_unique_filename_for_S3_bucket'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]