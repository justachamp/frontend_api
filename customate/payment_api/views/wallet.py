from rest_framework.permissions import AllowAny

from payment_api.serializers import WalletSerializer


from payment_api.views import (
    InclusionFiler,
    OrderingFilter,
    SearchFilter,
    ResourceRelationshipView,
    ResourceViewSet
)


class WalletViewSet(ResourceViewSet):
    resource_name = 'wallets'
    serializer_class = WalletSerializer
    permission_classes = (AllowAny,)

    filter_backends = (
        OrderingFilter,
        InclusionFiler,
        # ResourceFilterBackend,
        SearchFilter
    )


class WalletRelationshipView(ResourceRelationshipView):
    serializer_class = WalletSerializer
    resource_name = 'wallets'
