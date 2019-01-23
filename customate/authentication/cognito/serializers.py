from rest_framework_json_api import serializers, exceptions
from rest_framework.fields import Field, DictField, ListField
from rest_framework import status as status_codes

from authentication.cognito.core.constants import NEW_PASSWORD_CHALLENGE
from authentication.cognito.models import Identity, Verification, Challenge, Invitation
from django.contrib.auth import get_user_model
from authentication.cognito.core import helpers
from authentication.cognito.exceptions import Unauthorized
from authentication.cognito.middleware import helpers as mid_helpers
from django.db import transaction
from authentication.cognito.core.base import generate_password
import logging

from frontend_api.fields import AccountType
from frontend_api.models import Account, Company, AdminUserAccount, SubUserAccount, UserAccount
from frontend_api.serializers import UserSerializer
from authentication.cognito.core.mixins import AuthSerializerMixin
from authentication import settings
from authentication.cognito.middleware import helpers as m_helpers
from core.fields import UserRole, UserStatus

logger = logging.getLogger(__name__)


class CognitoAttributeFiled(Field):

    def to_representation(self, data):
        return data

    def to_internal_value(self, data):
        return data

class BaseAuthValidationMixin(object):
    @staticmethod
    def validate_user_attributes(data):
        for item in data:
            if item.get('Name') == 'email':
                email = item['Value'].lower()
                item['Value'] = email
            if get_user_model().objects.filter(email=email).exists():
                raise serializers.ValidationError("Email already exists you cannot register the same email twice")

        return data

    @staticmethod
    def validate_username(email):
        email = email.lower()
        if get_user_model().objects.filter(email=email).exists():
            raise serializers.ValidationError("Email already exists you cannot register the same email twice")
        return email

class CognitoAuthVerificationSerializer(serializers.Serializer):
    id = serializers.UUIDField(write_only=True)
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


class CognitoMfaSerializer(serializers.Serializer):
    resource_name = 'identities'
    id = serializers.UUIDField(read_only=True)
    access_token = serializers.CharField(write_only=True, required=True)
    enable = serializers.BooleanField(write_only=True, required=True)

    @staticmethod
    def mfa_preference(validated_data):
        try:
            data = helpers.mfa_preference(validated_data)
            user, _, _, _ = m_helpers.get_tokens(access_token=validated_data['access_token'])
            enable_mfa = validated_data['enable']
            if enable_mfa and not user.phone_number_verified:
                raise ValueError("Phone number unverified")

            status = data.get('ResponseMetadata').get('HTTPStatusCode')
            if status == status_codes.HTTP_200_OK:
                # TODO reomve user from serializer

                user.mfa_enabled = enable_mfa
                user.save()
                return status_codes.HTTP_204_NO_CONTENT

            return status
        except Exception as ex:
            logger.error(f'general {ex}')
            raise Unauthorized(ex)


class CognitoAuthAttributeVerifySerializer(serializers.Serializer, AuthSerializerMixin):
    resource_name = 'identities'
    id = serializers.UUIDField(read_only=True)
    attribute_name = serializers.ChoiceField(required=True, allow_blank=False, choices=('email', 'phone_number'))
    access_token = serializers.CharField(write_only=True, required=True)
    code = serializers.CharField(max_length=50, required=False, write_only=True)

    @staticmethod
    def verify_attribute(validated_data):
        try:
            data = helpers.verify_attribute(validated_data)

            status = data.get('ResponseMetadata').get('HTTPStatusCode')
            if status == status_codes.HTTP_200_OK:
                # TODO reomve user from serializer
                user, _, _, _ = m_helpers.get_tokens(access_token=validated_data['access_token'])
                attribute = validated_data['attribute_name']
                if getattr(user, attribute):
                    if attribute == 'email':
                        user.email_verified = True
                    elif attribute == 'phone_number':
                        user.phone_number_verified = True
                    user.check_verification()
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

            user = get_user_model().objects.get(cognito_id=data[1].get('cognito:username')) if len(data) else None

            if not user:
                raise ValueError("User not found")
            if validated_data['challenge_name'] == NEW_PASSWORD_CHALLENGE:
                user.status = UserStatus.active
                user.save()
            validated_data['user'] = user
            return Identity(id=user.id, **validated_data)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Unauthorized(ex)


