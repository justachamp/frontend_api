from rest_framework.exceptions import ValidationError

from payment_api.core.views import ProxyView
from frontend_api.permissions import IsOwnerOrReadOnly
from payment_api.core.client import Client

from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework import response
from rest_framework_json_api.views import viewsets


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