from django.forms.models import model_to_dict
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import MethodNotAllowed
from rest_framework_json_api.views import RelationshipView

from core import views

from frontend_api.models import Company
from frontend_api.serializers import CompanyAddressSerializer, CompanySerializer, ShareholderSerializer
from frontend_api.permissions import IsActive, IsOwnerOrReadOnly

from ..views import PatchRelatedMixin,  RelationshipPostMixin

import logging
logger = logging.getLogger(__name__)


class CompanyRelationshipView(RelationshipPostMixin, RelationshipView):
    serializer_class = CompanySerializer
    queryset = Company.objects
    permission_classes = ( IsAuthenticated,
                           IsActive,
                           IsOwnerOrReadOnly )
    _related_serializers = {
        'address': CompanyAddressSerializer,
        'shareholders': ShareholderSerializer
    }

    def post_address(self, request, *args, **kwargs):
        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        company = self.get_object()

        logger.info("Handle company's address creation request (company_id=%s)" % company.id)

        if company.address:
            raise MethodNotAllowed('POST')

        serializer = related_serializer(data=request.data.get('attributes'), context={'request': request})
        serializer.is_valid(raise_exception=True)
        company.address = serializer.save()
        company.save()

        return serializer

    def post_shareholders(self, request, *args, **kwargs):
        logger.info("Handle shareholders creation request")

        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        company = self.get_object()
        company = model_to_dict(company)
        company['type'] = 'Company'
        data = []
        for rec in request.data:
            rec = rec.get('attributes')
            rec['company'] = company
            data.append(rec)

        serializer = related_serializer(data=data, context={'request': request}, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return serializer


class CompanyViewSet(PatchRelatedMixin, views.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = ( IsAuthenticated,
                           IsActive,
                           IsOwnerOrReadOnly )

    def perform_create(self, serializer):
        logger.info("Handle company creation request")
        user = self.request.user

        if not user.account.company:
            user.account.company = serializer.save()
            user.account.save()