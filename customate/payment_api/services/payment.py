from django.utils.functional import cached_property

from payment_api.services import (
    BaseRequestResourceSerializerService,
    RequestResourcePaymentAccountMixin,
    PayeeRequestResourceService
)


class BasePaymentRequestResourceService(BaseRequestResourceSerializerService, RequestResourcePaymentAccountMixin):
    pass


class FundsRequestResourceService(BasePaymentRequestResourceService):

    @cached_property
    def payee_service(self):
        return PayeeRequestResourceService(resource=self._resource, context=self._context)

    @property
    def currency(self):
        return self._resource.initial_data['currency']

    @property
    def payee_wallet_id_by_currency(self):
        payee = self.payee_service.get_wallet(self.currency)
        return payee.id

    def prepare_funds(self, attrs):

        attrs['userId'] = self.get_attr('user_id', True)
        attrs['recipient'] = self.payee_wallet_id_by_currency
        attrs['account'] = self.get_attr('payment_account_id', True)
        return attrs
