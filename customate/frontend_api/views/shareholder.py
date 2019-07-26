from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework_json_api.views import RelationshipView

from core import views
from core.serializers import BulkExtensionMixin

from frontend_api.models import Shareholder
from frontend_api.serializers import ShareholderSerializer

from ..views import PatchRelatedMixin

import logging
logger = logging.getLogger(__name__)


class ShareholderRelationshipView(RelationshipView):
    queryset = Shareholder.objects
    serializer_class = ShareholderSerializer


class ShareholderViewSet(BulkExtensionMixin, PatchRelatedMixin, views.ModelViewSet):

    queryset = Shareholder.objects.all()
    serializer_class = ShareholderSerializer
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def perform_create(self, serializer):
        company = self.request.user.account.company
        company.shareholders.all().delete()
        company.shareholders.set(serializer.save())
        company.save()
