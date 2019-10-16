from traceback import format_exc

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from core.models import User


class Command(BaseCommand):
    help = 'Find an user with specified phone number and change phone to random value'

    def add_arguments(self, parser):
        parser.add_argument('phone_number', type=str, help='Phone number'),

    def handle(self, *args, **options):
        if not options.get('phone_number'):
            raise CommandError('Phone number must be specified')

        phone_number = options.get('phone_number')
        try:
            self.stdout.write("Searching for user with phone_number=%s" % phone_number)
            user = User.objects.get(phone_number=phone_number)
        except Exception:
            raise CommandError("Unable to find user with phone_number=%s (problem=%r)" % (phone_number, format_exc()))

        update_sql = f"""
            UPDATE core_user
            SET phone_number_verified = FALSE, phone_number = (SELECT format('%1$s%2$s%3$s%4$s%5$s%6$s%7$s%8$s%9$s%10$s%11$s', '+44', a[1], a[2], a[3], a[4], a[5], a[6], a[7], a[8], a[9], a[10])
            FROM (
               SELECT ARRAY (
                  SELECT trunc(random() * 10)::int
                  FROM generate_series(1, 10 + core_user.is_active::int)
                  ) AS a
               ) as random_phone_number)
            WHERE id = '{user.id}' 
            RETURNING phone_number
        """

        with connection.cursor() as cursor:
            cursor.execute(update_sql)
            new_phone_number = cursor.fetchone()[0]

        if user:
            self.stdout.write(f"Updated user ({user.email}) with new phone number={new_phone_number}")

        from authentication.cognito.core import helpers
        helpers.admin_update_user_attributes({
            'username': user.username,
            'user_attributes': [{
                'Name': 'phone_number',
                'Value': new_phone_number
            }]
        })
