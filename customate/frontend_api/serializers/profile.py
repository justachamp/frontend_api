from django.db import transaction
from phonenumber_field.phonenumber import PhoneNumber
from rest_framework_json_api.serializers import Serializer

from authentication.cognito.core.mixins import AuthSerializerMixin
from frontend_api.exceptions import GBGVerificationError
from frontend_api.services.account import ProfileValidationService
from rest_framework.exceptions import ValidationError

from core.fields import SerializerField
from frontend_api.serializers import (
    UUIDField,
    CharField,
    UserSerializer,
    UserAddressSerializer,
    AccountSerializer
)
from phonenumber_field.modelfields import PhoneNumberField

import logging

logger = logging.getLogger(__name__)


class DomainService:
    _service_object = None
    __service = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = self.instance

    @property
    def service(self):
        return self.__service

    @service.setter
    def service(self, instance):
        self.__service = self._service_object(instance)


class BaseAuthUserSerializerMixin(AuthSerializerMixin):

    def _validate_attribute_verification(self, attr, verify_attr, value, data, alias=None):

        if self.auth.check(attr, value):
            data[verify_attr] = self.auth.check(verify_attr, 'true')
        else:
            data[verify_attr] = False
            self.auth.update_attribute(attr, value)

        if alias:
            data[alias] = value
            # setattr(self.instance, alias, value)

        return value

    def _validate_phone_number(self, data, value):
        if isinstance(value, PhoneNumberField) or isinstance(value, PhoneNumber):
            value = value.as_e164
        return self._validate_attribute_verification('phone_number', 'phone_number_verified', value, data)

    def _validate_email(self, data, value):
        return self._validate_attribute_verification('email', 'email_verified', value, data, 'username')

    def _validate_first_name(self, value):
        self.auth.update_attribute('given_name', value)
        return value

    def _validate_last_name(self, value):
        self.auth.update_attribute('family_name', value)
        return value

    def _validate_user_role(self, value):
        self.auth.update_attribute('custom:account_type', value.value)
        return value


class CognitoCredentialSerializer(Serializer):
    id_token = CharField(read_only=True)
    access_token = CharField(read_only=True)
    refresh_token = CharField(read_only=False, required=False)


class ProfileSerializer(DomainService, BaseAuthUserSerializerMixin, Serializer):
    _service_object = ProfileValidationService
    id = UUIDField()
    user = SerializerField(resource=UserSerializer)
    address = SerializerField(resource=UserAddressSerializer, required=False)
    account = SerializerField(resource=AccountSerializer, required=False)

    @property
    def additional_key(self):
        profile = self.context.get('profile')
        return 'credentials' if profile and profile.credentials else None

    def validate(self, attrs):
        self.service.validate_profile(attrs, True)
        self._validate_user(attrs)
        return attrs

    def _validate_user(self, attrs):
        user_data = attrs['user']
        user = self.instance.user
        user_data['phone_number'] = self._validate_phone_number(
            user_data, user_data.get('phone_number', user.phone_number))
        user_data['email'] = self._validate_email(user_data, user_data.get('email', user.email))
        user_data['first_name'] = self._validate_first_name(user_data.get('first_name', user.first_name))
        user_data['last_name'] = self._validate_last_name(user_data.get('last_name', user.last_name))
        # user['role'] = self.instance.user.role
        # user['role'] = self._validate_user_role(self.instance.user.role)

        return attrs

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @transaction.atomic
    def update(self, instance, validated_data):

        # Deny ability to allow sms notifications if phone number is not verified.
        validated_user_fields = validated_data.get("user", {})
        if not instance.user.phone_number_verified \
                and validated_user_fields.get("notify_by_phone"):
            raise ValidationError("Please, verify your phone number first.")

        def update_model(model, data):
            for (key, val) in data.items():
                setattr(model, key, val)
            model.save()

        update_model(instance.user, validated_data.get('user', {}))
        update_model(instance.address, validated_data.get('address', {}))
        update_model(instance.account, validated_data.get('account', {}))

        try:
            if not validated_data.get("skip_gbg", False):
                self.service.verify_profile(instance)
        except GBGVerificationError as e:
            if not validated_data.get("ignore_gbg_exception", False):
                raise e
        return instance
