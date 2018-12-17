from django.contrib.auth.models import Group
from rest_framework_json_api import serializers
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.serializers import HyperlinkedIdentityField
from rest_framework_json_api.serializers import ResourceIdentifierObjectSerializer
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import (
    get_resource_type_from_model
)
from core.models import User
from authentication.cognito.core.mixins import AuthSerializerMixin
from frontend_api.models import Address, Account, Shareholder, Company
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


class RelativeResourceIdentifierObjectSerializer(ResourceIdentifierObjectSerializer):

    def to_internal_value(self, data):
        if data['type'] != get_resource_type_from_model(self.model_class):
            self.fail(
                'incorrect_model_type', model_type=self.model_class, received_type=data['type']
            )
        # pk = data['id']
        try:
            # if pk != 'null':
            #     return self.model_class.objects.get(pk=pk)
            # else:
            model = self.model_class(data.get('attributes'))
            model.save()
            return model
        # except ObjectDoesNotExist:
        #     self.fail('does_not_exist', pk_value=pk)
        except (TypeError, ValueError):
            self.fail('incorrect_type', data_type=type(data['pk']).__name__)


class UserSerializer(serializers.HyperlinkedModelSerializer, AuthSerializerMixin):


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

    def validate_phone_number(self, value):
        """
        Check that the blog post is about Django.
        """
        if self.auth.check('phone_number', value):
            self.initial_data['phone_number_verified'] = self.auth.check('phone_number_verified', True)
        else:
            self.initial_data['phone_number_verified'] = False
            self.auth.update_attribute('phone_number', value)

        return value

    def validate_email(self, value):
        """
        Check that the blog post is about Django.
        """
        if self.auth.check('email', value):
            self.initial_data['email_verified'] = self.auth.check('email_verified', True)
        else:
            self.initial_data['email_verified'] = False
            self.auth.update_attribute('email', value)

        self.initial_data['username'] = value
        self.instance.username = value

        return value


    class Meta:
        model = User
        fields = ('url', 'username', 'first_name', 'last_name', 'middle_name', 'phone_number',
                  'phone_number_verified', 'email_verified',
                  'birth_date', 'last_name', 'email', 'groups', 'address', 'account')
        # extra_kwargs = {'username': {'write_only': True}}


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
        'company': 'frontend_api.serializers.CompanySerializer'
    }

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
        fields = ('url', 'account_type', 'position', 'user', 'company')


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

    def update(self, instance, validated_data):
        raise NotImplementedError(
            "Serializers update test"
        )

    class Meta:
        model = Shareholder
        fields = ('url', 'company', 'is_active', 'first_name', 'last_name', 'birth_date', 'country_of_residence')

# class GroupSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Group
#         fields = ('url', 'name')