from jsonapi_client.resourceobject import ResourceObject

from core.fields import PayeeType
from payment_api.services import (
    BaseRequestResourceSerializerService as BaseService,
    RequestResourcePaymentAccountMixin as AccountMixin,
    RequestResourceQuerysetMixin as QuerysetMixin
)


class PayeeRequestResourceService(BaseService, AccountMixin, QuerysetMixin):
    def get_payee_details(self, payee_id) -> ResourceObject:
        return self.queryset.one(payee_id)

    def get_wallet(self, currency):
        return self.queryset.filter(
            account__id=self.get_attr('payment_account_id', True),
            type=PayeeType.WALLET.value,
            currency=currency).first()

    class Meta:
        resource_name = 'payees'
