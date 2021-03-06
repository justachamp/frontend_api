# Generated by Django 2.2 on 2020-01-09 09:15
import logging

from django.core.paginator import Paginator
from django.db import migrations
import external_apis.payment.service as payment_service
from core.fields import UserRole
from core.models import User
from customate import settings

logger = logging.getLogger(__name__)


def update_payment_accounts(apps, schema_editor):
    """
    Update schedules & escrows payee fields with correct values
    :return:
    """

    users = User.objects.filter(
        role=UserRole.owner
    )
    logger.info("Process users (count=%s)" % users.count())
    paginator = Paginator(users, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for page in paginator.page_range:
        for user in paginator.page(page).object_list:  # type: User
            logger.info("Updating payment account (id=%s) for user (id=%s)"
                        % (user.account.payment_account_id, user.id))

            if user.account.payment_account_id is not None:
                payment_service.PaymentAccount.update(
                    user_account_id=user.account.payment_account_id,
                    email=user.email,
                    full_name=user.get_full_name()
                )


class Migration(migrations.Migration):

    dependencies = [
        ('frontend_api', '0068_business_info_verified_field'),
    ]

    operations = [
        migrations.RunPython(update_payment_accounts),
    ]
