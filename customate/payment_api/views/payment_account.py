from rest_framework.permissions import AllowAny
from payment_api.serializers import PaymentAccountSerializer


from payment_api.views import (
    InclusionFiler,
    IbanGeneralPartFiler,
    ResourceFilterBackend,
    QueryParameterValidationFilter,
    OrderingFilter,
    SearchFilter,
    RelationshipView,
    ResourceViewSet
)


class PaymentAccountViewSet(ResourceViewSet):
    resource_name = 'payment_accounts'
    serializer_class = PaymentAccountSerializer
    permission_classes = (AllowAny,)

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
        filters = [{'active__exact': 1}]

    # ordering_fields = ('email',)
    #
    filter_backends = (
        IbanGeneralPartFiler,
        # QueryParameterValidationFilter,
        OrderingFilter,
        InclusionFiler,
        ResourceFilterBackend,
        SearchFilter
    )

    filterset_fields = {
        'active': ('exact',),
        'email': ('icontains', 'contains', 'iexact', 'exact')
    }
    # search_fields = ('email',)


class PaymentAccountRelationshipView(RelationshipView):
    serializer_class = PaymentAccountSerializer
    resource_name = 'payment_accounts'

    class Meta:
        external_resource_name = 'accounts'

