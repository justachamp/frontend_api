
from authentication.cognito.serializers import CognitoAuthSerializer, CogrnitoAuthRetrieveSerializer, \
    CogrnitoSignOutSerializer, CognitoAuthForgotPasswordSerializer, CognitoAuthPasswordRestoreSerializer,\
    CognitoAuthVerificationSerializer, CognitoAuthAttributeVerifySerializer, CognitoAuthChallengeSerializer

from authentication.cognito.models import Challenge
from rest_framework_json_api.views import viewsets

from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework import response

# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AuthView(viewsets.ViewSet):
    serializer_class = CognitoAuthSerializer
    # queryset = User.objects.all().order_by('-date_joined')

    resource_name = 'identity'
    permission_classes = (AllowAny,)

    @action(methods=['POST'], detail=False, name='Login')
    def sign_in(self, request):
        serializer = CogrnitoAuthRetrieveSerializer(data=request.data)
        if serializer.is_valid(True):
            entity = serializer.retrieve(serializer.validated_data)
            if type(entity) == Challenge:
                return response.Response(
                    CognitoAuthChallengeSerializer(instance=entity, context={'request': request}).data)
            else:
                return response.Response(
                    CogrnitoAuthRetrieveSerializer(instance=entity, context={'request': request}).data)

    @action(methods=['POST'], detail=False, name='Challenge')
    def challenge(self, request):
        serializer = CognitoAuthChallengeSerializer(data=request.data)
        if serializer.is_valid(True):
            entity = serializer.auth_challenge(serializer.validated_data)
            return response.Response(
                    CogrnitoAuthRetrieveSerializer(instance=entity, context={'request': request}).data)

    @action(methods=['POST'], detail=False, name='Logout')
    def sign_out(self, request):
        serializer = CogrnitoSignOutSerializer(data=request.data, )
        if serializer.is_valid(True):
            serializer.sign_out(serializer.validated_data)
            return response.Response(serializer.data)

    @action(methods=['POST'], detail=False, name='Refresh')
    def refresh(self, request):
        serializer = CogrnitoAuthRetrieveSerializer(data=request.data)
        if serializer.is_valid(True):
            entity = serializer.retrieve(serializer.validated_data)
            return response.Response(CogrnitoAuthRetrieveSerializer(instance=entity, context={'request': request}).data)

    @action(methods=['POST'], detail=True, name='Confirm login')
    def confirm_login(self):
        pass

    @action(methods=['POST'], detail=False, name='Sign up', resource_name='identity')
    def sign_up(self, request):
        serializer = CognitoAuthSerializer(data=request.data)
        if serializer.is_valid(True):
            serializer.create(serializer.validated_data)
            return self.sign_in(request)

    @action(methods=['POST'], detail=False, name='Send verification code')
    def verification_code(self, request):
        serializer = CognitoAuthVerificationSerializer(data=request.data)
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


