from rest_framework.permissions import IsAuthenticated

from payment_api.serializers import WalletSerializer
from frontend_api.permissions import (
    IsSuperAdminOrReadOnly,
    IsOwnerOrReadOnly,
    IsActive,
    IsNotBlocked
)

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
    permission_classes = (  IsAuthenticated, 
                            IsActive,
                            IsNotBlocked,
                            IsSuperAdminOrReadOnly |
                            IsOwnerOrReadOnly )

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        ResourceFilterBackend,
        SearchFilter
    )

    filterset_fields = {
        'active': ('exact',),
        'is_virtual': ('exact',),
        'account__id': ('exact',),
        'currency': ('exact', 'not_in'),
    }

    def check_payment_account_id(self, filters, key, value):
        user = self.request.user
        if not user.is_anonymous and user.is_owner and user.account.payment_account_id:
            return user.account.payment_account_id
        else:
            self.get_queryset().set_empty_response()

    class Meta:
        filters = [
            {'active__exact': 1},
            {'is_virtual__exact': 0},
            {'account__id__exact': {'method': 'check_payment_account_id', 'force_override_filter': True}},
            {'currency__not_in': 'DK'},
        ]


class WalletRelationshipView(ResourceRelationshipView):
    serializer_class = WalletSerializer
    resource_name = 'wallets'
    permission_classes = (  IsAuthenticated, 
                            IsActive,
                            IsNotBlocked,
                            IsSuperAdminOrReadOnly |
                            IsOwnerOrReadOnly )
