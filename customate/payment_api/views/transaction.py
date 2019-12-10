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

    def define_payment_account_id(self, filters, key, value):
        # TODO: somehow receive users payment_account_id from client if request from admin
        if self.request.user.role == UserRole.admin:
            return self.get_queryset().set_empty_response()

        user = self.request.user \
            if self.request.user.is_owner \
            else self.request.user.account.owner_account.user

        """
            Main purpose of this walletIds verifications is to make sure that we will filter transactions with CORRECT
            "payment_account_id" (in general we MUST not return transactions that belong to another account), incoming
            "payment__account__id" parameter is not trusted in this case (just like any other), we need to find out and 
            set appropriate value ourselves
            
            Escrow's wallet is the main cause of this changes - there is a requirement to show Escrow's transactions to
            funder AND recipient, but nuance is that Escrow's wallet belongs ONLY to funder (we just don't provide a 
            possibility to interact with it directly), so in fact we created a way for recipient to see transactions
            from someone else's account (which is risky and we have to double-check everything) 
        """
        wallet_ids = self.request.query_params.get('filter[payment__wallet_id.in]')
        if isinstance(wallet_ids, str):
            wallet_ids = wallet_ids.split(',')

            if len(wallet_ids) == 1:
                from frontend_api.models import Escrow
                escrow = Escrow.objects.filter(wallet_id=wallet_ids[0]).first()  # type: Escrow

                if escrow is not None and user.id in [escrow.funder_user.id, escrow.recipient_user.id]:
                    return escrow.funder_payment_account_id

        # Get and return users (owner) payment_account_id even if request from subuser
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
        'payment__schedule_id': ('exact',),
        'payment__wallet_id': ('in', 'exact',),
        # "payment__account__id" property MUST be set after "payment__wallet_id", because we rely on it in our
        # calculations ("define_payment_account_id" method)
        'payment__account__id': ('exact',),
    }

    class Meta:
        filters = [
            {'active__exact': 1},
            {'is_hidden__exact': 0},
            {'payment__account__id__exact': {'method': 'define_payment_account_id', 'force_override_filter': True}}
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
