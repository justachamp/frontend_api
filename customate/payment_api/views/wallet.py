from rest_framework.permissions import AllowAny

from payment_api.serializers import WalletSerializer


from payment_api.views import (
    InclusionFilter,
    OrderingFilter,
    SearchFilter,
    ResourceFilterBackend,
    ResourceRelationshipView,
    ResourceViewSet
)


class WalletViewSet(ResourceViewSet):
    resource_name = 'wallets'
    serializer_class = WalletSerializer
    permission_classes = (AllowAny,)

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        ResourceFilterBackend,
        SearchFilter
    )

    filterset_fields = {
        'account__id': ('exact',),
    }

    def check_payment_account_id(self, filters, key, value):
        user = self.request.user
        if not user.is_anonymous and user.is_owner and user.account.payment_account_id:
            return user.account.payment_account_id
        else:
            self.get_queryset().set_empty_response()

    class Meta:
        filters = [
            {'account__id__exact': {'method': 'check_payment_account_id'}}
        ]


class WalletRelationshipView(ResourceRelationshipView):
    serializer_class = WalletSerializer
    resource_name = 'wallets'
