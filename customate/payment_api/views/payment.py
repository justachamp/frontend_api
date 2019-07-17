from payment_api.serializers import PaymentSerializer, LoadFundsSerializer
from frontend_api.permissions import (
    IsSuperAdminOrReadOnly,
    IsOwnerOrReadOnly,
    SubUserLoadFundsPermission
)
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
    permission_classes = (IsSuperAdminOrReadOnly|IsOwnerOrReadOnly|SubUserLoadFundsPermission,)

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        SearchFilter
    )


class PaymentViewSet(ResourceViewSet):
    resource_name = 'payments'
    allowed_methods = ['head', 'get']
    serializer_class = PaymentSerializer
    permission_classes = (IsSuperAdminOrReadOnly|IsOwnerOrReadOnly,)

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        SearchFilter
    )


class PaymentRelationshipView(ResourceRelationshipView):
    resource_name = 'payments'
    serializer_class = PaymentSerializer
