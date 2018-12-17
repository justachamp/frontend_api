from rest_framework_json_api import serializers, exceptions
from rest_framework.fields import Field, DictField, ListField
from rest_framework import status as status_codes
from authentication.cognito.models import Identity, Verification, Challenge
from django.contrib.auth import get_user_model
from authentication.cognito.core import helpers
from authentication.cognito.exceptions import Unauthorized
from authentication.cognito.middleware import helpers as mid_helpers
import logging
from frontend_api.serializers import UserSerializer
from authentication.cognito.core.mixins import AuthSerializerMixin
from authentication.cognito.middleware import helpers as m_helpers
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


class CognitoAuthAttributeVerifySerializer(serializers.Serializer, AuthSerializerMixin):
    resource_name = 'identities'
    attribute_name = serializers.ChoiceField(required=True, allow_blank=False, choices=('email', 'phone_number'))
    access_token = serializers.CharField(write_only=True, required=True)
    code = serializers.CharField(max_length=50, required=False, write_only=True)

    # @staticmethod
    def verify_attribute(self, validated_data):
        try:
            data = helpers.verify_attribute(validated_data)

            status = data.get('ResponseMetadata').get('HTTPStatusCode')
            if status == status_codes.HTTP_200_OK:
                user, _, _, _ = m_helpers.get_tokens(access_token=validated_data['access_token'])
                attribute = validated_data['attribute_name']
                if getattr(user, attribute):
                    if attribute == 'email':
                        user.email_verified = True
                    elif attribute == 'phone_number':
                        user.phone_number_verified = True

                    user.save()

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


class CognitoAuthChallengeSerializer(serializers.Serializer):

    id = serializers.UUIDField(read_only=True)
    username = serializers.EmailField(required=True)
    challenge_name = serializers.CharField(max_length=20, required=True)
    challenge_response = serializers.CharField(required=True, write_only=True)
    challenge_delivery = serializers.CharField(max_length=20, required=True)
    destination = serializers.CharField(max_length=14, required=True)
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

            user = get_user_model().objects.get(cognito_id=data[1].get('cognito:username')) if len(data) else None

            if not user:
                raise serializers.ValidationError("User not found")
            validated_data['user'] = user
            return Identity(id=user.id, **validated_data)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Unauthorized(ex)




class CogrnitoAuthRetreiveSerializer(serializers.Serializer):
    resource_name = 'identities'
    id = serializers.UUIDField(read_only=True)
    username = serializers.EmailField(required=True, source='preferred_username', write_only=True)
    password = serializers.CharField(max_length=50, required=False, write_only=True)
    id_token = serializers.CharField(read_only=True)
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=False, required=False)
    user = serializers.SerializerMethodField()
    # user = UserSerializer

    def get_user(self, data):
        return UserSerializer(instance=data.user, context=self.context).data

    related_serializers = {
        'user': 'frontend_api.serializers.UserSerializer',
    }

    def validate(self, data):
        if not data.get('refresh_token') and not data.get('password'):
            raise Unauthorized('Credentials not found')

        return data

    def retreive(self, validated_data):
        try:
            validated_data['username'] = validated_data['preferred_username']
            if validated_data.get('refresh_token'):
                result = helpers.refresh_session(validated_data)
            else:
                result = helpers.initiate_auth(validated_data)

            if result.get('AuthenticationResult'):
                return self._retreive_auth_result(validated_data, result)
            elif result.get('ChallengeName'):
                return self._retreive_auth_challenge(validated_data, result)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Unauthorized(ex)


    @staticmethod
    def _retreive_auth_result(validated_data, result):
        tokens = result.get('AuthenticationResult')

        data = mid_helpers.decode_token(tokens.get('IdToken'))
        validated_data['id_token'] = tokens.get('IdToken')
        validated_data['access_token'] = tokens.get('AccessToken')
        if not validated_data.get('refresh_token'):
            validated_data['refresh_token'] = tokens.get('RefreshToken')

        user = get_user_model().objects.get(cognito_id=data[1].get('cognito:username')) if len(data) else None

        if not user:
            raise serializers.ValidationError("User not found")
        validated_data['user'] = user
        return Identity(id=user.id, **validated_data)


    @staticmethod
    def _retreive_auth_challenge(validated_data, result):
        params = result.get('ChallengeParameters')
        session = result.get('Session')
        id = params.get('USER_ID_FOR_SRP')
        validated_data['challenge_name'] = result.get('ChallengeName')
        validated_data['challenge_delivery'] = params.get('CODE_DELIVERY_DELIVERY_MEDIUM')
        validated_data['destination'] = params.get('CODE_DELIVERY_DESTINATION')
        validated_data['session'] = session
        # validated_data['id'] = id

        return Challenge(id=id, **validated_data)


class CognitoAuthSerializer(CogrnitoAuthRetreiveSerializer):

    user_attributes = ListField(child=CognitoAttributeFiled(required=True), required=True)
    username = serializers.EmailField(required=True, source='preferred_username', write_only=True)
    password = serializers.CharField(max_length=50, required=False, write_only=True)
    account_type = serializers.ChoiceField(choices=('business', 'personal'))
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
            validated_data['username'] = validated_data['preferred_username']
            result = helpers.sign_up(validated_data)
            return CogrnitoAuthRetreiveSerializer.retreive(validated_data)
            # return Identity(id=result.get('UserSub'), **validated_data)
        except Exception as ex:
            logger.error(f'general {ex}')
            raise Unauthorized(ex)

    @staticmethod
    def update(instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        return instance
