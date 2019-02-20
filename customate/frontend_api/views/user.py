from rest_framework.permissions import AllowAny
from rest_framework.exceptions import MethodNotAllowed, NotFound
from rest_framework_json_api.views import RelationshipView

from core import views
from core.models import User
from core.fields import UserRole

from frontend_api.serializers import (
    UserAddressSerializer,
    SubUserAccountSerializer,
    AdminUserAccountSerializer,
    SubUserSerializer,
    AdminUserSerializer,
    UserAccountSerializer,
    UserSerializer
)

from frontend_api.permissions import IsOwnerOrReadOnly

from ..views import PatchRelatedMixin, RelationshipPostMixin

import logging
logger = logging.getLogger(__name__)


class AdminUserViewSet(PatchRelatedMixin, views.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().filter(role=UserRole.admin).order_by('-date_joined')
    serializer_class = AdminUserSerializer

    permission_classes = (IsOwnerOrReadOnly,)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()

    def get_serializer_class(self):

        field = self.kwargs.get('related_field')

        if field == 'account':
            user = self.request.user
            pk = self.kwargs.get('pk')

            try:
                user = User.objects.get(id=pk)
            except Exception as e:
                raise NotFound(f'Account not found {pk}')

            if user.is_owner:
                return UserAccountSerializer
            elif user.is_subuser:
                return SubUserAccountSerializer
            elif user.is_admin:
                return AdminUserAccountSerializer

        else:
            return super().get_serializer_class()


class UserViewSet(PatchRelatedMixin, views.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = User.objects.all().exclude(email='AnonymousUser').order_by('-date_joined')
    serializer_class = UserSerializer

    permission_classes = (IsOwnerOrReadOnly,)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()

    def get_serializer_class(self):

        field = self.kwargs.get('related_field')
        user = self.request.user
        id = self.kwargs.get('pk')
        if id:
            try:
                user = User.objects.get(id=id)
            except Exception as e:
                raise NotFound(f'Account not found {id}')

            if field:
                if field == 'account':
                    if user.is_owner:
                        return UserAccountSerializer
                    elif user.is_subuser:
                        return SubUserAccountSerializer
                    elif user.is_admin:
                        return AdminUserAccountSerializer
                else:
                    return super().get_serializer_class()
            else:
                if user.is_owner:
                    return UserSerializer
                elif user.is_subuser:
                    return SubUserSerializer
                elif user.is_admin:
                    return AdminUserSerializer
                else:
                    return super().get_serializer_class()
        else:
            return super().get_serializer_class()


class UserRelationshipView(RelationshipPostMixin, RelationshipView):
    queryset = User.objects
    permission_classes = (AllowAny,)
    _related_serializers = {
        'address': UserAddressSerializer
    }

    def post_address(self, request, *args, **kwargs):
        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        user = self.get_object()

        if user.address:
                raise MethodNotAllowed('POST')

        serializer = related_serializer(data=request.data.get('attributes'), context={'request': request})
        serializer.is_valid(raise_exception=True)
        user.address = serializer.save()
        user.save()

        return serializer