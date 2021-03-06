import logging
from django.utils.functional import cached_property
from django.conf import settings

from rest_framework_json_api import utils
from rest_framework_json_api.serializers import (
    HyperlinkedModelSerializer
)

from core.fields import SerializerField
from core.models import User

from payment_api.core.resource.fields import ExternalResourceRelatedField as ERRField
from payment_api.core.client import Client
from payment_api.core.resource.models import ResourceQueryset

from frontend_api.services.account import AccountService
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
from frontend_api.serializers import (
    EnumField,
    AdminUserPermissionSerializer,
    SubUserPermissionSerializer,
    ResourceRelatedField,
    PolymorphicResourceRelatedField,
    FlexFieldsSerializerMixin,
    PolymorphicModelSerializer,
    CharField,
    DateField
)

logger = logging.getLogger(__name__)

ACCOUNT_ADDITIONAL_FIELDS = {
    'GB': {
        'driver_licence_number': {
            'cls': CharField,
            'kwargs': {'source': 'country_fields.driver_licence_number', 'required': False, 'allow_blank': True}
        },
        'driver_licence_postcode': {
            'cls': CharField,
            'kwargs': {'source': 'country_fields.driver_licence_postcode', 'required': False, 'allow_blank': True}
        },
        'driver_licence_issue_date': {
            'cls': DateField,
            'kwargs': {'source': 'country_fields.driver_licence_issue_date', 'required': False, 'allow_null': True}
        }
    },
    'IT': {'tax_code': {
        'cls': CharField,
        'kwargs': {'source': 'country_fields.tax_code', 'required': False, 'allow_blank': True}
    }
    },
    'DK': {'id_card_number': {
        'cls': CharField,
        'kwargs': {'source': 'country_fields.id_card_number', 'required': False, 'allow_blank': True}
    }
    },
    'ES': {'tax_id': {
        'cls': CharField,
        'kwargs': {'source': 'country_fields.tax_id', 'required': False, 'allow_blank': True}
    }
    },
    'sub_user': {'permission': {
        'cls': SerializerField,
        'kwargs': {'resource': SubUserPermissionSerializer, 'required': False, 'read_only': True}
    }
    },
    'admin': {'permission': {
        'cls': SerializerField,
        'kwargs': {'resource': AdminUserPermissionSerializer, 'required': False, 'read_only': True}
    }
    }
}


class ExternalResourceRelatedField(ERRField):
    base_url = settings.PAYMENT_API_URL

    def __init__(self, resource_identifier=None, *args, **kwargs):
        self._resource_identifier = resource_identifier
        super().__init__(*args, **kwargs)

    @cached_property
    def client(self):
        client = Client(self.base_url)
        client.resource_mapping = {'id': {'op': 'copy', 'value': 'pk'}}
        return client

    def get_attribute(self, instance):
        queryset = ResourceQueryset(self.source, self.client, 'get')
        included = self.get_included_resources()
        if len(included):
            queryset.including(*included)
        attr_id = getattr(instance, self.attribute_identity_field, None)
        attr = queryset.one(attr_id, map_attributes=True) if attr_id else None
        setattr(instance, self.field_name, attr)
        self.context['client'] = self.client

        return attr

    @property
    def attribute_identity_field(self):
        return f'{self.field_name}_id'

    def get_included_resources(self):
        included_resources = utils.get_included_resources(self.context.get('request'))
        root_source = f'{self.field_name}.'
        return [source.lstrip(root_source) for source in included_resources if source.startswith(root_source)]


class AccountFlexFieldsSerializerMixin(FlexFieldsSerializerMixin):

    def __init__(self, *args, **kwargs):
        self.__service = None
        return super().__init__(*args, **kwargs)

    @property
    def service(self):
        if not self.__service:
            self.__service = AccountService(self.context.get('profile'))
        return self.__service

    @property
    def additional_key(self):
        keys = []
        country_key = self.service.get_account_country()
        if country_key:
            keys.append(country_key)

        self.apply_context_additional_keys(keys)
        return keys

    def apply_context_additional_keys(self, keys):
        additional_keys = self.context.get('additional_keys', {}).get('account', [])
        if 'permission' in additional_keys:
            keys.append(self.service.get_user_role())


