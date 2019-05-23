
from payment_api.services import (
    BaseRequestResourceSerializerService as BaseService,
    RequestResourcePaymentAccountMixin as AccountMixin,
    RequestResourceQuerysetMixin as QuerysetMixin,

)


class PayeeRequestResourceService(BaseService, AccountMixin, QuerysetMixin):

    def get_wallet(self, currency):
        return self.queryset.filter(account__id=self.payment_account_id, currency=currency).first()

    class Meta:
        resource_name = 'payees'
