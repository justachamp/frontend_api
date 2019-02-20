
from rest_framework_json_api.serializers import HyperlinkedModelSerializer

from frontend_api.models import (
    SubUserAccount,
    AdminUserAccount,
    AdminUserPermission,
    SubUserPermission
)

from ..serializers import PolymorphicResourceRelatedField

import logging
logger = logging.getLogger(__name__)


class SubUserPermissionSerializer(HyperlinkedModelSerializer):

    related_serializers = {
        'account': 'frontend_api.serializers.SubUserAccountSerializer'
    }

    included_serializers = {
        'account': 'frontend_api.serializers.SubUserAccountSerializer'
    }

    account = PolymorphicResourceRelatedField(
        'SubUserAccountSerializer',
        many=False,
        queryset=SubUserAccount.objects.all(),
        related_link_view_name='sub-user-permission-related',
        related_link_url_kwarg='pk',
        self_link_view_name='sub-user-permission-relationships',
        required=False
    )

    class Meta:
        model = SubUserPermission
        fields = ('url', 'account', 'manage_sub_user', 'manage_funding_sources', 'manage_unload_accounts',
                  'manage_contract')


class AdminUserPermissionSerializer(HyperlinkedModelSerializer):

    related_serializers = {
        'account': 'frontend_api.serializers.AdminUserAccountSerializer'
    }

    included_serializers = {
        'account': 'frontend_api.serializers.AdminUserAccountSerializer'
    }

    account = PolymorphicResourceRelatedField(
        'AdminUserAccountSerializer',
        many=False,
        queryset=AdminUserAccount.objects.all(),
        related_link_view_name='admin-user-permission-related',
        related_link_url_kwarg='pk',
        self_link_view_name='admin-user-permission-relationships',
        required=False
    )

    class Meta:
        model = AdminUserPermission
        fields = ('url', 'account', 'manage_admin_user', 'manage_tax', 'manage_fee', 'can_login_as_user',)