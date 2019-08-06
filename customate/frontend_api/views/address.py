import logging
import re
from traceback import format_exc

from rest_framework import response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import ValidationError
from rest_framework_json_api.views import RelationshipView

from external_apis.loqate.service import find_address, retrieve_address, LoqateError

from core import views

from frontend_api.models import Address
from frontend_api.serializers import UserAddressSerializer, CompanyAddressSerializer, AddressSerializer
from frontend_api.views.mixins import PatchRelatedMixin
from frontend_api.permissions import IsActive, IsOwnerOrReadOnly

logger = logging.getLogger(__name__)


def camelcase_to_snakecase(name):
    """
    CamelCase - > camel_case
    :param name:
    :return:
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class AddressRelationshipView(RelationshipView):
    queryset = Address.objects
    serializer_class = AddressSerializer
    permission_classes = ( IsAuthenticated,
                           IsActive,
                           IsOwnerOrReadOnly )


class UserAddressViewSet(PatchRelatedMixin, views.ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = UserAddressSerializer
    permission_classes = ( IsAuthenticated,
                           IsActive,
                           IsOwnerOrReadOnly )

    def perform_create(self, serializer):
        logger.info("perform_create")
        user = self.request.user
        if not user.address:
            user.address = serializer.save()
            user.save()


class CompanyAddressViewSet(PatchRelatedMixin, views.ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = CompanyAddressSerializer
    permission_classes = ( IsAuthenticated,
                           IsActive,
                           IsOwnerOrReadOnly )

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
    permission_classes = ( IsAuthenticated,
                           IsActive )

    @action(methods=['POST'], detail=False, name='Search address')
    def search(self, request):
        """
        Returns the list of suggested addresses
        :param request:
        :return:
        """
        res = []
        data = request.data
        logger.info("Calling search,data=%r" % data)
        try:
            for r in find_address(params=data):
                res.append(
                    dict((camelcase_to_snakecase(k), v) for k, v in r.items())
                )
        except LoqateError as e:
            raise ValidationError(str(e))
        except Exception as e:
            logger.error("Find address failed, request.data=%r, exc=%r" % (data, format_exc()))
        return response.Response(res)

    @action(methods=['POST'], detail=False, name='Retrieve address detail')
    def search_detail(self, request):
        """
        Returns full Address details for a specific address ID
        :param request:
        :return:
        """
        res = []
        data = request.data
        logger.info("Calling search_detail: %r" % data)
        try:
            for r in retrieve_address(params=data):
                res.append(
                    dict((camelcase_to_snakecase(k), v) for k, v in r.items())
                )
        except LoqateError as e:
            raise ValidationError(str(e))
        except Exception as e:
            logger.error("Retrieve address failed, request.data=%r, exc=%r" % (data, format_exc()))

        return response.Response(res)
