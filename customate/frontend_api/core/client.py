from payment_api.serializers import PaymentAccountSerializer


class PaymentApiClient:

    def __init__(self, user):

        self._user = user

    def assign_payment_account(self):
        user = self._user
        payment_account_id = None
        if user and user.is_owner and user.is_verified and not user.account.payment_account_id:
            from payment_api.views import PaymentAccountViewSet
            view = PaymentAccountViewSet()
            serializer = PaymentAccountSerializer(
                data={
                    'email': self._user.email,
                    'full_name': self._user.get_full_name(),
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