class SubUserAccountSerializer(AccountFlexFieldsSerializerMixin, HyperlinkedModelSerializer):
    included_serializers = {
        'user': 'frontend_api.serializers.SubUserSerializer',
        'owner_account': 'frontend_api.serializers.UserAccountSerializer',
        'permission': 'frontend_api.serializers.SubUserPermissionSerializer'
    }

    permission = ResourceRelatedField(
        many=False,
        queryset=SubUserPermission.objects,
        related_link_view_name='sub-user-account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='sub-user-account-relationships',
        required=False
    )

    owner_account = PolymorphicResourceRelatedField(
        'UserAccountSerializer',
        many=False,
        queryset=UserAccount.objects,
        related_link_view_name='sub-user-account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='sub-user-account-relationships',
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

    payment_account_id = CharField(read_only=True, source="owner_account.payment_account_id")

    class Meta:
        model = SubUserAccount
        additional_fields = ACCOUNT_ADDITIONAL_FIELDS
        fields = (
            'url',
            'user',
            'owner_account',
            'permission',
            'gbg_authentication_count',
            'is_verified',
            'is_owner_account_verified',
            'can_be_verified',
            'verification_status',
            'payment_account_id'
        )

        # extra_kwargs = {
        #     'url': {'view_name': 'account-detail', 'lookup_field': 'pk'},
        # }
        # ex'subuseraccount-detail'


class UserAccountSerializer(AccountFlexFieldsSerializerMixin, HyperlinkedModelSerializer):
    included_serializers = {
        'user': 'frontend_api.serializers.UserSerializer',
        'company': 'frontend_api.serializers.CompanySerializer',
        'sub_user_accounts': 'frontend_api.serializers.SubUserAccountSerializer',
        'payment_account': 'payment_api.serializers.PaymentAccountSerializer'
    }

    sub_user_accounts = PolymorphicResourceRelatedField(
        'SubUserAccountSerializer',
        many=True,
        queryset=SubUserAccount.objects.all(),
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
        queryset=Company.objects,
        related_link_view_name='account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='account-relationships',
        required=False
    )

    payment_account = ExternalResourceRelatedField(
        required=False,
        read_only=True,
        related_link_view_name='account-related',
        self_link_view_name='account-relationships',
        source='accounts'
    )

    account_type = EnumField(enum=AccountType, required=False)

    class Meta:
        model = UserAccount
        additional_fields = ACCOUNT_ADDITIONAL_FIELDS
        fields = (
            'url',
            'account_type',
            'payment_account_id',
            'gbg_authentication_count',
            'is_verified',
            'can_be_verified',
            'verification_status',
            'position',
            'user',
            'company',
            'sub_user_accounts',
            'payment_account'
        )


class AdminUserAccountSerializer(AccountFlexFieldsSerializerMixin, HyperlinkedModelSerializer):
    included_serializers = {
        'user': 'frontend_api.serializers.AdminUserSerializer',
        'permission': 'frontend_api.serializers.AdminUserPermissionSerializer'
    }

    user = ResourceRelatedField(
        many=False,
        queryset=User.objects,
        related_link_view_name='admin-user-account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='admin-user-account-relationships',
        required=False
    )

    permission = ResourceRelatedField(
        many=False,
        queryset=AdminUserPermission.objects,
        related_link_view_name='admin-user-account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='admin-user-account-relationships',
        required=False
    )

    class Meta:
        model = AdminUserAccount
        additional_fields = ACCOUNT_ADDITIONAL_FIELDS
        fields = ('url', 'user', 'permission')


class AccountSerializer(PolymorphicModelSerializer):
    polymorphic_serializers = [UserAccountSerializer, AdminUserAccountSerializer, SubUserAccountSerializer]

    included_serializers = {
        'user': 'frontend_api.serializers.UserSerializer',
        'payment_account': 'payment_api.serializers.PaymentAccountSerializer',
    }

    class Meta:
        model = Account
        fields = '__all__'
