from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from core.models import User
from frontend_api.notifications.helpers import get_ses_email_payload
from frontend_api.tasks.notifiers import send_notification_email, send_notification_sms


class Command(BaseCommand):
    """
    Usage: ./manage.py notify_about_valid_funding_source --user_email="some_mail@mail.com" --fs_title="Some title"
    """
    help = 'Send SMS & email notification about validated funding source (if notification settings are turned on)'

    def add_arguments(self, parser):
        parser.add_argument('--user_email', type=str, help='User email')
        parser.add_argument('--fs_title', type=str, help='Funding source title')

    def handle(self, *args, **options):
        user_email = options.get('user_email')
        fs_title = options.get('fs_title')

        if not user_email:
            raise CommandError('User email must be specified')
        if not fs_title:
            raise CommandError('Funding source title must be specified')

        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            raise CommandError("Unable to fetch user with email: %s." % user_email)

        if not any([user.notify_by_email, user.notify_by_phone]):
            self.stdout.write("Current user refused the both email and sms notifications.")
            return

        # Sending email notification if allowed by user
        if user.notify_by_email:
            context = {"fs_title": fs_title}
            email_message = get_ses_email_payload(
                tpl_filename="notifications/funding_source_validated.html",
                tpl_context=context,
                subject=settings.AWS_SES_SUBJECT_NAME
            )
            # Network errors get handled inside involved function
            send_notification_email.delay(to_address=user_email, message=email_message)

        # Sending sms notification if allowed by user
        if user.notify_by_phone:
            sms_message = "".join(
                [
                    "The DirectDebit was validated.",
                    "\nSource name: %s" % fs_title.capitalize(),
                    "\nSource validation status: Valid"
                 ]
            )
            # Network errors get handled inside involved function
            send_notification_sms.delay(to_phone_number=user.phone_number, message=sms_message)

        self.stdout.write("Done.")

