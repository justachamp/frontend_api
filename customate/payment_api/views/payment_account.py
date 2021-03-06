from rest_framework.permissions import IsAuthenticated

from payment_api.serializers import PaymentAccountSerializer
from frontend_api.permissions import (
    IsSuperAdminOrReadOnly,
    IsOwnerOrReadOnly,
    IsActive,
    IsNotBlocked
)
from payment_api.views import (
    InclusionFilter,
    IbanGeneralPartFiler,
    ResourceFilterBackend,
    QueryParameterValidationFilter,
    OrderingFilter,
    SearchFilter,
    ResourceRelationshipView,
    ResourceViewSet
)


class PaymentAccountViewSet(ResourceViewSet):
    resource_name = 'payment_accounts'
    serializer_class = PaymentAccountSerializer
    permission_classes = (  IsAuthenticated, 
                            IsActive,
                            IsNotBlocked,
                            IsSuperAdminOrReadOnly |
                            IsOwnerOrReadOnly )

    def prepare_request_params(self):
        param = self.request.query_params.get('ibanGeneralPart')
        iban = param.strip() if param else None
        if iban:
            self.client.request_kwargs = {'params': {'ibanGeneralPart': iban}}

    def perform_create(self, *args, **kwargs):
        self.prepare_request_params()
        return super().perform_create(*args, **kwargs)

    class Meta:
        external_resource_name = 'accounts'
        filters = [
            {'active__exact': 1},
            {'is_virtual__exact': {'resource': 'wallets', 'value': 0}}
        ]
        resource_suffix_name = None

    # ordering_fields = ('email',)
    #
    filter_backends = (
        IbanGeneralPartFiler,
        # QueryParameterValidationFilter,
        OrderingFilter,
        InclusionFilter,
        ResourceFilterBackend,
        SearchFilter
    )

    filterset_fields = {
        'active': ('exact',),
        'email': ('icontains', 'contains', 'iexact', 'exact'),
        'is_virtual': ('exact',),
    }
    # search_fields = ('email',)


class PaymentAccountRelationshipView(ResourceRelationshipView):
    serializer_class = PaymentAccountSerializer
    resource_name = 'payment_accounts'
    permission_classes = (  IsAuthenticated, 
                            IsActive,
                            IsNotBlocked,
                            IsSuperAdminOrReadOnly |
                            IsOwnerOrReadOnly )

    class Meta:
        external_resource_name = 'accounts'

