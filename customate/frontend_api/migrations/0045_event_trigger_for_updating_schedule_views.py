from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frontend_api', '0044_recreate_schedule_views'),
    ]

    sql_create_function = """
        CREATE FUNCTION handle_alter_schedule_event() RETURNS event_trigger AS $$
        DECLARE
            r RECORD;
            joins text := 'INNER JOIN "core_user" AS "t3" '
                    'ON ("t3"."id" = "t1"."origin_user_id") '
                'INNER JOIN "frontend_api_account" AS "t4" ' 
                    'ON ("t4"."user_id" = "t1"."origin_user_id") '
                'LEFT JOIN "frontend_api_subuseraccount" AS "t5" '
                    'ON ("t5".account_ptr_id = "t4".id) '
                'INNER JOIN "frontend_api_useraccount" AS "t6" '
                    'ON ("t6"."account_ptr_id" = "t4"."id" OR "t6"."account_ptr_id" = "t5"."owner_account_id")';
        BEGIN
            FOR r IN SELECT * FROM pg_event_trigger_ddl_commands() LOOP
                IF r.object_identity = 'public.frontend_api_schedule' THEN

                    /* update views related to frontend_api_schedule */
                    RAISE NOTICE 'drop frontend_api_one_time_schedule';
                    DROP VIEW IF EXISTS frontend_api_one_time_schedule;
                    RAISE NOTICE 'create frontend_api_one_time_schedule';
                    EXECUTE 'CREATE VIEW frontend_api_one_time_schedule AS '
                        'SELECT date(adjust_execution_date("t1"."start_date", "t1"."funding_source_type")) AS "scheduled_date", '
                        '"t1".*, "t6"."payment_account_id" FROM frontend_api_schedule AS "t1" '
                        || joins ||
                        ' WHERE "t1"."period" = ''one_time''; ';

                    RAISE NOTICE 'drop frontend_api_weekly_schedule';
                    DROP VIEW IF EXISTS frontend_api_weekly_schedule;
                    RAISE NOTICE 'create frontend_api_weekly_schedule';
                    EXECUTE 'CREATE VIEW frontend_api_weekly_schedule AS '
                        'SELECT date("t2") AS "scheduled_date", "t1".*, "t6"."payment_account_id" FROM frontend_api_schedule AS "t1" '
                        'LEFT JOIN generate_series(adjust_execution_date("t1"."start_date", "t1"."funding_source_type"), '
                            'adjust_execution_date("t1"."start_date", "t1"."funding_source_type")+''5 years'', ''1 week''::interval) AS "t2" '
                            'ON true '
                        || joins ||
                        'WHERE "t1"."period" = ''weekly'' AND '
                        't2 <= adjust_execution_date("t1"."start_date", "t1"."funding_source_type") '
                        '+ (("t1"."number_of_payments"+"t1"."number_of_payments_made") * ''1 week''::interval); ';

                    RAISE NOTICE 'drop frontend_api_monthly_schedule';
                    DROP VIEW IF EXISTS frontend_api_monthly_schedule;
                    RAISE NOTICE 'create frontend_api_monthly_schedule';
                    EXECUTE 'CREATE VIEW frontend_api_monthly_schedule AS '
                        'SELECT date("t2") AS "scheduled_date", "t1".*, "t6"."payment_account_id" FROM frontend_api_schedule AS "t1" '
                        'LEFT JOIN generate_series(adjust_execution_date("t1"."start_date", "t1"."funding_source_type"), '
                            'adjust_execution_date("t1"."start_date", "t1"."funding_source_type")+''5 years'', ''1 month''::interval) AS "t2" '
                            'ON true '
                        || joins ||
                        'WHERE "t1"."period" = ''monthly'' AND '
                        't2 <= adjust_execution_date("t1"."start_date", "t1"."funding_source_type") '
                            '+ (("t1"."number_of_payments"+"t1"."number_of_payments_made") * ''1 month''::interval); ';

                    RAISE NOTICE 'drop frontend_api_quarterly_schedule';
                    DROP VIEW IF EXISTS frontend_api_quarterly_schedule;
                    RAISE NOTICE 'create frontend_api_quarterly_schedule';
                    EXECUTE 'CREATE VIEW frontend_api_quarterly_schedule AS '
                    'SELECT date("t2") AS "scheduled_date", "t1".*, "t6"."payment_account_id" from frontend_api_schedule AS "t1" '
                    'LEFT JOIN generate_series(adjust_execution_date("t1"."start_date", "t1"."funding_source_type"), '
                        'adjust_execution_date("t1"."start_date", "t1"."funding_source_type")+''5 years'', ''4 months''::interval) AS "t2" '
                        'on true '
                    || joins ||
                    'where "t1"."period" = ''quarterly'' and '
                    't2 <= adjust_execution_date("t1"."start_date", "t1"."funding_source_type") '
                        '+ (("t1"."number_of_payments"+"t1"."number_of_payments_made") * ''4 months''::interval); ';

                    RAISE NOTICE 'drop frontend_api_yearly_schedule';
                    DROP VIEW IF EXISTS frontend_api_yearly_schedule;
                    RAISE NOTICE 'create frontend_api_yearly_schedule';
                    EXECUTE 'CREATE VIEW frontend_api_yearly_schedule AS '
                    'SELECT date("t2") AS "scheduled_date", "t1".*, "t6"."payment_account_id" from frontend_api_schedule AS "t1" '
                    'LEFT JOIN generate_series(adjust_execution_date("t1"."start_date", "t1"."funding_source_type"), '
                        'adjust_execution_date("t1"."start_date", "t1"."funding_source_type")+''10 years'', ''1 year''::interval) AS "t2" '
                        'ON true '
                    || joins ||
                    'where "t1"."period" = ''yearly'' and '
                    't2 <= adjust_execution_date("t1"."start_date", "t1"."funding_source_type") '
                        '+ (("t1"."number_of_payments"+"t1"."number_of_payments_made") * ''1 year''::interval); ';

                    RAISE NOTICE 'drop frontend_api_deposits_schedule';
                    DROP VIEW IF EXISTS frontend_api_deposits_schedule;
                    RAISE NOTICE 'create frontend_api_deposits_schedule';
                    EXECUTE 'CREATE VIEW frontend_api_deposits_schedule AS '
                    'SELECT date(adjust_execution_date("t1"."deposit_payment_date", "t1"."funding_source_type")) AS "scheduled_date", '
                        '"t1".*, "t6"."payment_account_id"  from frontend_api_schedule AS "t1" '
                    || joins ||
                    'where "t1"."deposit_payment_date" is not NULL; ';

                END IF;
            END LOOP;
        END;
        $$
        LANGUAGE plpgsql;
     """

    sql_create_event = """
        CREATE EVENT TRIGGER alter_schedule_event
          ON ddl_command_end WHEN TAG IN ('ALTER TABLE')
          EXECUTE PROCEDURE handle_alter_schedule_event();
    """

    operations = [
        migrations.RunSQL("DROP FUNCTION IF EXISTS handle_alter_schedule_event CASCADE"),
        migrations.RunSQL(sql_create_function),
        migrations.RunSQL("DROP EVENT TRIGGER IF EXISTS alter_schedule_event"),
        migrations.RunSQL(sql_create_event),
    ]
