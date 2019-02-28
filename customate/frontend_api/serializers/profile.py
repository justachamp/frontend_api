from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_json_api.serializers import (
    HyperlinkedModelSerializer,
    Serializer,
    SerializerMethodField
)
from authentication.cognito.core.mixins import AuthSerializerMixin
from frontend_api.serializers import UserAddressSerializer, AccountSerializer, AddressSerializer
from frontend_api.services.account import AccountService, ProfileValidationService
from core.models import User

from frontend_api.models import (
    Account,
    Company,
    SubUserAccount,
    AdminUserAccount,
    AdminUserPermission,
    SubUserPermission,
    UserAccount
)

from frontend_api.fields import AccountType

from ..serializers import (
    UUIDField,
    EnumField,
    ResourceRelatedField,
    PolymorphicResourceRelatedField,
    FlexFieldsJsonFieldSerializerMixin,
    PolymorphicModelSerializer,
    CharField,
    DateField,
    UserSerializer
)
from frontend_api.services.account import ProfileService

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
        # if not self.__service:
        #     self.__service = self._service_object()
        return self.__service

    @service.setter
    def service(self, instance):
        self.__service = self._service_object(instance)


class SerializerField(serializers.Field):

    def __init__(self, resource, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._resource = resource

    def to_representation(self, instance):
        # self._resource.context = self.context
        # return self._resource.to_representation(self, instance)
        return self._resource(context=self.context, instance=instance, partial=True).to_representation(instance)

    def to_internal_value(self, data):
        instance = getattr(self.parent.instance, self.field_name)
        serializer = self._resource(instance=instance, context=self.context, data=data, partial=True)
        try:
            validated_data = serializer.to_internal_value(data)
            return validated_data
        except ValidationError as ex:
            raise ValidationError({self.field_name: ex.detail})


class BaseAuthUserSerializerMixin(AuthSerializerMixin):

    def _validate_attribute_verification(self, attr, verify_attr, value, data, alias=None):

        if self.auth.check(attr, value):
            data[verify_attr] = self.auth.check(verify_attr, True)
        else:
            data[verify_attr] = False
            self.auth.update_attribute(attr, value)

        if alias:
            data[alias] = value
            # setattr(self.instance, alias, value)

        return value

    def _validate_phone_number(self, data, value):
        return self._validate_attribute_verification('phone_number',  'phone_number_verified', value, data)

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


class ProfileSerializer(DomainService, BaseAuthUserSerializerMixin, Serializer):

    _service_object = ProfileValidationService
    id = UUIDField()
    user = SerializerField(resource=UserSerializer)
    address = SerializerField(resource=UserAddressSerializer, required=False)
    account = SerializerField(resource=AccountSerializer, required=False)

    def validate(self, attrs):
        self.service.validate_age(attrs['user'])
        self.service.validate_phone_number(attrs)
        self.service.validate_address_country(attrs)
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

    # def retrieve(self, validated_data):
    #     instance = self.service.save_profile(validated_data)
    #     return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        def update_model(model, data):
            for (key, val) in data.items():
                setattr(model, key, val)
            model.save()

        update_model(instance.user, validated_data.get('user', {}))
        update_model(instance.address, validated_data.get('address', {}))
        update_model(instance.account, validated_data.get('account', {}))
        self.service.verify_profile(instance)
        # instance = self.service.update_profile(instance)
        return instance

