from rest_framework.permissions import AllowAny

from payment_api.serializers import WalletSerializer
from payment_api.views import (
    RelationshipView,
    ResourceViewSet
)


class WalletViewSet(ResourceViewSet):
    resource_name = 'wallets'
    serializer_class = WalletSerializer
    permission_classes = (AllowAny,)
    # ordering_fields = ('iban',)


class WalletRelationshipView(RelationshipView):
    serializer_class = WalletSerializer
    resource_name = 'wallets'
