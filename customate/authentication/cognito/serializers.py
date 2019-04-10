from rest_framework_json_api import serializers
from rest_framework.fields import Field, ListField
from rest_framework import status as status_codes
from rest_framework.exceptions import NotFound

from authentication.cognito.core.constants import NEW_PASSWORD_CHALLENGE
from authentication.cognito.models import Identity, Verification, Challenge, Invitation
from core.fields import UserStatus

from authentication.cognito.core import helpers
from authentication.cognito.exceptions import Unauthorized
from authentication.cognito.middleware import helpers as mid_helpers
from django.contrib.auth import get_user_model
from authentication.cognito.core.base import generate_password, CognitoException
import logging

from frontend_api.serializers import UserSerializer, AccountSerializer
from authentication.cognito.core.mixins import AuthSerializerMixin
from authentication import settings
from core.services.user import UserService
from core.fields import SerializerField

logger = logging.getLogger(__name__)


class CognitoAttributeFiled(Field):

    def to_representation(self, data):
        return data

    def to_internal_value(self, data):
        return data


class UserServiceMixin(object):

    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)

    _user_service = None

    @property
    def user_service(self)->UserService:
        if not self._user_service:
            self._user_service = UserService()

        return self._user_service

    def _get_cognito_user(self, data):
        identity = None
        user_data = None
        if len(data):
            cognito_user = data[1]
            identity = cognito_user.get('cognito:username')
            email = cognito_user.get('email')
            logger.error(f'process_request user_attributes: {cognito_user}')
            user_data = {
                'username': email,
                'email': email,
                'email_verified': cognito_user.get('email_verified', True),
                'phone_number': cognito_user.get('phone_number', ''),
                'phone_number_verified': cognito_user.get('phone_number_verified', False),
                'cognito_id': cognito_user.get('cognito:username'),
                'role': cognito_user.get('custom:account_type', self.user_service.user_role),
                'first_name': cognito_user.get('given_name', ''),
                'last_name': cognito_user.get('family_name', '')
            }
        return identity, user_data


class BaseAuthValidationMixin(object):

    def validate_user_attributes(self, data):
        for item in data:
            if item.get('Name') == 'email':
                email = item['Value'].lower()
                item['Value'] = email
            if self.user_service.user_exists(email):
                raise serializers.ValidationError("Email already exists you cannot register the same email twice")

        return data

    def validate_username(self, email):
        email = email.lower()
        if self.user_service.user_exists(email):
            raise serializers.ValidationError("Email already exists you cannot register the same email twice")
        return email


class CognitoAuthVerificationSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, write_only=True)
    attribute_name = serializers.ChoiceField(required=True, allow_blank=False, choices=('email', 'phone_number'))
    destination = serializers.CharField(max_length=50, required=False, read_only=True)
    access_token = serializers.CharField(write_only=True, required=True)

    @staticmethod
    def verification_code(validated_data):
        try:
            data = helpers.verification_code(validated_data)
            response = data.get('CodeDeliveryDetails')
            validated_data['destination'] = response.get('Destination')
            return Verification(**validated_data)
        except Exception as ex:
            logger.error(f'general verification_code {ex}')
            raise Unauthorized(ex)


class CognitoAuthAttributeVerifySerializer(serializers.Serializer, AuthSerializerMixin, UserServiceMixin):
    resource_name = 'identities'
    id = serializers.UUIDField(read_only=True)
    attribute_name = serializers.ChoiceField(required=True, allow_blank=False, choices=('email', 'phone_number'))
    access_token = serializers.CharField(write_only=True, required=True)
    code = serializers.CharField(max_length=50, required=False, write_only=True)

    def verify_attribute(self, validated_data):
        try:
            data = helpers.verify_attribute(validated_data)

            status = data.get('ResponseMetadata').get('HTTPStatusCode')
            if status == status_codes.HTTP_200_OK:
                user = self.user_service.get_user_from_token(access_token=validated_data['access_token'])
                attribute = validated_data['attribute_name']
                self.user_service.verify_attribute(user, attribute)
                return status_codes.HTTP_204_NO_CONTENT

            return status_codes.HTTP_204_NO_CONTENT if status == status_codes.HTTP_200_OK else status
        except Exception as ex:
            logger.error(f'verify_attribute general {ex}')
            raise Unauthorized(ex)


