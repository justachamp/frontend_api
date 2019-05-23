from rest_framework.permissions import AllowAny
from payment_api.serializers import PaymentSerializer, LoadFundsSerializer

from payment_api.views import (
    InclusionFilter,
    OrderingFilter,
    SearchFilter,
    ResourceRelationshipView,
    ResourceViewSet
)


class LoadFundsViewSet(ResourceViewSet):
    resource_name = 'funds'
    allowed_methods = ['post']
    serializer_class = LoadFundsSerializer
    permission_classes = (AllowAny,)

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        SearchFilter
    )


class PaymentViewSet(ResourceViewSet):
    resource_name = 'payments'
    allowed_methods = ['head', 'get']
    serializer_class = PaymentSerializer
    permission_classes = (AllowAny,)

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        SearchFilter
    )


class PaymentRelationshipView(ResourceRelationshipView):
    serializer_class = PaymentSerializer
    resource_name = 'payments'

