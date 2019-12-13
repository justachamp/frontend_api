from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('frontend_api', '0061_recreate_last_schedulepayments_view'),
    ]

    operations = [
        migrations.AlterField(
            model_name='escrow',
            name='wallet_id',
            field=models.UUIDField(
                help_text='Identifier of the virtual wallet, that relates to this Escrow',
                default=None, blank=True, null=True, unique=True
            ),
        ),
    ]
