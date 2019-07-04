from rest_framework_json_api.views import RelationshipView

from core import views

from frontend_api.permissions import IsOwnerOrReadOnly, IsSuperAdminOrReadOnly
from frontend_api.models import SubUserPermission, AdminUserPermission
from frontend_api.serializers import SubUserPermissionSerializer, AdminUserPermissionSerializer


from ..views import PatchRelatedMixin

import logging
logger = logging.getLogger(__name__)


class SubUserPermissionRelationshipView(RelationshipView):
    queryset = SubUserPermission.objects
    serializer_class = SubUserPermissionSerializer


class AdminUserPermissionRelationshipView(RelationshipView):
    queryset = AdminUserPermission.objects
    serializer_class = AdminUserPermissionSerializer


class SubUserPermissionViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = SubUserPermission.objects.all()
    serializer_class = SubUserPermissionSerializer
    permission_classes = (IsOwnerOrReadOnly,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user

        if not user.account.permission:
            user.account.permission = serializer.save()
            user.account.save()


class AdminUserPermissionViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = AdminUserPermission.objects.all()
    serializer_class = AdminUserPermissionSerializer
    permission_classes = (IsSuperAdminOrReadOnly,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user

        if not user.account.permission:
            user.account.permission = serializer.save()
            user.account.save()