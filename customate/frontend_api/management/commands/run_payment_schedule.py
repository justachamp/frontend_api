from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from uuid import UUID
from frontend_api.tasks import make_payment
from frontend_api.models.schedule import Schedule


class Command(BaseCommand):
    help = 'Immediately initiate payments according to payment schedule'

    def add_arguments(self, parser):
        parser.add_argument('schedule_id', type=str, help='UUID of payment schedule to initiate'),

    def handle(self, *args, **options):

        if not options.get('schedule_id'):
            raise CommandError('Schedule UUID must be specified')

        try:
            schedule_id = UUID(options.get('schedule_id'))
        except ValueError:
            raise CommandError("Invalid UUID string(%s)" % options.get('schedule_id'))

        # self.stdout.write(self.style.WARNING(f'Options {options}'))
        # schedule_id = options[]
        self.stdout.write("Fetching schedule_id=%s" % schedule_id)
        s = Schedule.objects.get(pk=schedule_id)

        self.stdout.write("Submitting regular payment: origin_user.id=%s, payment_account_id=%s, currency=%s, "
                          "payment_amount=%s, additional_information=%s, payee_id=%s, funding_source_id=%s" % (
                              str(s.origin_user.id), str(s.origin_user.account.payment_account_id), str(s.currency.value), int(s.payment_amount),
                              str(s.additional_information),
                              str(s.payee_id), str(s.funding_source_id)
                          ))

        make_payment.delay(
            schedule_id=str(s.id),
            user_id=str(s.origin_user.id),
            payment_account_id=str(s.origin_user.account.payment_account_id),
            currency=str(s.currency.value),
            payment_amount=int(s.payment_amount),
            additional_information=str(s.additional_information),
            payee_id=str(s.payee_id),
            funding_source_id=str(s.funding_source_id),
            parent_payment_id=None
        )
