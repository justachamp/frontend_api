from django.contrib.auth.models import Group
from rest_framework_json_api import serializers
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.serializers import HyperlinkedIdentityField
from rest_framework_json_api.serializers import ResourceIdentifierObjectSerializer
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import (
    get_resource_type_from_model
)
from core.models import User, Address
from core.fields import UserRole, UserStatus
from authentication.cognito.core.mixins import AuthSerializerMixin
from frontend_api.models import Account, Shareholder, Company, SubUserAccount, AdminUserAccount
from frontend_api.fields import AccountType, CompanyType

import logging
logger = logging.getLogger(__name__)


class EnumField(serializers.ChoiceField):
    def __init__(self, enum, **kwargs):
        self.enum = enum
        kwargs['choices'] = [(e.name, e.name) for e in enum]
        super(EnumField, self).__init__(**kwargs)

    def to_representation(self, obj):
        return obj.value

    def to_internal_value(self, data):
        try:
            return self.enum[data]
        except KeyError:
            self.fail('invalid_choice', input=data)


# class RelativeResourceIdentifierObjectSerializer(ResourceIdentifierObjectSerializer):
#
#     def to_internal_value(self, data):
#         if data['type'] != get_resource_type_from_model(self.model_class):
#             self.fail(
#                 'incorrect_model_type', model_type=self.model_class, received_type=data['type']
#             )
#         pk = data.get('id')
#         try:
#             if pk != 'Null':
#                 return self.model_class.objects.get(pk=pk)
#             else:
#                 model = self.model_class(data.get('attributes'))
#                 model.save()
#                 return model
#         # except ObjectDoesNotExist:
#         #     self.fail('does_not_exist', pk_value=pk)
#         except (TypeError, ValueError):
#             self.fail('incorrect_type', data_type=type(data['pk']).__name__)



class BaseUserSerializer(serializers.HyperlinkedModelSerializer):
    role = EnumField(enum=UserRole)
    status = EnumField(enum=UserStatus)

    class Meta:
        model = User
        fields = ('url', 'role', 'status', 'username', 'first_name', 'last_name', 'middle_name', 'phone_number',
                  'phone_number_verified', 'email_verified',
                  'birth_date', 'last_name', 'email', 'address', 'account')


class BaseAuthUserSerializereMixin(AuthSerializerMixin):
    def validate_phone_number(self, value):
        if self.auth.check('phone_number', value):
            self.initial_data['phone_number_verified'] = self.auth.check('phone_number_verified', True)
        else:
            self.initial_data['phone_number_verified'] = False
            self.auth.update_attribute('phone_number', value)

        return value

    def validate_email(self, value):
        if self.auth.check('email', value):
            self.initial_data['email_verified'] = self.auth.check('email_verified', True)
        else:
            self.initial_data['email_verified'] = False
            self.auth.update_attribute('email', value)

        self.initial_data['username'] = value
        self.instance.username = value

        return value

    def validate_first_name(self, value):
        self.auth.update_attribute('given_name', value)
        return value

    def validate_last_name(self, value):
        self.auth.update_attribute('family_name', value)
        return value

    def validate_role(self, value):
        self.auth.update_attribute('custom:account_type', value.value)
        return value


class UserSerializer(BaseUserSerializer, BaseAuthUserSerializereMixin):


    related_serializers = {
        'address': 'frontend_api.serializers.UserAddressSerializer',
        'account': 'frontend_api.serializers.AccountSerializer'
    }

    address = ResourceRelatedField(
        many=False,
        queryset=Address.objects,
        related_link_view_name='user-related',
        related_link_url_kwarg='pk',
        self_link_view_name='user-relationships',
        required=False
    )

    account = ResourceRelatedField(
        many=False,
        queryset=Account.objects,
        related_link_view_name='user-related',
        related_link_url_kwarg='pk',
        self_link_view_name='user-relationships',
        required=False
    )


class SubUserSerializer(BaseUserSerializer):
    related_serializers = {
        'address': 'frontend_api.serializers.UserAddressSerializer',
        'account': 'frontend_api.serializers.SubUserAccountSerializer'
    }

    address = ResourceRelatedField(
        many=False,
        queryset=Address.objects,
        related_link_view_name='user-related',
        related_link_url_kwarg='pk',
        self_link_view_name='user-relationships',
        required=False
    )

    account = ResourceRelatedField(
        many=True,
        queryset=SubUserAccount.objects,
        related_link_view_name='sub-user-account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='sub-user-account-relationships',
        required=False
    )

    def create(self, validated_data):
        user = User(**validated_data)
        user.save()
        owner_account = self.context.get('request').user.account
        account = SubUserAccount(owner_account=owner_account, user=user)
        account.save()

        return user


class AdminUserSerializer(BaseUserSerializer):
    related_serializers = {
        'address': 'frontend_api.serializers.UserAddressSerializer',
        'account': 'frontend_api.serializers.AdminUserAccountSerializer'
    }

    address = ResourceRelatedField(
        many=False,
        queryset=Address.objects,
        related_link_view_name='user-related',
        related_link_url_kwarg='pk',
        self_link_view_name='user-relationships',
        required=False
    )

    account = ResourceRelatedField(
        many=True,
        queryset=SubUserAccount.objects,
        related_link_view_name='sub-user-account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='sub-user-account-relationships',
        required=False
    )


class UserAddressSerializer(serializers.HyperlinkedModelSerializer):
    # user = serializers.ReadOnlyField(source='user.id')

    related_serializers = {
        'user': 'frontend_api.serializers.UserSerializer'
    }

    user = ResourceRelatedField(
        many=False,
        queryset=User.objects,
        related_link_view_name='address-related',
        related_link_url_kwarg='pk',
        self_link_view_name='address-relationships',
        required=False

    )

    class Meta:
        model = Address
        fields = ('url', 'address', 'country', 'address_line_1', 'address_line_2',
                  'city', 'locality', 'postcode', 'user')


