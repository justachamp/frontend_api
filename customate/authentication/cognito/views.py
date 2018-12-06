import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from authentication.cognito.core import helpers
from authentication.cognito.serializers import CognitoAuthSerializer, CogrnitoAuthRetreiveSerializer, \
    CogrnitoSignOutSerializer, CognitoAuthForgotPasswordSerializer, CognitoAuthPasswordRestoreSerializer,\
    CognitoAuthVerificationSerializer, CognitoAuthAttributeVerifySerializer

from authentication.cognito.core.base import CognitoException, CognitoUser
from rest_framework_json_api.views import viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework_json_api.serializers import Serializer
from rest_framework_json_api.renderers import JSONRenderer
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
        serializer = CogrnitoAuthRetreiveSerializer(data=request.data)
        if serializer.is_valid(True):
            entity = serializer.retreive(serializer.validated_data)
            return response.Response(CogrnitoAuthRetreiveSerializer(instance=entity).data)
        # result = helpers.initiate_auth(request.data)
        # return response.Response(result)

    @action(methods=['POST'], detail=False, name='Logout')
    def sign_out(self, request):

        serializer = CogrnitoSignOutSerializer(data=request.data)
        if serializer.is_valid(True):
            serializer.sign_out(serializer.validated_data)
            return response.Response(serializer.data)

    @action(methods=['POST'], detail=False, name='Refresh')
    def refresh(self, request):
        serializer = CogrnitoAuthRetreiveSerializer(data=request.data)
        if serializer.is_valid(True):
            entity = serializer.retreive(serializer.validated_data)
            return response.Response(CogrnitoAuthRetreiveSerializer(instance=entity).data)
        # result = helpers.initiate_auth(request.data)
        # return response.Response(result)

    @action(methods=['POST'], detail=True, name='Confirm login')
    def confirm_login(self):
        pass

    @action(methods=['POST'], detail=False, name='Sign up', resource_name='identity')
    def sign_up(self, request):
        # data = json.loads(request.body.decode('utf-8'))
        serializer = CognitoAuthSerializer(data=request.data)
        if serializer.is_valid(True):
            entity = serializer.create(serializer.validated_data)
            return response.Response(CognitoAuthSerializer(instance=entity).data)

    @action(methods=['POST'], detail=False, name='Forgot password')
    def verification_code(self, request):
        serializer = CognitoAuthVerificationSerializer(data=request.data)
        if serializer.is_valid(True):
            entity = serializer.verification_code(serializer.validated_data)
            return response.Response(CognitoAuthVerificationSerializer(instance=entity).data)

    @action(methods=['POST'], detail=False, name='Forgot password')
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
    def confirm_forgot_password(self, request):
        serializer = CognitoAuthPasswordRestoreSerializer(data=request.data)
        if serializer.is_valid(True):
            return response.Response(status=serializer.confirm_forgot_password(serializer.validated_data))


# @csrf_exempt
# @require_http_methods(['POST'])
# def initiate_auth(request):
#     try:
#         data = json.loads(request.body.decode('utf-8'))
#         result = helpers.initiate_auth(data)
#
#         return JsonResponse(result)
#     except CognitoException as ex:
#         return JsonResponse(ex.args[0], status=ex.status)
#     except ValueError as ex:
#         return JsonResponse({"error": ex.args[0]}, status=400)


# @csrf_exempt
# @require_http_methods(['POST'])
# def refresh_token(request):
#     try:
#         result = helpers.refresh_token(request)
#         return JsonResponse(result)
#     except CognitoException as ex:
#         return JsonResponse(ex.args[0], status=ex.status)
#     except ValueError as ex:
#         return JsonResponse({"error": ex.args[0]}, status=400)


@require_http_methods(['POST'])
def respond_to_auth_challenge(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        result = helpers.respond_to_auth_challenge(data)

        return JsonResponse(result)
    except CognitoException as ex:
        return JsonResponse(ex.args[0], status=ex.status)
    except ValueError as ex:
        return JsonResponse({"error": ex.args[0]}, status=400)
    pass


# @csrf_exempt
# @require_http_methods(['POST'])
# def forgot_password(request):
#     try:
#         data = json.loads(request.body.decode('utf-8'))
#         result = helpers.forgot_password(data)
#
#         return JsonResponse(result)
#     except CognitoException as ex:
#         return JsonResponse(ex.args[0], status=ex.status)
#     except ValueError as ex:
#         return JsonResponse({"error": ex.args[0]}, status=400)
#     pass


@csrf_exempt
@require_http_methods(['POST'])
def confirm_forgot_password(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        result = helpers.confirm_forgot_password(data)

        return JsonResponse(result)
    except CognitoException as ex:
        return JsonResponse(ex.args[0], status=ex.status)
    except ValueError as ex:
        return JsonResponse({"error": ex.args[0]}, status=400)
    pass


# @csrf_exempt
# @require_http_methods(['POST'])
# def sign_up(request):
#     logger.error('sign_up error')
#     try:
#         data = json.loads(request.body.decode('utf-8'))
#         result = helpers.sign_up(data)
#
#         return JsonResponse(result, safe=False)
#     except CognitoException as ex:
#         return JsonResponse(ex.args[0], status=ex.status)
#     except ValueError as ex:
#         return JsonResponse({"error": ex.args[0]}, status=400)
#     pass


# @csrf_exempt
# @require_http_methods(['POST'])
# def confirm_sign_up(request):
#     try:
#         data = json.loads(request.body.decode('utf-8'))
#         result = helpers.confirm_sign_up(data)
#
#         return JsonResponse(result)
#     except CognitoException as ex:
#         return JsonResponse(ex.args[0], status=ex.status)
#     except ValueError as ex:
#         return JsonResponse({"error": ex.args[0]}, status=400)
#     pass
