# Generated by Django 2.2 on 2019-07-19 10:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend_api', '0005_auto_20190719_0825'),
    ]

    operations = [
        migrations.AddField(
            model_name='schedule',
            name='payee_title',
            field=models.CharField(default='', max_length=100),
        ),
    ]
