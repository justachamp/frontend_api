import logging

from django.utils.functional import cached_property
from traceback import format_exc
from customate import settings
from payment_api.core.client import Client
from payment_api.serializers import PaymentAccountSerializer
from payment_api.services.schedule import ScheduleRequestResourceService

logger = logging.getLogger(__name__)


class PaymentApiClient:
    _base_url = settings.PAYMENT_API_URL

    def __init__(self, user):
        self._user = user

    @cached_property
    def client(self):
        return Client(self._base_url)

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
        try:
            logger.debug(f'cancel_schedule_payments started')
            resource_type = 'schedule_payments'
            self.client.delete(resource_type, schedule_id)
        except Exception as e:
            logger.error("Schedule payments cancellation thrown an exception: %r" % format_exc())
            raise e

    def get_schedule_payments_details(self, schedule_id):
        try:
            logger.debug(f'get_schedule_payments_details started')
            service = ScheduleRequestResourceService(resource=self)
            schedule_payments_details = service.get_schedule_payment_details(schedule_id)

            return schedule_payments_details.totalPaidSum
        except Exception as e:
            logger.error("Receiving schedule payments details thrown an exception: %r" % format_exc())
            raise e
