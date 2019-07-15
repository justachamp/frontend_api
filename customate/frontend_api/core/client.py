import logging

from django.utils.functional import cached_property
from traceback import format_exc
from jsonapi_client import Filter
from jsonapi_client.common import HttpStatus
from customate import settings
from payment_api.core.client import Session
from payment_api.serializers import PaymentAccountSerializer

logger = logging.getLogger(__name__)


class PaymentApiClient:
    _base_url = settings.PAYMENT_API_URL

    def __init__(self, user):
        self._user = user

    def assign_payment_account(self):
        user = self._user
        payment_account_id = None
        if user and user.is_owner and user.contact_verified and not user.account.payment_account_id:
            from payment_api.views import PaymentAccountViewSet
            view = PaymentAccountViewSet()
            serializer = PaymentAccountSerializer(
                data={
                    'email': user.email,
                    'full_name': user.get_full_name() or user.email,
                    'original_account_id': user.account.id
                },
                context={'view': view}
            )
            serializer.is_valid(True)
            data = serializer.save()
            payment_account_id = data.id
            user.account.payment_account_id = payment_account_id
            user.account.save()
        return payment_account_id

    def cancel_schedule_payments(self, schedule_id):
        resource_type = 'payments'
        filters = Filter(payments__scheduleId=schedule_id)

        try:
            logger.debug(f'cancel_schedule_payments started')
            status_code, response, _ = self.client.remove_by_filters(resource_type, filters)
            if status_code != HttpStatus.NO_CONTENT_204:
                logger.error("Schedule payments cancellation received unexpected response: %s", response)
        except Exception as e:
            logger.error("Schedule payments cancellation thrown an exception: %r" % format_exc())
            raise e

    @cached_property
    def client(self):
        return Session(self._base_url, schema={})
