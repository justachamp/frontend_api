from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.fields import UserRole
RESEND = 'RESEND'


class Command(BaseCommand):
    help = 'Invite admin with full set of permissions'

    def add_arguments(self, parser):
        # parser.add_argument('username', type=str, help='Indicates the username of user to be created')
        # help = 'sum the integers (default: find the max)')
        parser.add_argument('username', type=str, help='Indicates the username of user to be created'),

        parser.add_argument('-f', '--first_name', type=str, help='Indicates the first_name of user to be created')
        parser.add_argument('-m', '--middle_name', type=str, help='Indicates the middle_name of user to be created')
        parser.add_argument('-l', '--last_name', type=str, help='Indicates the last_name of user to be created')
        parser.add_argument('-r', '--resend',
                            default=False,
                            action='store_true',
                            help='Set to "RESEND" to resend the invitation message to a user that already exists '
                                 'and reset the expiration limit on the user\'s account. Set to "SUPPRESS" to suppress'
                                 ' sending the message. Only one value can be specified.')

    # @staticmethod
    def get_user_data(self, data):

        username = data.get('username').lower()
        userdata = {
            'username': username,
            'email': username,
            'role': UserRole.admin.value,
            'first_name': data.get('first_name', ''),
            'middle_name': data.get('middle_name', ''),
            'last_name': data.get('last_name', ''),
        }

        if data.get('resend'):
            userdata['action'] = RESEND

        return userdata

    def get_serializer_class(self, data):
        from frontend_api.serializers import AdminUserSerializer
        from frontend_api.serializers import BaseUserResendInviteSerializer
        return BaseUserResendInviteSerializer if data and data.get('resend') else AdminUserSerializer

    def handle(self, *args, **options):

        from authentication.cognito.serializers import CognitoInviteUserSerializer

        if not options.get('username'):
            raise CommandError('username argument does not exist')

        self.stdout.write(self.style.WARNING(f'Options {options}'))
        data = self.get_user_data(options)

        self.stdout.write(self.style.WARNING(f'Admin user data {data}'))
        serializer = self.get_serializer_class(options)(data=data)

        try:
            if serializer.is_valid(True):
                self.stdout.write(
                    self.style.WARNING(
                        f'Serializer data {serializer.validated_data}'
                    )
                )
                with transaction.atomic():
                    invitation = CognitoInviteUserSerializer.invite(data)
                    if not data.get('action') == RESEND:
                        user = serializer.save()
                        user.cognito_id = invitation.id
                        user.email_verified = True
                        user.is_superuser = True
                        user.save()
                        user.account.permission.manage_tax = True 
                        user.account.permission.manage_fee = True
                        user.account.permission.save()
                        invitation.pk = user.id
                    self.stdout.write(
                        self.style.MIGRATE_LABEL(
                            f'Admin was successfully initiated with '
                            f'username:{invitation.username} '
                            f'pass:{invitation.temporary_password}'
                        )
                    )
        except Exception as ex:
            raise ex