from django.contrib.auth.models import Group
from rest_framework_json_api import serializers
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.serializers import HyperlinkedIdentityField
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import (
    get_resource_type_from_model
)
from core.models import User
from frontend_api.models import Address, Account, Shareholder, Company
import logging
logger = logging.getLogger(__name__)



class UserSerializer(serializers.HyperlinkedModelSerializer):

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

    # def update(self, validated_data, test):
    #     logger.error(f'validated_data {validated_data} {test}')

    # def address_update(self, *args, **kwargs):
    #     logger.error(f'validated_data {kwargs}')

        # tracks_data = validated_data.pop('tracks')
        # album = Album.objects.create(**validated_data)
        # for track_data in tracks_data:
        #     Track.objects.create(album=album, **track_data)
        # return album



# class UserSerializer(serializers.HyperlinkedModelSerializer):
#     snippets = serializers.HyperlinkedRelatedField(many=True, view_name='api-root', read_only=True)
#     snippets = ResourceRelatedField(
#         queryset=Snippet.objects,
#         many=True,
#         # related_link_view_name='user-snippet-list',
#         related_link_url_kwarg='user_pk',
#         # self_link_view_name='snippet-list'
#     )

    class Meta:
        model = User
        fields = ('url', 'username', 'first_name', 'last_name', 'middle_name', 'phone_number',
                  'birth_date', 'last_name', 'email', 'groups', 'address', 'account')


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
    # user = serializers.ReadOnlyField(source='user.id')

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
        queryset=Shareholder.objects,
        related_link_view_name='shareholder-related',
        related_link_url_kwarg='pk',
        self_link_view_name='shareholder-relationships',
        required=False
    )

    def update(self, instance, validated_data):
        raise NotImplementedError(
            "Serializers update test"
        )

    def to_internal_value(self, data):
        if data['type'] != get_resource_type_from_model(self.model_class):
            self.fail(
                'incorrect_model_type', model_type=self.model_class, received_type=data['type']
            )
        pk = data['id']
        try:
            if pk is not 'null':
                return self.model_class.objects.get(pk=pk)
            else:
                return data.get('attributes')
        except ObjectDoesNotExist:
            self.fail('does_not_exist', pk_value=pk)
        except (TypeError, ValueError):
            self.fail('incorrect_type', data_type=type(data['pk']).__name__)

    class Meta:
        model = Shareholder
        fields = ('url', 'company','is_active', 'first_name', 'last_name', 'birth_date', 'country_of_residence')

# class GroupSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Group
#         fields = ('url', 'name')