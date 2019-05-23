
from payment_api.services import (
    BaseRequestResourceSerializerService as BaseService,
    RequestResourcePaymentAccountMixin as AccountMixin,
    RequestResourceQuerysetMixin as QuerysetMixin,

)


class PayeeRequestResourceService(BaseService, AccountMixin, QuerysetMixin):

    def get_wallet(self, currency):
        return self.queryset.filter(account__id=self.get_attr('payment_account_id', True), currency=currency).first()

    class Meta:
        resource_name = 'payees'
