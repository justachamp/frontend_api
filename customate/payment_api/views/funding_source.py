from rest_framework.permissions import IsAuthenticated

from payment_api.serializers import FundingSourceSerializer, UpdateFundingSourceSerializer
from frontend_api.permissions import (
    IsSuperAdminOrReadOnly,
    IsOwnerOrReadOnly,
    SubUserManageFundingSourcesPermission
)
from payment_api.views import (
    InclusionFilter,
    OrderingFilter,
    SearchFilter,
    ResourceFilterBackend,
    ResourceRelationshipView,
    ResourceViewSet
)


class FundingSourceViewSet(ResourceViewSet):
    resource_name = 'funding_sources'
    paginate_response = False
    serializer_class = FundingSourceSerializer
    permission_classes = (  IsAuthenticated,
                            IsSuperAdminOrReadOnly|
                            IsOwnerOrReadOnly|
                            SubUserManageFundingSourcesPermission,)

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        ResourceFilterBackend,
        SearchFilter
    )

    filterset_fields = {
        'status': ('exact',),
        'active': ('exact',),
        'account__id': ('exact',),
        'type': ('exact',),
        'currency': ('exact', 'not_in')
    }

    class Meta:
        filters = [
            {'active__exact': 1},
            {'account__id__exact': {'method': 'check_payment_account_id'}},
            {'currency__not_in': 'DK'}
        ]

    def get_serializer_class(self):
        return UpdateFundingSourceSerializer if self.request.method == 'PATCH' else FundingSourceSerializer

    def check_payment_account_id(self, filters, key, value):
        user = self.request.user
        try:
            return user.account.payment_account_id if \
                    user.is_owner else user.account.owner_account.payment_account_id
        except AttributeError:
            return None


class FundingSourceRelationshipView(ResourceRelationshipView):
    serializer_class = FundingSourceSerializer
    resource_name = 'funding_sources'
