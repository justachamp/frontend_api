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
        # ResourceFilterBackend,
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
        # ResourceFilterBackend,
        SearchFilter
    )


class PaymentRelationshipView(ResourceRelationshipView):
    serializer_class = PaymentSerializer
    resource_name = 'payments'


{'data':
     {'type': 'payments',
      'attributes': {'currency': 'EUR', 'scenario': 'CreditCardToCustomate', 'data': {'amount': 100, 'description': 'Load funds test'}},
      'relationships': {'account': {'data': {'id': '7b83a0a3-ee3d-4ec1-9404-0184c48b1ad4', 'type': 'account'}},
                        'origin': {'data': {'id': 'c5af2e0e-f35d-4fff-ab51-232e64389371', 'type': 'origin'}},
                        'recipient': {'data': {'id': '26e025ac-a51f-e36d-d796-605634a26a4e', 'type': 'recipient'}}}}}

