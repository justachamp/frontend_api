from rest_framework.permissions import AllowAny
from payment_api.serializers import TransactionSerializer

from payment_api.views import (
    InclusionFilter,
    OrderingFilter,
    SearchFilter,
    ResourceRelationshipView,
    ResourceFilterBackend,
    ResourceViewSet
)

SYSTEM_TRANSACTIONS = (
    # 'IncomingContribution',
    'Lock',
    'Release',
    'InternalFeeAndTax',
    'MoneyInBtFeeAndTax',
    'MoneyInCcFeeAndTax',
    'MoneyInDdFeeAndTax',
    'MoneyOutBtFeeAndTax',
    # 'CustomateToIban'
)


class TransactionViewSet(ResourceViewSet):
    resource_name = 'transactions'
    allowed_methods = ['head', 'get']
    serializer_class = TransactionSerializer
    permission_classes = (AllowAny,)

    # def get_queryset(self):
    #     queryset = super().get_queryset()
    #     user = self.request.user
    #     if not user.is_anonymous and user.is_owner and user.account.payment_account_id:
    #         # self.Meta.filters.append({'payment__payment_account__id__exact': user.account.payment_account_id})
    #
    #         queryset.apply_filter({'payment__account__id': user.account.payment_account_id})
    #     else:
    #         queryset.set_empty_response()
    #
    #     return queryset

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
        'name': ('exact', 'not_in'),
        'payment__currency': ('exact',),
        'payment__payment_account__id': ('exact',),
        'execution_date': ('exact', 'eq', 'ne', 'gt', 'lt', 'gte', 'lte'),
        'completion_date': ('exact', 'eq', 'ne', 'gt', 'lt', 'gte', 'lte'),
        'payment__account__id': ('exact',),
    }

    class Meta:
        filters = [
            {'name__not_in': ','.join(SYSTEM_TRANSACTIONS)},
            {'active__exact': 1},
            {'payment__account__id__exact': {'method': 'check_payment_account_id'}}
        ]


class TransactionRelationshipView(ResourceRelationshipView):
    serializer_class = TransactionSerializer
    resource_name = 'transactions'

    def get_queryset(self):
        pass
