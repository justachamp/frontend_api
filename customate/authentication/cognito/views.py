import arrow

from authentication.cognito.serializers import CognitoAuthSerializer, CognitoAuthRetrieveSerializer, \
    CognitoSignOutSerializer, CognitoAuthForgotPasswordSerializer, CognitoAuthPasswordRestoreSerializer, \
    CognitoAuthVerificationSerializer, CognitoAuthAttributeVerifySerializer, CognitoAuthChallengeSerializer, \
    CognitoAuthChangePasswordSerializer

from authentication.cognito.models import Challenge, Identity
from rest_framework_json_api.views import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework import response
from rest_framework.status import HTTP_204_NO_CONTENT

import logging

logger = logging.getLogger(__name__)


class AuthView(viewsets.ViewSet):
    serializer_class = CognitoAuthSerializer

    resource_name = 'identity'
    permission_classes = (AllowAny,)

    @action(methods=['POST'], detail=False, name='Login')
    def sign_in(self, request):
        logger.info("Handle sign in request")
        serializer = CognitoAuthRetrieveSerializer(data=request.data)
        if serializer.is_valid(True):
            entity = serializer.retrieve(serializer.validated_data)
            self._update_user_model(entity, serializer.validated_data)

            if type(entity) == Challenge:
                logger.info("Returning challenge")
                return response.Response(
                    CognitoAuthChallengeSerializer(instance=entity, context={'request': request}).data)
            else:
                logger.info("Returning identity data")
                context = {'request': request, 'additional_keys': {'account': ['permission']}}
                return response.Response(
                    CognitoAuthRetrieveSerializer(instance=entity, context=context).data)
        else:
            logger.info("Invalid data was transferred to sign in end-point")

    def _update_user_model(self, identity, data):
        if type(identity) == Identity:
            identity.user.remember_me = data.get('remember', False)
            identity.user.last_activity = arrow.utcnow().datetime
            logger.debug("Updating user model with remember_me=%s, last_activity=%s"
                         % (identity.user.remember_me, identity.user.last_activity))
            identity.user.save(update_fields=["remember_me", "last_activity"])

    @action(methods=['POST'], detail=False, name='Challenge')
    def challenge(self, request):
        logger.info("Handle challenge request")
        serializer = CognitoAuthChallengeSerializer(data=request.data)
        if serializer.is_valid(True):
            entity = serializer.auth_challenge(serializer.validated_data)
            self._update_user_model(entity, serializer.validated_data)

            context = {'request': request, 'additional_keys': {'account': ['permission']}}
            return response.Response(
                CognitoAuthRetrieveSerializer(instance=entity, context=context).data)
        else:
            logger.info("Invalid data was transferred to challenge end-point")

    @action(methods=['POST'], detail=False, name='Logout')
    def sign_out(self, request):
        serializer = CognitoSignOutSerializer(data=request.data, )
        if serializer.is_valid(True):
            serializer.sign_out(serializer.validated_data)
            return response.Response(status=HTTP_204_NO_CONTENT)

    @action(methods=['POST'], detail=False, name='Refresh')
    def refresh(self, request):
        serializer = CognitoAuthRetrieveSerializer(data=request.data)
        if serializer.is_valid(True):
            entity = serializer.retrieve(serializer.validated_data)
            context = {'request': request, 'additional_keys': {'account': ['permission']}}
            return response.Response(CognitoAuthRetrieveSerializer(instance=entity, context=context).data)

    @action(methods=['POST'], detail=False, name='Sign up', resource_name='identity')
    def sign_up(self, request):
        serializer = CognitoAuthSerializer(data=request.data)
        if serializer.is_valid(True):
            serializer.create(serializer.validated_data)
            result_sign_in = self.sign_in(request)
            return result_sign_in

    @action(methods=['POST'], detail=False, name='Send verification code')
    def verification_code(self, request):
        serializer = CognitoAuthVerificationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid(True):
            entity = serializer.verification_code(serializer.validated_data)
            return response.Response(CognitoAuthVerificationSerializer(instance=entity).data)

    @action(methods=['POST'], detail=False, name='Verify')
    def verify(self, request):
        serializer = CognitoAuthAttributeVerifySerializer(data=request.data)
        if serializer.is_valid(True):
            return response.Response(status=serializer.verify_attribute(serializer.validated_data))

    @action(methods=['POST'], detail=False, name='Forgot password')
    def forgot_password(self, request):
        serializer = CognitoAuthForgotPasswordSerializer(data=request.data)
        if serializer.is_valid(True):
            entity = serializer.forgot_password(serializer.validated_data)
            return response.Response(CognitoAuthForgotPasswordSerializer(instance=entity).data)

    @action(methods=['POST'], detail=False, name='Confirm forgot password')
    def restore_password(self, request):
        serializer = CognitoAuthPasswordRestoreSerializer(data=request.data)
        if serializer.is_valid(True):
            return response.Response(status=serializer.restore_password(serializer.validated_data))

    @action(methods=['POST'], detail=False, name='Change password')
    def change_password(self, request):
        serializer = CognitoAuthChangePasswordSerializer(data=request.data)
        if serializer.is_valid(True):
            return response.Response(status=serializer.change_password(serializer.validated_data))
