from rest_framework.permissions import IsAuthenticated

from core.exceptions import ConflictError
from core.fields import UserRole
from frontend_api.models import Schedule
from payment_api.serializers import PayeeSerializer, UpdatePayeeSerializer
from frontend_api.permissions import (
    IsSuperAdminOrReadOnly,
    IsOwnerOrReadOnly,
    SubUserManagePayeesPermission,
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


class PayeeViewSet(ResourceViewSet):
    resource_name = 'payees'
    paginate_response = False
    serializer_class = PayeeSerializer
    permission_classes = (IsAuthenticated,
                          IsActive, 
                          IsNotBlocked, 
                          IsSuperAdminOrReadOnly |
                          IsOwnerOrReadOnly |
                          SubUserManagePayeesPermission )

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        ResourceFilterBackend,
        SearchFilter
    )

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

    def get_serializer_class(self):
        return UpdatePayeeSerializer if self.request.method == 'PATCH' else PayeeSerializer

    def check_payment_account_id(self, filters, key, value):
        # TODO: somehow receive users payment_account_id from client if request from admin
        if self.request.user.role == UserRole.admin:
            return self.get_queryset().set_empty_response()
        # Get and return users (owner) payment_account_id even if request from subuser
        user = self.request.user \
            if self.request.user.is_owner \
            else self.request.user.account.owner_account.user
        return user.account.payment_account_id

    def perform_destroy(self, payee, *args, **kwargs):
        """
        Handle HTTP DELETE here.
        :return:
        """

        if Schedule.has_active_schedules_with_payee(payee.id):
            raise ConflictError(f'Cannot remove payee that is used in active schedule ({payee.id})')

        return super().perform_destroy(payee)


class PayeeRelationshipView(ResourceRelationshipView):
    serializer_class = PayeeSerializer
    resource_name = 'payees'
    permission_classes = (IsAuthenticated,
                          IsActive, 
                          IsNotBlocked, 
                          IsSuperAdminOrReadOnly |
                          IsOwnerOrReadOnly |
                          SubUserManagePayeesPermission )