class CogrnitoAuthRetrieveSerializer(serializers.Serializer):
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

        data = mid_helpers.decode_token(tokens.get('IdToken'))
        validated_data['id_token'] = tokens.get('IdToken')
        validated_data['access_token'] = tokens.get('AccessToken')
        if not validated_data.get('refresh_token'):
            validated_data['refresh_token'] = tokens.get('RefreshToken')

        try:
            user = get_user_model().objects.get(cognito_id=data[1].get('cognito:username')) if len(data) else None
        except Exception as ex:
            if getattr(settings, 'AUTO_CREATE_USER', False):
                with transaction.atomic():
                    cognito_user = data[1]
                    email = cognito_user.get('email')
                    logger.error(f'process_request user_attributes: {cognito_user}')
                    user = get_user_model().objects.create(
                        username=email,
                        email=email,
                        email_verified=cognito_user.get('email_verified'),
                        phone_number=cognito_user.get('phone_number', ''),
                        phone_number_verified=cognito_user.get('phone_number_verified', False),
                        cognito_id=cognito_user.get('cognito:username'),
                        role=cognito_user.get('custom:account_type', UserRole.owner),
                        first_name=cognito_user.get('given_name', ''),
                        last_name=cognito_user.get('family_name', '')
                    )

                    self._restore_account(user)
                    user.save()
                # user = None
            else:
                user = None

        if not user:
            raise Exception("User not found")
        elif user.status == UserStatus.inactive:
            raise Exception("User is inactive")
        validated_data['user'] = user
        return Identity(id=user.id, **validated_data)

    @staticmethod
    def _restore_account(user):
        role = user.role
        if role == UserRole.owner:
            account = UserAccount.objects.create(account_type=AccountType.personal, user=user)
            account.save()
        elif role == UserRole.admin:
            account = AdminUserAccount.objects.create(user=user)
            account.save()
        elif role == UserRole.sub_user:
            account = SubUserAccount.objects.create(user=user)
            account.save()
            # company = Company.objects.create(is_active=(account_type == BUSINESS_ACCOUNT))
            # account.company = company
            # company.save()



    @staticmethod
    def _retrieve_auth_challenge(validated_data, result):
        params = result.get('ChallengeParameters')
        session = result.get('Session')
        id = params.get('USER_ID_FOR_SRP')
        validated_data['challenge_name'] = result.get('ChallengeName')
        validated_data['challenge_delivery'] = params.get('CODE_DELIVERY_DELIVERY_MEDIUM')
        validated_data['destination'] = params.get('CODE_DELIVERY_DESTINATION')
        validated_data['session'] = session
        # validated_data['id'] = id

        return Challenge(id=id, **validated_data)


class CognitoInviteUserSerializer(serializers.Serializer, BaseAuthValidationMixin):
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
            validated_data['action'] = validated_data.get('action', '') #SUPPRESS
            validated_data['delivery'] = validated_data.get('delivery', ['EMAIL'])
            user = helpers.admin_create_user(validated_data)

            return Invitation(id=user.get('Username'), **validated_data)
        except Exception as ex:
            logger.error(f'general {ex}')
            raise Unauthorized(ex)


class CognitoAuthSerializer(BaseAuthValidationMixin, CogrnitoAuthRetrieveSerializer):

    user_attributes = ListField(child=CognitoAttributeFiled(required=True), required=True)
    username = serializers.EmailField(required=True, source='preferred_username', write_only=True)
    password = serializers.CharField(max_length=50, required=False, write_only=True)
    account_type = serializers.ChoiceField(choices=('business', 'personal'))
    id_token = serializers.CharField(max_length=256, write_only=True, required=False)
    access_token = serializers.CharField(max_length=256, write_only=True, required=False)
    refresh_token = serializers.CharField(max_length=256, write_only=True, required=False)

    @staticmethod
    def create(validated_data):
        try:
            validated_data['preferred_username'] = validated_data['preferred_username'].lower()
            validated_data['username'] = validated_data['preferred_username']
            validated_data['user_attributes'] = [
                {'Name': 'email', 'Value': validated_data['preferred_username']},
                {'Name': 'custom:account_type', 'Value': UserRole.owner.value}
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
