# Generated by Django 2.2 on 2019-08-16 06:33

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('frontend_api', '0012_remove_schedule_was_accepted'),
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('filename', models.CharField(max_length=128, unique=True)),
                ('slug', models.CharField(blank=True, max_length=128, null=True)),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='frontend_api.Schedule')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedule_documents', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
