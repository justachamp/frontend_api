from django.db import transaction
from django.contrib.auth.models import AnonymousUser

from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import MethodNotAllowed, NotFound
from rest_framework import response
from rest_framework.views import APIView
from rest_framework_json_api.views import RelationshipView

from authentication.cognito.serializers import CognitoInviteUserSerializer
from core.fields import UserRole
from core import views
from core.models import User

from frontend_api.models import (
    Account,
    SubUserAccount,
    AdminUserAccount,
    SubUserPermission,
    AdminUserPermission
)

from frontend_api.serializers import (
    ProfileSerializer
)

from frontend_api.permissions import IsOwnerOrReadOnly

from ..views import (
    PatchRelatedMixin,
    RelationshipMixin,
    RelationshipPostMixin
)

import logging
logger = logging.getLogger(__name__)

from frontend_api.services.account import ProfileService


class DomainService:

    _service_object=None
    __service=None

    @property
    def service(self):
        # if not self.__service:
        #     self.__service = self._service_object()
        return self.__service

    @service.setter
    def service(self, args):
        self.__service = self._service_object(*args)


class ProfileView(DomainService, APIView):

    # permission_classes = (AllowAny,)
    _service_object=ProfileService

    def get(self, request, pk):
        self.service = request.user
        serializer = ProfileSerializer(self.service.profile, context={'request': request})
        return response.Response(serializer.data)

    def patch(self, request, pk):
        data = request.data
        self.service = request.user, data

        if data.get('account'):
            data['account']['type'] = self.request.user.account.__class__.__name__

        profile = self.service.profile

        serializer = ProfileSerializer(
            instance=self.service.profile,
            data=request.data,
            context={'request': request, 'profile': profile})
        serializer.is_valid(True)
        serializer.save()
        return response.Response(serializer.data)
