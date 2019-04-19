from rest_framework.permissions import AllowAny
from payment_api.serializers import TransactionSerializer

from payment_api.views import (
    InclusionFiler,
    OrderingFilter,
    SearchFilter,
    RelationshipView,
    ResourceFilterBackend,
    ResourceViewSet
)

SYSTEM_TRANSACTIONS = (
    'IncomingContributionTransactionWorker',
    'LockTransactionWorker',
    'ReleaseTransactionWorker',
    'LockTransactionWorker',
    'InternalFeeAndTaxTransactionWorker',
    'MoneyInBtFeeAndTaxTransactionWorker',
    'MoneyInCcFeeAndTaxTransactionWorker',
    'MoneyInDdFeeAndTaxTransactionWorker',
    'MoneyOutBtFeeAndTaxTransactionWorker',
    'CustomateToIbanTransactionWorker'
)


class TransactionViewSet(ResourceViewSet):
    resource_name = 'transactions'
    allowed_methods = ['head', 'get']
    serializer_class = TransactionSerializer
    permission_classes = (AllowAny,)

    filter_backends = (
        OrderingFilter,
        InclusionFiler,
        ResourceFilterBackend,
        SearchFilter
    )

    filterset_fields = {
        'status': ('exact',),
        'active': ('exact',),
        'name': ('exact', 'not_in'),
        'payment__currency': ('exact',),
        'execution_date': ('exact', 'eq', 'ne', 'gt', 'lt', 'gte', 'lte')
    }

    class Meta:
        filters = [
            {'name__not_in': ','.join(SYSTEM_TRANSACTIONS)},
            {'active__exact': 1}
        ]


class TransactionRelationshipView(RelationshipView):
    serializer_class = TransactionSerializer
    resource_name = 'transactions'

    def get_queryset(self):
        pass
