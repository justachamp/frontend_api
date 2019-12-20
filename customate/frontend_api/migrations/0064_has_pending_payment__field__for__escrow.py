from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('frontend_api', '0063_index_for_escrowoperation_type_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='escrow',
            name='has_pending_payment',
            field=models.BooleanField(default=False)
        ),
    ]
