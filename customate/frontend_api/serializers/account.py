
from rest_framework_json_api.serializers import (
    HyperlinkedModelSerializer,
)

from frontend_api.services.account import AccountService
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
    EnumField,
    ResourceRelatedField,
    PolymorphicResourceRelatedField,
    FlexFieldsJsonFieldSerializerMixin,
    PolymorphicModelSerializer,
    CharField,
    DateField
)

import logging
logger = logging.getLogger(__name__)

ACCOUNT_ADDITIONAL_FIELDS = {
    'GB': {
        'driver_licence_number': CharField(source='country_fields.driver_licence_number', default=None),
        'driver_licence_postcode': CharField(source='country_fields.driver_licence_postcode', default=None),
        'driver_licence_issue_date': DateField(source='country_fields.driver_licence_issue_date', default=None)
    },
    'IT': {'tax_code': CharField(source='country_fields.tax_code', default=None)},
    'DK': {'id_card_number': CharField(source='country_fields.id_card_number', default=None)},
    'SP': {'tax_id': CharField(source='country_fields.tax_id', default=None)}
}


class AccountFlexFieldsJsonFieldSerializerMixin(FlexFieldsJsonFieldSerializerMixin):

    def __init__(self):
        self.__service = None

    @property
    def service(self):
        if not self.__service:
            self.__service = AccountService(self.instance)
        return self.__service

    @property
    def additional_key(self):
        return self.service.get_account_country()


class SubUserAccountSerializer(AccountFlexFieldsJsonFieldSerializerMixin, HyperlinkedModelSerializer):

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
        related_link_view_name='sub-user-account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='sub-user-account-relationships',
        required=False
    )

    class Meta:
        model = SubUserAccount
        additional_fields = ACCOUNT_ADDITIONAL_FIELDS
        fields = ('url', 'user', 'owner_account', 'permission')


class UserAccountSerializer(AccountFlexFieldsJsonFieldSerializerMixin, HyperlinkedModelSerializer):

    included_serializers = {
        'user': 'frontend_api.serializers.UserSerializer',
        'company': 'frontend_api.serializers.CompanySerializer',
        'sub_user_accounts': 'frontend_api.serializers.SubUserAccountSerializer'
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

    account_type = EnumField(enum=AccountType)

    class Meta:
        model = UserAccount
        additional_fields = ACCOUNT_ADDITIONAL_FIELDS
        fields = (
            'url',
            'account_type',
            'gbg_authentication_count',
            'is_verified',
            'can_be_verified',
            'position',
            'user',
            'company',
            'sub_user_accounts'
        )


class AdminUserAccountSerializer(AccountFlexFieldsJsonFieldSerializerMixin, HyperlinkedModelSerializer):

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

    class Meta:
        model = Account
        fields = '__all__'
