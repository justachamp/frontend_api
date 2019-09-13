# Generated by Django 2.2 on 2019-08-21 16:22

import core.fields
from django.db import migrations, models
import enumfields.fields
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ('frontend_api', '0014_alter_parent_payment_id'),
    ]

    sql_ltree_initialize = """
CREATE EXTENSION IF NOT EXISTS ltree;
ALTER TABLE public.frontend_api_schedulepayments ADD payment_path ltree;
CREATE INDEX schedulepayments_payment_path_idx ON public.frontend_api_schedulepayments USING GIST (payment_path);
CREATE INDEX schedulepayments_payment_id_idx ON public.frontend_api_schedulepayments (payment_path);


CREATE OR REPLACE FUNCTION update_payment_path() RETURNS TRIGGER AS $$
    DECLARE
        path ltree;
    BEGIN
        IF NEW.parent_payment_id IS NULL THEN
            NEW.payment_path = 'root'::ltree;
        ELSEIF TG_OP = 'INSERT' OR OLD.parent_payment_id IS NULL OR OLD.parent_payment_id != NEW.parent_payment_id THEN
            SELECT payment_path || replace(payment_id::text, '-', '_') FROM frontend_api_schedulepayments WHERE payment_id = NEW.parent_payment_id INTO path;
            IF path IS NULL THEN
                RAISE EXCEPTION 'Invalid parent_payment_id %', NEW.parent_payment_id;
            END IF;
            NEW.payment_path = path;
        END IF;
        RETURN NEW;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER payment_path_tgr
    BEFORE INSERT OR UPDATE ON frontend_api_schedulepayments
    FOR EACH ROW EXECUTE PROCEDURE update_payment_path();
    
    """

    sql_ltree_migrate_existing = """
UPDATE frontend_api_schedulepayments SET payment_path='root'::ltree WHERE parent_payment_id is NULL;
UPDATE frontend_api_schedulepayments SET payment_path='root'::ltree || replace(parent_payment_id::text,'-','_') WHERE parent_payment_id is not NULL;
    """

# select 'leaf' payments only (whose are last in payment chains)
    sql_view = """
CREATE OR REPLACE VIEW frontend_api_last_schedulepayments AS
SELECT id, created_at, updated_at,payment_id, parent_payment_id,funding_source_id, payment_status, schedule_id 
FROM frontend_api_schedulepayments AS f1
WHERE NOT EXISTS (
  SELECT *  FROM frontend_api_schedulepayments AS f2
  WHERE f1.payment_path @> f2.payment_path
    AND f1.payment_path <> f2.payment_path
)
or (parent_payment_id is null and not exists (
	SELECT payment_id, parent_payment_id, payment_status, payment_path from frontend_api_schedulepayments as f2 
	where  f2.payment_path ~ ('*.' || replace(f1.payment_id::text,'-', '_') || '.*')::lquery
))
"""

    operations = [
        migrations.CreateModel(
            name='LastSchedulePayments',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('payment_id', models.UUIDField(help_text='Original UUID from payment-api service')),
                ('parent_payment_id', models.UUIDField(
                    blank=True, default=None,
                    help_text='In case of follow-up payments, this points to a preceding payment UUID ',
                    null=True)
                 ),
                ('funding_source_id', models.UUIDField()),
                ('payment_status', enumfields.fields.EnumField(enum=core.fields.PaymentStatusType, max_length=10)),
            ],
            options={
                'db_table': 'frontend_api_last_schedulepayments',
                'managed': False,
            },
        ),
        migrations.AlterField(
            model_name='schedulepayments',
            name='parent_payment_id',
            field=models.UUIDField(
                blank=True, default=None,
                help_text='In case of follow-up payments, this points to a preceding payment UUID ',
                null=True
            ),
        ),
        migrations.RunSQL(sql_ltree_initialize),
        migrations.RunSQL(sql_ltree_migrate_existing),
        migrations.RunSQL("DROP VIEW IF EXISTS public.frontend_api_last_schedulepayments"),
        migrations.RunSQL(sql_view),
    ]