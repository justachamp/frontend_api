# Generated by Django 2.1.7 on 2019-03-12 13:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_auto_20190312_1342'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='address',
            field=models.CharField(blank=True, max_length=250),
        ),
    ]
