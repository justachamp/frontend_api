from rest_framework.permissions import AllowAny
from payment_api.serializers import TaxSerializer

from payment_api.views import (
    InclusionFiler,
    IbanGeneralPartFiler,
    QueryParameterValidationFilter,
    OrderingFilter,
    SearchFilter,
    RelationshipView,
    ResourceViewSet
)


class TaxViewSet(ResourceViewSet):
    resource_name = 'taxes'
    serializer_class = TaxSerializer
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

    # ordering_fields = ('email',)
    #
    filter_backends = (
        IbanGeneralPartFiler,
        # QueryParameterValidationFilter,
        OrderingFilter,
        InclusionFiler,
        # ResourceFilterBackend,
        SearchFilter
    )
    #
    # filterset_fields = {
    #     'active': ('exact',),
    #     'email': ('icontains', 'contains', 'iexact', 'exact')
    # }
    # search_fields = ('email',)


class TaxRelationshipView(RelationshipView):
    pass
