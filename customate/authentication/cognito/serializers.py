from rest_framework_json_api import serializers, exceptions
from rest_framework.fields import Field, DictField, ListField
from rest_framework import status as status_codes
from authentication.cognito.models import Identity, Verification
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


class CognitoAuthVerificationSerializer(serializers.Serializer):
    resource_name = 'identities'
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


class CognitoAuthAttributeVerifySerializer(serializers.Serializer):
    resource_name = 'identities'
    attribute_name = serializers.ChoiceField(required=True, allow_blank=False, choices=('email', 'phone_number'))
    access_token = serializers.CharField(write_only=True, required=True)
    code = serializers.CharField(max_length=50, required=False, write_only=True)

    @staticmethod
    def verify_attribute(validated_data):
        try:
            data = helpers.verify_attribute(validated_data)
            status = data.get('ResponseMetadata').get('HTTPStatusCode')
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
    def confirm_forgot_password(validated_data):
        try:
            status = helpers.confirm_forgot_password(validated_data)
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
            if not validated_data.get('refresh_token'):
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

    @staticmethod
    def validate_username(email):
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
    def create(validated_data):
        try:
            # "type": 'personal|business"
            validated_data['username'] = validated_data['preferred_username']
            result = helpers.sign_up(validated_data)
            return Identity(id=result.get('UserSub'), **validated_data)
        except Exception as ex:
            logger.error(f'general {ex}')
            # raise exceptions.exceptions.ValidationError(detail=ex.args[0])
            raise Unauthorized(ex)

    @staticmethod
    def update(instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        return instance
