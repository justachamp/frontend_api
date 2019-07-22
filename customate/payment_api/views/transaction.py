from payment_api.serializers import TransactionSerializer
from frontend_api.permissions import (
    IsSuperAdminOrReadOnly,
    IsOwnerOrReadOnly,
    SubUserManageFundingSourcesPermission
)
from payment_api.views import (
    InclusionFilter,
    OrderingFilter,
    SearchFilter,
    ResourceRelationshipView,
    ResourceFilterBackend,
    ResourceViewSet
)


class TransactionViewSet(ResourceViewSet):
    resource_name = 'transactions'
    allowed_methods = ['head', 'get']
    serializer_class = TransactionSerializer
    permission_classes = (IsSuperAdminOrReadOnly|IsOwnerOrReadOnly|SubUserManageFundingSourcesPermission, )

    def check_payment_account_id(self, filters, key, value):
        user = self.request.user
        if not user.is_anonymous and user.is_owner and user.account.payment_account_id:
            return user.account.payment_account_id
        else:
            self.get_queryset().set_empty_response()

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        ResourceFilterBackend,
        SearchFilter
    )

    filterset_fields = {
        'status': ('exact',),
        'active': ('exact',),
        'is_hidden': ('exact',),
        'name': ('exact', 'not_in'),
        'payment__currency': ('exact',),
        'payment__payment_account__id': ('exact',),
        'execution_date': ('exact', 'eq', 'ne', 'gt', 'lt', 'gte', 'lte'),
        'completion_date': ('exact', 'eq', 'ne', 'gt', 'lt', 'gte', 'lte'),
        'payment__account__id': ('exact',),
    }

    class Meta:
        filters = [
            {'active__exact': 1},
            {'is_hidden__exact': 0},
            {'payment__account__id__exact': {'method': 'check_payment_account_id'}}
        ]


class TransactionRelationshipView(ResourceRelationshipView):
    serializer_class = TransactionSerializer
    resource_name = 'transactions'

    def get_queryset(self):
        pass
