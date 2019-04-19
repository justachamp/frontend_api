from django.utils.functional import cached_property

from payment_api.core.client import Client
from payment_api.serializers import PaymentAccountSerializer


class PaymentApiClient:

    def __init__(self, user):

        self._user = user

    def assign_payment_account(self):
        user = self._user
        payment_account_id = None
        if user and user.is_owner:
            serializer = PaymentAccountSerializer({'email': self._user.email})
            serializer.is_valid(True)
            data = serializer.save()
            payment_account_id = data.get('id')
        return payment_account_id
