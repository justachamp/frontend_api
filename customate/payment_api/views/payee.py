from rest_framework.permissions import IsAuthenticated
from payment_api.serializers import PayeeSerializer, UpdatePayeeSerializer
from frontend_api.permissions import (
    IsSuperAdminOrReadOnly,
    IsOwnerOrReadOnly,
    SubUserManagePayeesPermission
)
from payment_api.views import (
    InclusionFilter,
    OrderingFilter,
    SearchFilter,
    ResourceFilterBackend,
    ResourceRelationshipView,
    ResourceViewSet
)


class PayeeViewSet(ResourceViewSet):
    resource_name = 'payees'
    paginate_response = False
    serializer_class = PayeeSerializer
    permission_classes = ( IsAuthenticated, 
                           IsSuperAdminOrReadOnly|
                           IsOwnerOrReadOnly|
                           SubUserManagePayeesPermission,)

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        ResourceFilterBackend,
        SearchFilter
    )

    def get_serializer_class(self):
        return UpdatePayeeSerializer if self.request.method == 'PATCH' else PayeeSerializer

    def check_payment_account_id(self, filters, key, value):
        user = self.request.user
        if not user.is_anonymous and user.is_owner and user.account.payment_account_id:
            return user.account.payment_account_id
        else:
            self.get_queryset().set_empty_response()

    filterset_fields = {
        'type': ('exact', 'not_in', 'in'),
        'active': ('exact',),
        'account__id': ('exact',),
        'currency': ('exact', 'not_in')
    }

    class Meta:
        filters = [
            {'active__exact': 1},
            {'account__id__exact': {'method': 'check_payment_account_id'}},
            {'currency__not_in': 'DK'},
            {'type__exact': 'BANK_ACCOUNT'}
        ]


class PayeeRelationshipView(ResourceRelationshipView):
    serializer_class = PayeeSerializer
    resource_name = 'payees'
