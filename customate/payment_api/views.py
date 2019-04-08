from rest_framework.exceptions import ValidationError

from payment_api.core.views import ProxyView
from frontend_api.permissions import IsOwnerOrReadOnly
from payment_api.core.client import Client

from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework import response
from rest_framework_json_api.views import viewsets
from payment_api.core.resource.filters import InclusionFiler, IbanGeneralPartFiler
from payment_api.serializers import PaymentAccountSerializer, WalletSerializer

from rest_framework_json_api import filters
from rest_framework.filters import SearchFilter


from rest_framework_json_api.views import RelationshipView
from payment_api.core.resource.views import ResourceViewSet


class ItemListProxy(ProxyView):
    """
    List of items
    """
    permission_classes = (IsOwnerOrReadOnly,)
    resource_name = 'identity'
    source = 'auth/sign_in/'
    verify_ssl = False
    return_raw = True


class SignUpProxy(viewsets.ViewSet):
    resource_name = 'identity'
    resource = 'sign_in'
    permission_classes = (AllowAny,)

    @action(methods=['POST'], detail=False, name='Sign up', resource_name='identity')
    def sign_in(self, request):
        api = Client()
        resource = api.client.create('identity', **request.data)
        try:
            resource.commit('https://dev-api.gocustomate.com/auth/sign_in/')
        except Exception as ex:
            resp = ex.response.json()
            errors = resp.get('errors')
            data = {error.get('source', {}).get('pointer'): error.get('detail', '') for error in errors}
            raise ValidationError(data)

        return response.Response(resource.json)

    @action(methods=['POST'], detail=False, name='Sign up', resource_name='identity')
    def sign_in(self, request):
        api = Client('https://dev-api.gocustomate.com/auth/')
        resource = api.client.create('identity', **request.data)
        try:
            resource.commit('https://dev-api.gocustomate.com/auth/sign_in/')
        except Exception as ex:
            resp = ex.response.json()
            errors = resp.get('errors')
            data = {error.get('source', {}).get('pointer'): error.get('detail', '') for error in errors}
            raise ValidationError(data)

        return response.Response(resource.json)

    def get_queryset(self):
        client = Client()
        return client.get(self.resource)


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

    # ordering_fields = ('email',)
    #
    filter_backends = (
        IbanGeneralPartFiler,
        # filters.QueryParameterValidationFilter,
        filters.OrderingFilter,
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


class PaymentAccountRelationshipView(RelationshipView):
    # queryset = Address.objects
    pass


class WalletRelationshipView(RelationshipView):
    # queryset = Address.objects
    pass


class WalletViewSet(ResourceViewSet):
    resource_name = 'wallets'
    serializer_class = WalletSerializer
    permission_classes = (AllowAny,)
    # ordering_fields = ('iban',)
