import logging
from traceback import format_exc

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework import response
from rest_framework_json_api.views import RelationshipView

from external_apis.loqate.service import find_address

from core import views

from frontend_api.models import Address
from frontend_api.serializers import UserAddressSerializer, CompanyAddressSerializer, AddressSerializer
from frontend_api.views.mixins import PatchRelatedMixin

logger = logging.getLogger(__name__)


class AddressRelationshipView(RelationshipView):
    queryset = Address.objects
    serializer_class = AddressSerializer


class UserAddressViewSet(PatchRelatedMixin, views.ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = UserAddressSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        logger.info("perform_create")
        user = self.request.user
        if not user.address:
            user.address = serializer.save()
            user.save()


class CompanyAddressViewSet(PatchRelatedMixin, views.ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = CompanyAddressSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        logger.info("perform_create")
        user = self.request.user
        if not user.account.company.address:
            user.account.company.address = serializer.save()
            user.account.company.save()


# class AddressViewSet(PatchRelatedMixin, views.ModelViewSet):
class AddressViewSet(views.ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = (IsAuthenticated,)

    @action(methods=['POST'], detail=False, name='Search address')
    def search(self, request):
        res = []
        data = request.data
        logger.info("Calling search,data=%r" % data)
        try:
            for r in find_address(params=data):
                res.append(
                    dict((k.lower(), v) for k, v in r.items())
                )
        except Exception as e:
            logger.error("Find address failed, request.data=%r, exc=%r" % (data, format_exc()))
        return response.Response(res)

    # @action(methods=['POST'], detail=False, name='Retrieve address detail')
    # def search_detail(self, request):
    #     data = request.data
    #     logger.info("Calling search_detail: %r" % data)
    #     id = data.get('id')
    #     serializer = RetrieveAddressSerializer(data={'Id': id})
    #     if serializer.is_valid(True):
    #         return response.Response(serializer.retrieve(id))
