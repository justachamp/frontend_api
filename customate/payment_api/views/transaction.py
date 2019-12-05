from rest_framework.permissions import IsAuthenticated

from payment_api.serializers import TransactionSerializer
from frontend_api.permissions import (
    IsSuperAdminOrReadOnly,
    IsOwnerOrReadOnly,
    SubUserManageSchedulesPermission,
    IsActive,
    IsNotBlocked
)
from payment_api.views import (
    InclusionFilter,
    OrderingFilter,
    SearchFilter,
    ResourceRelationshipView,
    ResourceFilterBackend,
    ResourceViewSet
)

from core.fields import UserRole



class TransactionViewSet(ResourceViewSet):
    resource_name = 'transactions'
    allowed_methods = ['head', 'get']
    serializer_class = TransactionSerializer
    permission_classes = (  IsAuthenticated, 
                            IsActive, 
                            IsNotBlocked,
                            IsSuperAdminOrReadOnly |
                            IsOwnerOrReadOnly |
                            SubUserManageSchedulesPermission )

    def check_payment_account_id(self, filters, key, value):
        # TODO: somehow receive users payment_account_id from client if request from admin
        if self.request.user.role == UserRole.admin:
            return self.get_queryset().set_empty_response()
        # Get and return users (owner) payment_account_id even if request from subuser
        user = self.request.user \
              if self.request.user.is_owner \
            else self.request.user.account.owner_account.user 
        return user.account.payment_account_id

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
        'payment__schedule_id': ('exact',),
        'payment__wallet_id': ('in', 'exact',),
    }

    class Meta:
        filters = [
            {'active__exact': 1},
            {'is_hidden__exact': 0},
            {'payment__account__id__exact': {'method': 'check_payment_account_id', 'force_override_filter': True}}
        ]


class TransactionRelationshipView(ResourceRelationshipView):
    serializer_class = TransactionSerializer
    resource_name = 'transactions'
    permission_classes = (  IsAuthenticated, 
                            IsActive, 
                            IsNotBlocked,
                            IsSuperAdminOrReadOnly |
                            IsOwnerOrReadOnly |
                            SubUserManageSchedulesPermission )

    def get_queryset(self):
        pass
