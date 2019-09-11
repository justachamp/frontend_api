from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.fields import UserRole
from enumfields import Enum

from core.models import Address
from frontend_api.core.client import PaymentApiClient
from frontend_api.fields import AccountType
from frontend_api.models import UserAccount, Company

RESEND = 'RESEND'


class ServiceAccountType(Enum):
    fee = 'fee'
    tax = 'tax'
    credit_card = 'credit_card'

    class Labels:
        fee = 'fee'
        tax = 'tax'
        credit_card = 'credit_card'


class Command(BaseCommand):
    help = 'Create service account and its user, that will be used to sign in. ' \
           'Service accounts provide a user-friendly way to access wallets with credit card, fees and tax funds.'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Indicates the username of user to be created'),
        parser.add_argument('phone_number', type=str,
                            help='Indicates the phone number of user to be created')
        parser.add_argument('account_type', type=str,
                            help='Indicates the service account\'s type ("fee", "tax" or "credit_card")')

        parser.add_argument('-f', '--first_name', type=str, help='Indicates the first_name of user to be created')
        parser.add_argument('-m', '--middle_name', type=str, help='Indicates the middle_name of user to be created')
        parser.add_argument('-l', '--last_name', type=str, help='Indicates the last_name of user to be created')
        parser.add_argument('-r', '--resend',
                            default=False,
                            action='store_true',
                            help='Set to "RESEND" to resend the invitation message to a user that already exists '
                                 'and reset the expiration limit on the user\'s account.')

    def get_user_data(self, data):
        username = data.get('username').lower()
        phone_number = data.get('phone_number').lower()
        userdata = {
            'username': username,
            'phone_number': phone_number,
            'email': username,
            'role': UserRole.owner.value,
            'first_name': data.get('first_name', ''),
            'middle_name': data.get('middle_name', ''),
            'last_name': data.get('last_name', ''),
        }

        if data.get('resend'):
            userdata['action'] = RESEND

        return userdata

    def get_serializer_class(self, data):
        from frontend_api.serializers import UserSerializer
        from frontend_api.serializers import BaseUserResendInviteSerializer
        return BaseUserResendInviteSerializer if data and data.get('resend') else UserSerializer

    def handle(self, *args, **options):
        from authentication.cognito.serializers import CognitoInviteUserSerializer

        if not options.get('username'):
            raise CommandError('username argument does not exist')

        if not options.get('phone_number'):
            raise CommandError('phone_number argument does not exist')

        if not options.get('account_type'):
            raise CommandError('account_type argument does not exist')

        if not options.get('account_type') in [s.name for s in ServiceAccountType]:
            raise CommandError('Provided account_type argument contains incorrect data, '
                               'allowed values: fee, tax, credit_card')

        self.stdout.write(f'Provided options: {options}')
        data = self.get_user_data(options)

        self.stdout.write(f'Formatted user data: {data}')
        serializer = self.get_serializer_class(options)(data=data)

        try:
            if serializer.is_valid(True):
                self.stdout.write(
                    f'Validated data: {serializer.validated_data}'
                )
                with transaction.atomic():
                    invitation = CognitoInviteUserSerializer.invite(data)
                    if not data.get('action') == RESEND:
                        user = serializer.save()
                        user.cognito_id = invitation.id
                        user.role = UserRole[data.get('role')]
                        user.email_verified = True
                        user.phone_number_verified = True
                        user_address = Address()
                        user_address.save()

                        user.address = user_address
                        user.save()

                        company_address = Address()
                        company_address.save()
                        company = Company()
                        company.address = company_address
                        company.save()

                        account = UserAccount(user=user, account_type=AccountType.business, company=company)
                        account.save()

                        client = PaymentApiClient(user)
                        client.assign_payment_service_account(options.get('account_type'))
                        invitation.pk = user.id

                    self.stdout.write(
                        f'User was successfully initiated with '
                        f'username:{invitation.username} '
                        f'pass:{invitation.temporary_password}'
                    )
        except Exception as ex:
            raise ex
