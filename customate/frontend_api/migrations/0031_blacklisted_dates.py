# Generated by Django 2.2 on 2019-09-03 12:36

from django.db import migrations, models
import uuid

from frontend_api.models.blacklist import BlacklistDate


def create_blacklistdate_records(apps, schema_editor):
    BlacklistDate(date="2019-12-25", description="Christmas").save()
    BlacklistDate(date="2019-12-26", description="Christmas").save()
    BlacklistDate(date="2020-01-01", description="New year").save()
    BlacklistDate(date="2020-04-10", description="Good Friday").save()
    BlacklistDate(date="2020-04-13", description="Easter Monday").save()
    BlacklistDate(date="2020-12-25", description="Christmas").save()
    BlacklistDate(date="2020-12-26", description="Christmas").save()


class Migration(migrations.Migration):

    dependencies = [
        ('frontend_api', '0030_schedule_funding_source_id_nullable'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlacklistDate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('date', models.DateField(unique=True)),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('description', models.CharField(blank=True, max_length=250, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunPython(create_blacklistdate_records)
    ]
