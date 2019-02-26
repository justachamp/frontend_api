from rest_framework_json_api import serializers
from rest_framework.fields import Field, ListField
from rest_framework import status as status_codes
from rest_framework.exceptions import NotFound

from authentication.cognito.core.constants import NEW_PASSWORD_CHALLENGE
from authentication.cognito.models import Identity, Verification, Challenge, Invitation

from authentication.cognito.core import helpers
from authentication.cognito.exceptions import Unauthorized
from authentication.cognito.middleware import helpers as mid_helpers

from authentication.cognito.core.base import generate_password
import logging

from frontend_api.serializers import UserSerializer
from authentication.cognito.core.mixins import AuthSerializerMixin
from authentication import settings
from core.services.user import UserService
from core.fields import UserStatus

logger = logging.getLogger(__name__)


class CognitoAttributeFiled(Field):

    def to_representation(self, data):
        return data

    def to_internal_value(self, data):
        return data


class UserServiceMixin(object):

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
            logger.error(f'general {ex}')
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
            logger.error(f'general {ex}')
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
            logger.error(f'general {ex}')
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
            logger.error(f'general {ex}')
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
            logger.error(f'general {ex}')
            raise Unauthorized(ex)


class CogrnitoSignOutSerializer(serializers.Serializer):
    resource_name = 'identities'
    access_token = serializers.CharField(write_only=True, required=True)

    @staticmethod
    def sign_out(validated_data):
        try:
            return helpers.sign_out(validated_data)
        except Exception as ex:
            logger.error(f'general {ex}')
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

            validated_data['user'] = user
            return Identity(id=user.id, **validated_data)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Unauthorized(ex)


class CogrnitoAuthRetrieveSerializer(serializers.Serializer, UserServiceMixin):
    resource_name = 'identities'
    id = serializers.UUIDField(read_only=True)
    username = serializers.EmailField(required=True, source='preferred_username', write_only=True)
    password = serializers.CharField(max_length=50, required=False, write_only=True)
    id_token = serializers.CharField(read_only=True)
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=False, required=False)
    user = serializers.SerializerMethodField()

    def get_user(self, data):
        return UserSerializer(instance=data.user, context=self.context).data

    related_serializers = {
        'user': 'frontend_api.serializers.UserSerializer',
    }

    @staticmethod
    def validate_username(email):
        return email.lower()

    def validate(self, data):
        if not data.get('refresh_token') and not data.get('password'):
            raise Unauthorized('Credentials not found')

        return data

    def retrieve(self, validated_data):
        try:
            validated_data['username'] = validated_data['preferred_username']
            if validated_data.get('refresh_token'):
                result = helpers.refresh_session(validated_data)
            else:
                result = helpers.initiate_auth(validated_data)

            if result.get('AuthenticationResult'):
                return self._retrieve_auth_result(validated_data, result)
            elif result.get('ChallengeName'):
                return self._retrieve_auth_challenge(validated_data, result)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Unauthorized(ex)

    def _retrieve_auth_result(self, validated_data, result):
        tokens = result.get('AuthenticationResult')
        validated_data['id_token'] = tokens.get('IdToken')
        validated_data['access_token'] = tokens.get('AccessToken')
        if not validated_data.get('refresh_token'):
            validated_data['refresh_token'] = tokens.get('RefreshToken')

        data = mid_helpers.decode_token(tokens.get('IdToken'))
        identity, user_data = self._get_cognito_user(data)
        user = self.user_service.get_user_by_external_identity(
            identity=identity,
            user_data=user_data,
            auto_create=getattr(settings, 'AUTO_CREATE_USER', False)
        )
        if user.status == UserStatus.banned:
            raise Exception('User banned')

        if user.status == UserStatus.blocked:
            raise Exception('User blocked')

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
    temporary_password = serializers.CharField(max_length=50, required=False)
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
            logger.error(f'general {ex}')
            raise Unauthorized(ex)


class CognitoConfirmSignUpSerializer(serializers.Serializer, BaseAuthValidationMixin, UserServiceMixin):
    client_id = serializers.CharField(max_length=50, required=True)
    username = serializers.CharField(max_length=50, required=True)
    code = serializers.CharField(max_length=50, required=True)

    def verify(self, validated_data):
        try:
            user = self.user_service.get_user_by_external_identity(identity=validated_data["username"])
        except Exception as e:
            raise NotFound(f'Account not found {validated_data["username"]}')

        try:
            helpers.confirm_sign_up(validated_data)
            self.user_service.verify_attribute(user, "email")
        except Exception as ex:
            logger.error(f'general {ex}')
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
            logger.error(f'general {ex}')
            raise Unauthorized(ex)

    @staticmethod
    def update(instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        return instance