class AddressSerializer(serializers.HyperlinkedModelSerializer):

    related_serializers = {
        'user': 'frontend_api.serializers.UserSerializer',
        'company': 'frontend_api.serializers.CompanySerializer'
    }

    user = ResourceRelatedField(
        many=False,
        queryset=User.objects,
        related_link_view_name='address-related',
        related_link_url_kwarg='pk',
        self_link_view_name='address-relationships',
        required=False

    )

    company = ResourceRelatedField(
        many=False,
        queryset=Company.objects,
        related_link_view_name='address-related',
        related_link_url_kwarg='pk',
        self_link_view_name='address-relationships',
        required=False

    )

    class Meta:
        model = Address
        fields = ('url', 'address', 'country', 'address_line_1', 'address_line_2',
                  'city', 'locality', 'postcode', 'user', 'company')


class CompanyAddressSerializer(serializers.HyperlinkedModelSerializer):
    # user = serializers.ReadOnlyField(source='user.id')

    related_serializers = {
        'company': 'frontend_api.serializers.CompanySerializer'
    }

    company = ResourceRelatedField(
        many=False,
        queryset=Company.objects,
        related_link_view_name='address-related',
        related_link_url_kwarg='pk',
        self_link_view_name='address-relationships',
        required=False
    )

    class Meta:
        model = Address
        fields = ('url', 'address', 'country', 'address_line_1', 'address_line_2',
                  'city', 'locality', 'postcode', 'company')


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    # user = serializers.ReadOnlyField(source='user.id')

    related_serializers = {
        'user': 'frontend_api.serializers.UserSerializer',
        'company': 'frontend_api.serializers.CompanySerializer',
        'sub_user_accounts': 'frontend_api.serializers.SubUserAccountSerializer'
    }

    sub_user_accounts = ResourceRelatedField(
        many=True,
        queryset=SubUserAccount.objects,
        related_link_view_name='account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='account-relationships',
        required=False
    )

    user = ResourceRelatedField(
        many=False,
        queryset=User.objects,
        related_link_view_name='account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='account-relationships',
        required=False
    )

    company = ResourceRelatedField(
        many=False,
        queryset=User.objects,
        related_link_view_name='account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='account-relationships',
        required=False
    )

    account_type = EnumField(enum=AccountType)

    class Meta:
        model = Account
        fields = ('url', 'account_type', 'position', 'user', 'company', 'sub_user_accounts')


class SubUserAccountSerializer(serializers.HyperlinkedModelSerializer):

    related_serializers = {
        'user': 'frontend_api.serializers.SubUserSerializer',
        'owner_account': 'frontend_api.serializers.AccountSerializer'
    }

    owner_account = ResourceRelatedField(
        many=False,
        queryset=Account.objects,
        related_link_view_name='user-related',
        related_link_url_kwarg='pk',
        self_link_view_name='user-relationships',
        required=False
    )

    user = ResourceRelatedField(
        many=False,
        queryset=User.objects,
        related_link_view_name='sub-user-account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='sub-user-account-relationships',
        required=False
    )

    class Meta:
        model = SubUserAccount
        fields = ('url', 'user', 'owner_account')


class AdminUserAccountSerializer(serializers.HyperlinkedModelSerializer):

    related_serializers = {
        'user': 'frontend_api.serializers.AdminUserSerializer'
    }

    user = ResourceRelatedField(
        many=False,
        queryset=User.objects,
        related_link_view_name='admin-user-account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='admin-user-account-relationships',
        required=False
    )

    class Meta:
        model = AdminUserAccount
        fields = ('url', 'user')


class CompanySerializer(serializers.HyperlinkedModelSerializer):

    related_serializers = {
        'account': 'frontend_api.serializers.AccountSerializer',
        'address': 'frontend_api.serializers.CompanyAddressSerializer',
        'shareholders': 'frontend_api.serializers.ShareholderSerializer'
    }

    account = ResourceRelatedField(
        many=False,
        queryset=Account.objects,
        related_link_view_name='company-related',
        related_link_url_kwarg='pk',
        self_link_view_name='company-relationships',
        required=False
    )

    shareholders = ResourceRelatedField(
        many=True,
        queryset=Shareholder.objects,
        related_link_view_name='company-related',
        related_link_url_kwarg='pk',
        self_link_view_name='company-relationships',
        required=False
    )

    address = ResourceRelatedField(
        many=False,
        queryset=Address.objects,
        related_link_view_name='company-related',
        related_link_url_kwarg='pk',
        self_link_view_name='company-relationships',
        required=False
    )

    company_type = EnumField(enum=CompanyType)

    class Meta:
        model = Company
        fields = ('url', 'company_type','is_active', 'registration_business_name', 'registration_number',
                  'is_private', 'shareholders', 'account', 'address')


class ShareholderSerializer(serializers.HyperlinkedModelSerializer):

    related_serializers = {
        'company': 'frontend_api.serializers.CompanySerializer',
    }

    company = ResourceRelatedField(
        many=False,
        queryset=Company.objects,
        related_link_view_name='shareholder-related',
        related_link_url_kwarg='pk',
        self_link_view_name='shareholder-relationships',
        required=False
    )

    class Meta:
        model = Shareholder
        fields = ('url', 'company', 'is_active', 'first_name', 'last_name', 'birth_date', 'country_of_residence')

# class GroupSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Group
#         fields = ('url', 'name')