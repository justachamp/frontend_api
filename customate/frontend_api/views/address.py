from rest_framework.decorators import action
from rest_framework import response
from rest_framework_json_api.views import RelationshipView

from core import views
from address.loqate.serializers import RetrieveAddressSerializer, SearchAddressSerializer

from frontend_api.models import Address
from frontend_api.serializers import UserAddressSerializer, CompanyAddressSerializer, AddressSerializer
from frontend_api.permissions import IsOwnerOrReadOnly, AllowAny

from ..views import PatchRelatedMixin

import logging
logger = logging.getLogger(__name__)


class AddressRelationshipView(RelationshipView):
    queryset = Address.objects
    serializer_class = AddressSerializer


class UserAddressViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = Address.objects.all()
    serializer_class = UserAddressSerializer
    permission_classes = (AllowAny,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user
        if not user.address:
            user.address = serializer.save()
            user.save()


class AddressViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = (AllowAny, )

    @action(methods=['POST'], detail=False, name='Search address')
    def search(self, request):
        data = request.data
        serializer = SearchAddressSerializer(data=data)
        if serializer.is_valid(True) and serializer.validated_data.get('text'):
            return response.Response(serializer.find(serializer.validated_data))

        return response.Response([])

    @action(methods=['POST'], detail=False, name='Retrieve address detail')
    def search_detail(self, request):
        data = request.data
        id = data.get('id')
        serializer = RetrieveAddressSerializer(data={'Id': id})
        if serializer.is_valid(True):
            return response.Response(serializer.retrieve(id))


class CompanyAddressViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = Address.objects.all()
    serializer_class = CompanyAddressSerializer
    permission_classes = (AllowAny,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user
        if not user.account.company.address:
            user.account.company.address = serializer.save()
            user.account.company.save()
