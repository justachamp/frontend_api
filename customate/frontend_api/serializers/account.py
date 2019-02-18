
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
    ACCOUNT_ADDITIONAL_FIELDS)

import logging
logger = logging.getLogger(__name__)


class SubUserAccountSerializer(FlexFieldsJsonFieldSerializerMixin, HyperlinkedModelSerializer):

    related_serializers = {
        'user': 'frontend_api.serializers.SubUserSerializer',
        'owner_account': 'frontend_api.serializers.UserAccountSerializer',
        'permission': 'frontend_api.serializers.SubUserPermissionSerializer'
    }

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
        fields = ('url', 'user',
                  'owner_account',
                  'permission'
                  )


class UserAccountSerializer(FlexFieldsJsonFieldSerializerMixin, HyperlinkedModelSerializer):

    @property
    def service(self):
        return AccountService(self.instance)

    @property
    def additional_key(self):
        return self.service.get_account_country()

    related_serializers = {
        'user': 'frontend_api.serializers.UserSerializer',
        'company': 'frontend_api.serializers.CompanySerializer',
        'sub_user_accounts': 'frontend_api.serializers.SubUserAccountSerializer'
    }

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


class AdminUserAccountSerializer(HyperlinkedModelSerializer):

    related_serializers = {
        'user': 'frontend_api.serializers.AdminUserSerializer',
        'permission': 'frontend_api.serializers.AdminUserPermissionSerializer'
    }

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
        fields = ('url', 'user', 'permission')


class AccountSerializer(PolymorphicModelSerializer):
    polymorphic_serializers = [UserAccountSerializer, AdminUserAccountSerializer, SubUserAccountSerializer]

    class Meta:
        model = Account
        fields = '__all__'
