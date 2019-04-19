


from payment_api.serializers import PaymentAccountSerializer

class PaymentApiClient:

    def __init__(self, user):

        self._user = user

    def assign_payment_account(self):
        user = self._user
        payment_account_id = None
        if user and user.is_owner:
            from payment_api.views import PaymentAccountViewSet
            view = PaymentAccountViewSet()
            serializer = PaymentAccountSerializer(data={'email': self._user.email}, context={'view': view})
            serializer.is_valid(True)
            data = serializer.save()
            payment_account_id = data.id
        return payment_account_id
