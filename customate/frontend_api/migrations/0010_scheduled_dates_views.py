
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('frontend_api', '0009_schedule_payments'),
    ]

    # repeated joins
    joins = """
        inner join "core_user" as "t3" 
          on ("t3"."id" = "t1"."user_id")
        inner join "frontend_api_account" as "t4" 
          on ("t4"."user_id" = "t1"."user_id")
        inner join "frontend_api_useraccount" as "t5"
          on ("t5"."account_ptr_id" = "t4"."id") 
    """

    sql_one_time = """
          create view frontend_api_one_time_schedule as 
            select "t1"."start_date" as "scheduled_date", "t1".*, "t5"."payment_account_id" from frontend_api_schedule as "t1" 
              {joins}  
            where "t1"."period" = 'one_time'
        """.format(joins=joins)

    sql_weekly = """
      create view frontend_api_weekly_schedule as
        select date("t2") as "scheduled_date", "t1".*, "t5"."payment_account_id" from frontend_api_schedule as "t1" 
        left join generate_series("t1"."start_date"::timestamp, "t1"."start_date"::timestamp+'5 years', '1 week'::interval) as "t2" 
          on true
        {joins}  
        where "t1"."period" = 'weekly' and t2 <= "t1"."start_date" + ("t1"."number_of_payments" * '1 week'::interval)
    """.format(joins=joins)

    sql_monthly = """
         create view frontend_api_monthly_schedule as
           select date("t2") as "scheduled_date", "t1".*, "t5"."payment_account_id" from frontend_api_schedule as "t1" 
           left join generate_series("t1"."start_date"::timestamp, "t1"."start_date"::timestamp+'5 years', '1 month'::interval) as "t2" 
            on true
            {joins}
           where "t1"."period" = 'monthly' and t2 <= "t1"."start_date" + ("t1"."number_of_payments" * '1 month'::interval)
       """.format(joins=joins)

    sql_quarterly = """
          create view frontend_api_quarterly_schedule as
            select date("t2") as "scheduled_date", "t1".*, "t5"."payment_account_id" from frontend_api_schedule as "t1" 
            left join generate_series("t1"."start_date"::timestamp, "t1"."start_date"::timestamp+'5 years', '4 months'::interval) as "t2" 
            on true
            {joins}
            where "t1"."period" = 'quarterly' and t2 <= "t1"."start_date" + ("t1"."number_of_payments" * '4 months'::interval)
        """.format(joins=joins)

    sql_yearly = """
           create view frontend_api_yearly_schedule as
             select date("t2") as "scheduled_date", "t1".*, "t5"."payment_account_id" from frontend_api_schedule as "t1" 
             left join generate_series("t1"."start_date"::timestamp, "t1"."start_date"::timestamp+'5 years', '1 year'::interval) as "t2" 
             on true
             {joins}
             where "t1"."period" = 'yearly' and t2 <= "t1"."start_date" + ("t1"."number_of_payments" * '1 year'::interval)
         """.format(joins=joins)

    # deposit payment schedule
    sql_deposits = """
            create view frontend_api_deposits_schedule as
              select "t1"."deposit_payment_date" as "scheduled_date", "t1".*, "t5"."payment_account_id"  from frontend_api_schedule as "t1" 
              {joins}
              where "t1"."deposit_payment_date" is not NULL 
             """.format(joins=joins)

    # constraints
    sql_schedule_payments_constraint = """
    ALTER TABLE public.frontend_api_schedulepayments ADD CONSTRAINT frontend_api_schedulepayments_payment_id_schedule_id 
    UNIQUE (payment_id,schedule_id);
    """

    operations = [
        migrations.RunSQL("DROP VIEW IF EXISTS public.frontend_api_one_time_schedule"),
        migrations.RunSQL(sql_one_time),
        migrations.RunSQL("DROP VIEW IF EXISTS public.frontend_api_weekly_schedule"),
        migrations.RunSQL(sql_weekly),
        migrations.RunSQL("DROP VIEW IF EXISTS public.frontend_api_monthly_schedule"),
        migrations.RunSQL(sql_monthly),
        migrations.RunSQL("DROP VIEW IF EXISTS public.frontend_api_quarterly_schedule"),
        migrations.RunSQL(sql_quarterly),
        migrations.RunSQL("DROP VIEW IF EXISTS public.frontend_api_yearly_schedule"),
        migrations.RunSQL(sql_yearly),
        migrations.RunSQL("DROP VIEW IF EXISTS public.frontend_api_deposits_schedule"),
        migrations.RunSQL(sql_deposits),
        migrations.RunSQL("DROP CONSTRAINT IF EXISTS frontend_api_schedulepayments_payment_id_schedule_id"),
        migrations.RunSQL(sql_schedule_payments_constraint),
        migrations.AddField(
            model_name='schedule',
            name='was_accepted',
            field=models.NullBooleanField(
                help_text='Indicates whether this payment Schedule was accepted by payee(counterpart)'),
        ),

    ]
