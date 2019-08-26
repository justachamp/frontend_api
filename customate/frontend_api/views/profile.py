from rest_framework import response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from frontend_api.serializers import (
    ProfileSerializer
)
from frontend_api.permissions import (
    CheckFieldsCredentials,
    IsOwnerOrReadOnly,
    IsSuperAdminOrReadOnly,
    SubUserManageSchedulesPermission,
    IsNotBlocked,
    IsActive,
    IsBlockedUsersUpdateContactInfoRequest)

import logging

logger = logging.getLogger(__name__)

from frontend_api.services.account import ProfileService


class DomainService:
    _service_object = None
    __service = None

    @property
    def service(self):
        return self.__service

    @service.setter
    def service(self, args):
        self.__service = self._service_object(*args)


class ProfileView(DomainService, APIView):
    permission_classes = ( IsAuthenticated,
                           IsActive,
                           IsNotBlocked | IsBlockedUsersUpdateContactInfoRequest,
                           CheckFieldsCredentials )
    _service_object = ProfileService

    credentials_required_fields = {}

    def __init__(self, *args, **kwargs):
        self.credentials_required_fields['user.email'] = ProfileView.can_change_email_without_credentials
        self.credentials_required_fields['user.phone_number'] = ProfileView.can_change_phone_without_credentials
        super().__init__(*args, **kwargs)

    def get(self, request, pk):
        self.service = request.user, None
        profile = self.service.profile
        serializer = ProfileSerializer(
            profile,
            context={'request': request, 'profile': profile, 'additional_keys': {'account': ['permission']}})
        return response.Response(serializer.data)

    def patch(self, request, pk):
        data = request.data
        self.service = request.user, data
        profile = self.service.profile
        is_gbg_optional = request.query_params.get("is_gbg_optional", 'true') == 'true'

        serializer = ProfileSerializer(
            instance=self.service.profile,
            data=request.data,
            context={'request': request, 'profile': profile, 'additional_keys': {'account': ['permission']}})

        serializer.is_valid(True)
        serializer.save(is_gbg_optional=is_gbg_optional)

        return response.Response(serializer.data)

    @staticmethod
    def can_change_email_without_credentials(request):
        return not request.user.email_verified

    @staticmethod
    def can_change_phone_without_credentials(request):
        return not request.user.phone_number_verified
