from rest_framework.permissions import AllowAny
from payment_api.serializers import TransactionSerializer

from payment_api.views import (
    InclusionFiler,
    OrderingFilter,
    SearchFilter,
    RelationshipView,
    ResourceViewSet
)


class TransactionViewSet(ResourceViewSet):
    resource_name = 'transactions'
    allowed_methods = ['head', 'get']
    serializer_class = TransactionSerializer
    permission_classes = (AllowAny,)

    filter_backends = (
        OrderingFilter,
        InclusionFiler,
        # ResourceFilterBackend,
        SearchFilter
    )


class TransactionRelationshipView(RelationshipView):
    serializer_class = TransactionSerializer
    resource_name = 'transactions'

    def get_queryset(self):
        pass