# Generated by Django 2.1.7 on 2019-03-12 13:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_remove_user_mfa_enabled'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='address_line_1',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='address',
            name='locality',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='address',
            name='postcode',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]