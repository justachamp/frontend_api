# Generated by Django 2.2 on 2019-12-10 06:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frontend_api', '0064_has_pending_payment__field__for__escrow'),
    ]

    # Deny to create several pending "load_funds" operations.
    drop_index = "DROP INDEX IF EXISTS pending_escrowoperation_unique;"
    sql_unique_index = """
        CREATE UNIQUE INDEX pending_escrowoperation_unique ON frontend_api_escrowoperation (type, escrow_id)
            WHERE approved is NULL AND is_expired = FALSE;
    """

    operations = [
        migrations.RunSQL(drop_index),
        migrations.RunSQL(sql_unique_index),
    ]
