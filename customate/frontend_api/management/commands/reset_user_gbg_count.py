from django.core.management.base import BaseCommand, CommandError
from core.models import User
from frontend_api.models import Account


class Command(BaseCommand):
    help = 'Reset GBG authenication count for specific user'

    def add_arguments(self, parser):
        parser.add_argument('user_email', type=str, help='User email'),

    def handle(self, *args, **options):

        if not options.get('user_email'):
            raise CommandError('User email must be specified')

        user_email = options.get('user_email')
        user = None
        try:
            self.stdout.write("Fetching user with email=%s" % user_email)
            user = User.objects.get(email=user_email)
        except Exception:
            raise CommandError("Unable to fetch user with email=%s" % user_email)

        account = user.account  # type: Account
        self.stdout.write("GBG info: %r" % account.gbg)
        account.gbg_authentication_count = 0
        account.save()
        self.stdout.write("new GBG info: %r" % account.gbg)
