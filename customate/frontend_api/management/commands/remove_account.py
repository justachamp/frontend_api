from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection

import external_apis.payment.service as payment_service
from core.models import User


class Command(BaseCommand):
    help = "PERMANENTLY remove accounts by any related user's emails. " \
           "NOTE that payment service account will not be removed, just marked as inactive."

    def add_arguments(self, parser):
        parser.add_argument('user_emails', type=str, help='Emails of users that exist in target accounts'),

        parser.add_argument('--skip_confirmation',
                            type=bool, default=False,
                            help='Prevent interactive confirmation')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options.get('user_emails'):
            raise CommandError('user_emails argument does not exist')

        user_emails = list(map(lambda s: s.strip(), options.get('user_emails').split(',')))

        self.stdout.write(f"Total users: {len(user_emails)}")

        for user_email in user_emails:
            self.stdout.write(f"Processing email: {user_email}")

            try:
                user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                self.stderr.write(f"Cannot find user record by provided email({user_email})")
                continue

            if user.is_superuser:
                self.stderr.write("Cannot remove superuser")
                continue

            owner_account = user.account.owner_account if user.is_subuser else user.account
            if hasattr(owner_account, 'sub_user_accounts'):
                related_account_ids = [owner_account.id] + list(
                    owner_account.sub_user_accounts.all().values_list('id', flat=True)
                )
            else:
                related_account_ids = [owner_account.id]

            skip_confirmation = options.get('skip_confirmation')
            if not skip_confirmation:
                confirm = input("Type 'yes' if you would like to permanently remove specified accounts: %s (it's time to "
                                "check IDs and environment): "
                                % related_account_ids)
                if confirm != 'yes':
                    return

            with connection.cursor() as cursor:
                related_user_ids = []
                cursor.execute("SELECT user_id FROM frontend_api_account WHERE id = ANY(%s)", params=[related_account_ids])
                for user_id in cursor.fetchall():
                    related_user_ids.append(user_id[0])

                payment_account_ids = []
                cursor.execute("SELECT payment_account_id FROM frontend_api_useraccount "
                               "WHERE payment_account_id IS NOT NULL AND account_ptr_id = ANY(%s)",
                               params=[related_account_ids])
                for payment_account_id in cursor.fetchall():
                    payment_account_ids.append(payment_account_id[0])
                self.stdout.write(f'Affected payment account ids: {payment_account_ids}')

                self.stdout.write(f'Starting accounts removing process...')
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")  # Inform about constrain violation immediately

                # Remove sub-user related records (link with owner account & permissions)
                cursor.execute("DELETE FROM frontend_api_subuserpermission WHERE account_id = ANY(%s)",
                               params=[related_account_ids])
                cursor.execute("DELETE FROM frontend_api_subuseraccount WHERE owner_account_id = ANY(%s)",
                               params=[related_account_ids])

                # Remove admin user related records
                cursor.execute("DELETE FROM frontend_api_adminuserpermission WHERE account_id = ANY(%s)",
                               params=[related_account_ids])
                cursor.execute("DELETE FROM frontend_api_adminuseraccount WHERE account_ptr_id = ANY(%s)",
                               params=[related_account_ids])

                # Remove relationship between account & company & payment account
                cursor.execute("DELETE FROM frontend_api_useraccount WHERE account_ptr_id = ANY(%s)",
                               params=[related_account_ids])

                # Remove user's accounts
                cursor.execute("DELETE FROM frontend_api_account WHERE id = ANY(%s)", params=[related_account_ids])

                # Remove schedules related records (documents, schedule payments data and schedules themselves)
                cursor.execute("DELETE FROM frontend_api_document WHERE user_id = ANY(%s)", params=[related_user_ids])
                cursor.execute("DELETE FROM frontend_api_schedulepayments WHERE schedule_id "
                               "IN (SELECT id FROM frontend_api_schedule WHERE recipient_user_id = ANY(%s) OR origin_user_id = ANY(%s))",
                               params=[related_user_ids, related_user_ids])
                cursor.execute(
                    "DELETE FROM frontend_api_schedule WHERE recipient_user_id = ANY(%s) OR origin_user_id = ANY(%s)",
                    params=[related_user_ids, related_user_ids])

                # Remove core django user related records
                cursor.execute("DELETE FROM core_user_user_permissions WHERE user_id = ANY(%s)", params=[related_user_ids])
                cursor.execute("DELETE FROM core_user_groups WHERE user_id = ANY(%s)", params=[related_user_ids])
                cursor.execute("DELETE FROM core_user WHERE id = ANY(%s)", params=[related_user_ids])

                # Deactivate (not REMOVE) payment account (we do this in the end, to be sure that queries pass)
                for account_id in payment_account_ids:
                    payment_service.PaymentAccount.deactivate(payment_account_id=account_id)

                self.stdout.write(f'Done')