class CognitoAuthForgotPasswordSerializer(serializers.Serializer):
    resource_name = 'identities'
    username = serializers.EmailField(required=True, write_only=True)
    attribute_name = serializers.ChoiceField(required=False, read_only=True, choices=('email', 'phone_number'))
    destination = serializers.CharField(max_length=50, required=False, read_only=True)

    @staticmethod
    def forgot_password(validated_data):
        try:
            data = helpers.forgot_password(validated_data).get('CodeDeliveryDetails')
            attributes = {
                'destination': data.get('Destination'),
                'attribute_name': data.get('AttributeName')
            }
            return Verification(**attributes)
        except Exception as ex:
            logger.error(f'forgot_password general {ex}')
            raise Unauthorized(ex)


class CognitoAuthPasswordRestoreSerializer(serializers.Serializer):
    resource_name = 'identities'
    username = serializers.EmailField(required=True, write_only=True)
    code = serializers.CharField(max_length=50, required=False, write_only=True)
    password = serializers.CharField(min_length=6, max_length=50, required=False, write_only=True)

    @staticmethod
    def restore_password(validated_data):
        try:
            data = helpers.restore_password(validated_data)
            status = data.get('ResponseMetadata').get('HTTPStatusCode')
            return status_codes.HTTP_204_NO_CONTENT if status == status_codes.HTTP_200_OK else status
        except Exception as ex:
            logger.error(f'restore_password general {ex}')
            raise Unauthorized(ex)


class CognitoAuthChangePasswordSerializer(serializers.Serializer):
    resource_name = 'identities'
    previous = serializers.CharField(max_length=250, required=True, write_only=True)
    proposed = serializers.CharField(max_length=250, required=True, write_only=True)
    access_token = serializers.CharField(write_only=True, required=True)

    @staticmethod
    def change_password(validated_data):
        try:
            data = helpers.change_password(validated_data)
            status = data.get('ResponseMetadata').get('HTTPStatusCode')
            return status_codes.HTTP_204_NO_CONTENT if status == status_codes.HTTP_200_OK else status
        except Exception as ex:
            logger.error(f'change_password general {ex}')
            raise Unauthorized(ex)


class CogrnitoSignOutSerializer(serializers.Serializer):
    resource_name = 'identities'
    access_token = serializers.CharField(write_only=True, required=True)

    @staticmethod
    def sign_out(validated_data):
        try:
            return helpers.sign_out(validated_data)
        except Exception as ex:
            logger.error(f'sign_out general {ex}')
            raise Unauthorized(ex)


class CognitoAuthChallengeSerializer(serializers.Serializer, UserServiceMixin):

    id = serializers.UUIDField(read_only=True)
    username = serializers.EmailField(required=True)
    challenge_name = serializers.CharField(max_length=40, required=True)
    challenge_response = serializers.CharField(required=False, write_only=True)
    challenge_delivery = serializers.CharField(max_length=20, required=False)
    destination = serializers.CharField(max_length=14, required=False)
    session = serializers.CharField(required=True)

    def auth_challenge(self, validated_data):
        try:
            result = helpers.respond_to_auth_challenge(validated_data)
            tokens = result.get('AuthenticationResult')
            data = mid_helpers.decode_token(tokens.get('IdToken'))
            validated_data['id_token'] = tokens.get('IdToken')
            validated_data['access_token'] = tokens.get('AccessToken')
            if not validated_data.get('refresh_token'):
                validated_data['refresh_token'] = tokens.get('RefreshToken')

            identity, user_data = self._get_cognito_user(data)
            user = self.user_service.get_user_by_external_identity(identity=identity)

            if validated_data['challenge_name'] == NEW_PASSWORD_CHALLENGE:
                self.user_service.activate_user(user)
                helpers.admin_update_user_attributes({
                    'username': user.username,
                    'user_attributes': [{
                        'Name': 'email_verified',
                        'Value': 'true'
                    }]
                })
                self.user_service.verify_attribute(user, 'email')

            validated_data['user'] = user
            return Identity(id=user.id, **validated_data)

        except Exception as ex:
            logger.error(f'auth_challenge general {ex}')
            raise Unauthorized(ex)


class CogrnitoAuthRetrieveMessageSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)

    def validate(self, data):
        message = data.get('message')
        if 'account has expired' in message:
            raise serializers.ValidationError({'password': 'Temporary code has been expired.'})

        return data


class CogrnitoAuthRetrieveSerializer(serializers.Serializer, UserServiceMixin):
    resource_name = 'identities'
    id = serializers.UUIDField(read_only=True)
    username = serializers.EmailField(required=True, source='preferred_username', write_only=True)
    password = serializers.CharField(max_length=50, required=False, write_only=True)
    id_token = serializers.CharField(read_only=True)
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=False, required=False)
    user = SerializerField(resource=UserSerializer, required=False)

    account = SerializerField(
        resource=AccountSerializer, required=False, source='user.account'
    )

    related_serializers = {
        'user': 'frontend_api.serializers.UserSerializer',
    }

    @staticmethod
    def validate_username(email):
        return email.lower()

    def validate_user_status(self, username):
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=username)
        except user_model.DoesNotExist:
            raise Unauthorized('User does not exist')

        if user.status == UserStatus.banned:
            raise Unauthorized('User is banned')

        if user.is_subuser:
            try:
                if user.account.owner_account.user.status == UserStatus.banned:
                    raise Unauthorized('Owner account is banned')
            except user_model.DoesNotExist:
                raise Unauthorized('Owner account not exists')

    def validate(self, data):
        if not data.get('refresh_token') and not data.get('password'):
            raise Unauthorized('Credentials not found')

        self.validate_user_status(data.get('preferred_username'))
        return data

    def retrieve(self, validated_data):
        from django.conf import settings as gsettings
        logger.error(
            f'retrieve general {validated_data} client id: {getattr(gsettings, "COGNITO_APP_CLIENT_ID", "Not found")}')
        try:
            logger.error(f'retrieve before all general {validated_data}')
            validated_data['username'] = validated_data['preferred_username']
            if validated_data.get('refresh_token'):
                logger.error(f'retrieve before refresh_session general {validated_data}')
                result = helpers.refresh_session(validated_data)
            else:
                logger.error(f'retrieve before initiate_auth general {validated_data}')
                result = helpers.initiate_auth(validated_data)
            logger.error(f'retrieve result general {result}')
            if result.get('AuthenticationResult'):
                return self._retrieve_auth_result(validated_data, result)
            elif result.get('ChallengeName'):
                return self._retrieve_auth_challenge(validated_data, result)

        except Exception as ex:
            logger.error(f'retrieve general {validated_data} client id: {getattr(gsettings, "COGNITO_APP_CLIENT_ID", "Not found")}')
            logger.error(f'retrieve general {ex}')
            import traceback
            import sys

            logger.error(f'traceback.format_exc() {traceback.format_exc()}')
            logger.error(f'sys.exc_info()[0] {sys.exc_info()[0]}')

            s = CogrnitoAuthRetrieveMessageSerializer(data={'message': str(ex)})
            s.is_valid(True)
            
            raise Unauthorized(ex)

    def check_password(self, validated_data):
        try:
            validated_data['username'] = validated_data['preferred_username']
            password = validated_data['password']
            data = {
                "previous": password,
                "proposed": password,
                "access_token": self.context.get('request').META.get('HTTP_ACCESSTOKEN')
            }

            result = helpers.change_password(data)
            status = result.get('ResponseMetadata').get('HTTPStatusCode')
            return status == status_codes.HTTP_200_OK

        except CognitoException as ex:
            logger.error(f'check_password CognitoException general {ex}')
            raise serializers.ValidationError(ex)
        except Exception as ex:
            logger.error(f'check_password general {ex}')
            raise Unauthorized(ex)

    def _retrieve_auth_result(self, validated_data, result):
        logger.error(f'_retrieve_auth_result validated_data {validated_data}')
        logger.error(f'_retrieve_auth_result result {result}')
        tokens = result.get('AuthenticationResult')
        validated_data['id_token'] = tokens.get('IdToken')
        validated_data['access_token'] = tokens.get('AccessToken')
        if not validated_data.get('refresh_token'):
            validated_data['refresh_token'] = tokens.get('RefreshToken')

        logger.error(f'_retrieve_auth_result validated_data {validated_data}')
        data = mid_helpers.decode_token(tokens.get('IdToken'))
        logger.error(f'_retrieve_auth_result data {data}')
        identity, user_data = self._get_cognito_user(data)
        user = self.user_service.get_user_by_external_identity(
            identity=identity,
            user_data=user_data,
            auto_create=getattr(settings, 'AUTO_CREATE_USER', False)
        )

        validated_data['user'] = user
        return Identity(id=user.id, **validated_data)

    @staticmethod
    def _retrieve_auth_challenge(validated_data, result):
        params = result.get('ChallengeParameters')
        session = result.get('Session')
        id = params.get('USER_ID_FOR_SRP')
        validated_data['challenge_name'] = result.get('ChallengeName')
        validated_data['challenge_delivery'] = params.get('CODE_DELIVERY_DELIVERY_MEDIUM')
        validated_data['destination'] = params.get('CODE_DELIVERY_DESTINATION')
        validated_data['session'] = session

        return Challenge(id=id, **validated_data)


