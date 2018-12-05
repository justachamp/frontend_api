from rest_framework_json_api import serializers, exceptions
from rest_framework.fields import Field, DictField, ListField
from authentication.cognito.models import Identity
from django.contrib.auth import get_user_model
from authentication.cognito.core import helpers
from authentication.cognito.exceptions import Unauthorized
from authentication.cognito.middleware import helpers as mid_helpers
import logging
logger = logging.getLogger(__name__)


class CognitoAttributeFiled(Field):

    def to_representation(self, data):
        return data

    def to_internal_value(self, data):
        return data


class CognitoAuthPasswordRestoreSerializer(serializers.Serializer):
    resource_name = 'identities'
    username = serializers.EmailField(required=True, write_only=True)
    code = serializers.CharField(max_length=50, required=False, write_only=True)
    new_password = serializers.CharField(max_length=50, required=False, write_only=True)

    @staticmethod
    def forgot_password(validated_data):
        try:
            return helpers.forgot_password(validated_data)
        except Exception as ex:
            logger.error(f'general {ex}')
            raise Unauthorized(ex)

    @staticmethod
    def confirm_forgot_password(validated_data):
        try:
            return helpers.confirm_forgot_password(validated_data)
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


class CogrnitoAuthRetreiveSerializer(serializers.Serializer):
    resource_name = 'identities'
    id = serializers.UUIDField(read_only=True)
    username = serializers.EmailField(required=True,  source='preferred_username', write_only=True)
    password = serializers.CharField(max_length=50, required=False, write_only=True)
    id_token = serializers.CharField(read_only=True)
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=False, required=False)

    def validate(self, data):
        if not data.get('refresh_token') and not data.get('password'):
            raise Unauthorized('Credentials not found')

        return data

    @staticmethod
    def retreive(validated_data):
        try:
            validated_data['username'] = validated_data['preferred_username']
            if validated_data.get('refresh_token'):
                result = helpers.refresh_session(validated_data)
            else:
                result = helpers.initiate_auth(validated_data)
            tokens = result.get('AuthenticationResult')
            data = mid_helpers.decode_token(tokens.get('IdToken'))
            validated_data['id_token'] = tokens.get('IdToken')
            validated_data['access_token'] = tokens.get('AccessToken')
            if not validated_data.get('access_token'):
                validated_data['refresh_token'] = tokens.get('RefreshToken')

            user = get_user_model().objects.get(email=data[1].get('email')) if len(data) else None

            if not user:
                raise serializers.ValidationError("User not found")
            return Identity(id=user.cognito_id, **validated_data)
        except Exception as ex:
            logger.error(f'general {ex}')
            raise Unauthorized(ex)


class CognitoAuthSerializer(CogrnitoAuthRetreiveSerializer):

    user_attributes = ListField(child=CognitoAttributeFiled(required=True), required=True)

    id_token = serializers.CharField(max_length=256, write_only=True, required=False)
    access_token = serializers.CharField(max_length=256, write_only=True, required=False)
    refresh_token = serializers.CharField(max_length=256, write_only=True, required=False)

    @staticmethod
    def validate_user_attributes(data):
        for item in data:
            if item.get('Name') == 'email':
                email = item['Value'].lower()
                item['Value'] = email
            if get_user_model().objects.filter(email=email).exists():
                raise serializers.ValidationError("Not unique email")

        return data

    def validate_username(self, email):
        email = email.lower()
        if get_user_model().objects.filter(email=email).exists():
            raise serializers.ValidationError("Not unique email")
        return email

    @staticmethod
    def validate_user_attributes(data):
        for item in data:
            if item.get('Name') == 'email':
                email = item['Value'].lower()
                item['Value'] = email
            if get_user_model().objects.filter(email=email).exists():
                raise serializers.ValidationError("Not unique email")

        return data

    @staticmethod
    def create(self, validated_data):
        try:
            validated_data['username'] = validated_data['preferred_username']
            result = helpers.sign_up(validated_data)
            return Identity(id=result.get('UserSub'), **validated_data)
        except Exception as ex:
            logger.error(f'general {ex}')
            raise Unauthorized(ex)

    @staticmethod
    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        return instance
