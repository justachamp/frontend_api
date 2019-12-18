from django.db import migrations, models
from django.db.migrations import AddIndex
from django.db.models.indexes import Index


class Migration(migrations.Migration):
    dependencies = [
        ('frontend_api', '0062_escrow_wallet_id_unique'),
    ]

    operations = [
        AddIndex('EscrowOperation', Index(fields=['type'], name='type_index'))
    ]