class CognitoInviteUserSerializer(serializers.Serializer, BaseAuthValidationMixin, UserServiceMixin):
    username = serializers.EmailField(required=True, source='preferred_username', write_only=True)
    user_attributes = ListField(child=CognitoAttributeFiled(required=True), required=True)
    # temporary_password = serializers.CharField(max_length=50, required=False)
    action = serializers.ChoiceField(choices=('RESEND', 'SUPPRESS'), required=False)
    delivery = ListField(child=serializers.ChoiceField(choices=('SMS', 'EMAIL'), required=True), required=False)

    @staticmethod
    def invite(validated_data):
        try:
            validated_data['username'] = validated_data['username'].lower()
            validated_data['user_attributes'] = [
                {'Name': 'email', 'Value': validated_data['username']},
                {'Name': 'custom:account_type', 'Value': validated_data['role']}
            ]
            validated_data['temporary_password'] = generate_password()
            validated_data['action'] = validated_data.get('action', '')
            validated_data['delivery'] = validated_data.get('delivery', ['EMAIL'])
            user = helpers.admin_create_user(validated_data)

            return Invitation(id=user.get('Username'), **validated_data)
        except Exception as ex:
            logger.error(f'invite general {ex}')
            raise Unauthorized(ex)


class CognitoAuthSerializer(BaseAuthValidationMixin, CogrnitoAuthRetrieveSerializer, UserServiceMixin):

    user_attributes = ListField(child=CognitoAttributeFiled(required=True), required=True)
    username = serializers.EmailField(required=True, source='preferred_username', write_only=True)
    password = serializers.CharField(max_length=50, required=False, write_only=True)
    account_type = serializers.ChoiceField(choices=('business', 'personal'))
    id_token = serializers.CharField(max_length=256, write_only=True, required=False)
    access_token = serializers.CharField(max_length=256, write_only=True, required=False)
    refresh_token = serializers.CharField(max_length=256, write_only=True, required=False)

    def create(self, validated_data):
        try:
            validated_data['preferred_username'] = validated_data['preferred_username'].lower()
            validated_data['username'] = validated_data['preferred_username']
            validated_data['user_attributes'] = [
                {'Name': 'email', 'Value': validated_data['preferred_username']},
                {'Name': 'custom:account_type', 'Value': str(self.user_service.user_role)}
            ]
            helpers.sign_up(validated_data)
            serializer = CogrnitoAuthRetrieveSerializer()
            return serializer.retrieve(validated_data)
        except Exception as ex:
            logger.error(f'create general {ex}')
            raise Unauthorized(ex)

    def validate_user_status(self, username):
        pass

    @staticmethod
    def update(instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        return instance
