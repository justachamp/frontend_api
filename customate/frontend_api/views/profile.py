from traceback import format_exc

from rest_framework import response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from authentication.cognito.core.base import CognitoException
from authentication.cognito.exceptions import GeneralCognitoException
from frontend_api.serializers import (
    ProfileSerializer
)
from frontend_api.permissions import (
    CheckFieldsCredentials,
    IsActive)

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
    permission_classes = (IsAuthenticated,
                          IsActive,
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
        skip_gbg = bool(int(request.query_params.get("skip_gbg", 0)))
        ignore_gbg_exception = bool(int(request.query_params.get("ignore_gbg_exception", 1)))

        try:
            serializer = ProfileSerializer(
                instance=self.service.profile,
                data=request.data,
                context={'request': request, 'profile': profile, 'additional_keys': {'account': ['permission']}}
            )

            serializer.is_valid(True)
            serializer.save(ignore_gbg_exception=ignore_gbg_exception, skip_gbg=skip_gbg)
        except Exception as ex:
            # Special case for issue with Cognito's limits,
            # we need to convert original exception to APIException instance
            if isinstance(ex, CognitoException):
                logger.debug("Cognito exception occurred (updating profile): %s" % format_exc())
                raise GeneralCognitoException(ex)
            else:
                raise ex

        return response.Response(serializer.data)

    @staticmethod
    def can_change_email_without_credentials(request):
        return not request.user.email_verified

    @staticmethod
    def can_change_phone_without_credentials(request):
        return not request.user.phone_number_verified
