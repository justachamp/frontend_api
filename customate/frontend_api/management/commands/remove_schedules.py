from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection

from core.models import User


class Command(BaseCommand):
    help = "PERMANENTLY remove schedules related to provided email and have specified status."

    def add_arguments(self, parser):
        parser.add_argument('user_email', type=str, help='Email of user that acts as origin in schedules'),
        parser.add_argument('statuses', type=str, help='Schedules statuses (via comma)'),

    @transaction.atomic
    def handle(self, *args, **options):
        if not options.get('user_email'):
            raise CommandError('user_email argument does not exist')

        if not options.get('statuses'):
            raise CommandError('statuses argument does not exist')

        user_email = options.get('user_email')
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            self.stderr.write(f"Cannot find user record by provided email ({user_email})")
            return

        statuses = list(map(lambda s: s.strip(), options.get('statuses').split(',')))

        with connection.cursor() as cursor:
            self.stdout.write(f'Starting schedules removing process...')
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")  # Inform about constrain violation immediately

            schedule_ids = []
            cursor.execute("select id from frontend_api_schedule where origin_user_id = %s and status = ANY(%s)",
                           params=[user.id, statuses])
            for schedule_id in cursor.fetchall():
                schedule_ids.append(schedule_id[0])

            self.stdout.write(f"Removing {len(schedule_ids)} schedule(s)")

            if schedule_ids:
                cursor.execute("delete from frontend_api_schedulepayments where schedule_id = ANY(%s);",
                               params=[schedule_ids])
                cursor.execute("delete from frontend_api_document where schedule_id = ANY(%s);",
                               params=[schedule_ids])
                cursor.execute("delete from frontend_api_schedule where id = ANY(%s);",
                               params=[schedule_ids])

            self.stdout.write(f'Done')
