from rest_framework.permissions import AllowAny
from payment_api.serializers import PaymentSerializer

from payment_api.views import (
    InclusionFiler,
    OrderingFilter,
    SearchFilter,
    RelationshipView,
    ResourceViewSet
)


class PaymentViewSet(ResourceViewSet):
    resource_name = 'payments'
    allowed_methods = ['head', 'get']
    serializer_class = PaymentSerializer
    permission_classes = (AllowAny,)

    filter_backends = (
        OrderingFilter,
        InclusionFiler,
        # ResourceFilterBackend,
        SearchFilter
    )


class PaymentRelationshipView(RelationshipView):
    serializer_class = PaymentSerializer
    resource_name = 'payments'

    def get_queryset(self):
        pass