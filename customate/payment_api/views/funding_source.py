from rest_framework.permissions import IsAuthenticated

from frontend_api.models import Schedule
from core.exceptions import ConflictError
from payment_api.serializers import FundingSourceSerializer, UpdateFundingSourceSerializer
from frontend_api.permissions import (
    IsSuperAdminOrReadOnly,
    IsOwnerOrReadOnly,
    SubUserManageFundingSourcesPermission,
    IsActive,
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
                            IsActive,
                            IsSuperAdminOrReadOnly |
                            IsOwnerOrReadOnly |
                            SubUserManageFundingSourcesPermission )

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
            {'account__id__exact': {'method': 'check_payment_account_id', 'force_override_filter': True}},
            {'currency__not_in': 'DK'}
        ]

    def get_serializer_class(self):
        return UpdateFundingSourceSerializer if self.request.method == 'PATCH' else FundingSourceSerializer

    def check_payment_account_id(self, filters, key, value):
        user = self.request.user
        try:
            payment_account_id = user.account.payment_account_id if \
                    user.is_owner else user.account.owner_account.payment_account_id

            if payment_account_id is None:
                self.get_queryset().set_empty_response()
            else:
                return payment_account_id
        except AttributeError:
            return None

    def perform_destroy(self, funding_source, *args, **kwargs):
        """
        Handle HTTP DELETE here.
        :return:
        """

        if Schedule.has_active_schedules_with_source(funding_source.id):
            raise ConflictError(f'Cannot remove funding source that is used in active schedule ({funding_source.id})')

        return super().perform_destroy(funding_source)


class FundingSourceRelationshipView(ResourceRelationshipView):
    serializer_class = FundingSourceSerializer
    resource_name = 'funding_sources'
    permission_classes = (  IsAuthenticated,
                            IsActive,
                            IsSuperAdminOrReadOnly |
                            IsOwnerOrReadOnly |
                            SubUserManageFundingSourcesPermission )
