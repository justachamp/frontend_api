# Generated by Django 2.2 on 2019-08-01 15:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_auto_20190620_1840'),
    ]
    operations = [
        migrations.RunSQL("DROP TABLE public.guardian_groupobjectpermission"),
        migrations.RunSQL("DROP TABLE public.guardian_userobjectpermission")

    ]
