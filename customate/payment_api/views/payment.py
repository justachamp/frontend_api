from rest_framework.permissions import IsAuthenticated

from payment_api.serializers import PaymentSerializer, LoadFundsSerializer
from frontend_api.permissions import (
    IsSuperAdminOrReadOnly,
    IsOwnerOrReadOnly,
    SubUserLoadFundsPermission,
    SubUserManageSchedulesPermission,
    IsActive,
    IsNotBlocked,
    IsVerified)
from payment_api.serializers.payment import MakingPaymentSerializer
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
    permission_classes = (IsAuthenticated,
                          IsActive,
                          IsNotBlocked,
                          IsSuperAdminOrReadOnly |
                          IsOwnerOrReadOnly |
                          SubUserLoadFundsPermission)

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        SearchFilter
    )


class PaymentViewSet(ResourceViewSet):
    resource_name = 'payments'
    allowed_methods = ['head', 'get']
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,
                          IsActive,
                          IsNotBlocked,
                          IsSuperAdminOrReadOnly |
                          IsOwnerOrReadOnly |
                          SubUserManageSchedulesPermission)

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        SearchFilter
    )


class MakePaymentViewSet(ResourceViewSet):
    resource_name = 'payments'
    allowed_methods = ['post']
    serializer_class = MakingPaymentSerializer
    permission_classes = (IsAuthenticated,
                          IsActive,
                          IsNotBlocked,
                          IsVerified,
                          IsSuperAdminOrReadOnly |
                          IsOwnerOrReadOnly |
                          SubUserManageSchedulesPermission)

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        SearchFilter
    )


class PaymentRelationshipView(ResourceRelationshipView):
    resource_name = 'payments'
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,
                          IsActive,
                          IsNotBlocked,
                          IsSuperAdminOrReadOnly |
                          IsOwnerOrReadOnly |
                          SubUserManageSchedulesPermission)


class ForcePaymentViewSet(PaymentViewSet):
    resource_name = 'forced_payments'
    allowed_methods = ['post']
    permission_classes = (IsAuthenticated,
                          IsActive,
                          IsNotBlocked,
                          IsSuperAdminOrReadOnly |
                          IsOwnerOrReadOnly |
                          SubUserManageSchedulesPermission)

    filter_backends = ()
