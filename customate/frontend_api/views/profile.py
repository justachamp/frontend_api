from rest_framework import response
from rest_framework.views import APIView

from frontend_api.serializers import (
    ProfileSerializer
)
from frontend_api.permissions import CheckFieldsCredentials

import logging
logger = logging.getLogger(__name__)

from frontend_api.services.account import ProfileService


class DomainService:

    _service_object=None
    __service=None

    @property
    def service(self):
        return self.__service

    @service.setter
    def service(self, args):
        self.__service = self._service_object(*args)


class ProfileView(DomainService, APIView):

    permission_classes = (CheckFieldsCredentials,)
    _service_object=ProfileService

    credentials_required_fields = ['user.email', 'user.phone_number']

    def get(self, request, pk):
        self.service = request.user, None
        profile = self.service.profile
        serializer = ProfileSerializer(profile, context={'request': request, 'profile': profile})
        return response.Response(serializer.data)

    def patch(self, request, pk):
        data = request.data
        self.service = request.user, data
        profile = self.service.profile

        serializer = ProfileSerializer(
            instance=self.service.profile,
            data=request.data,
            context={'request': request, 'profile': profile})

        serializer.is_valid(True)
        serializer.save()
        return response.Response(serializer.data)
