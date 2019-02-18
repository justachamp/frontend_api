
from rest_framework_json_api.serializers import (
    HyperlinkedModelSerializer,
)
from core.fields import UserRole, UserStatus
from core.models import User
from authentication.cognito.core.mixins import AuthSerializerMixin
from frontend_api.models import (
    SubUserAccount,
    AdminUserAccount,
    AdminUserPermission,
    SubUserPermission,
    UserAccount,
    Address
)

from ..serializers import (
    ResourceRelatedField,
    PolymorphicResourceRelatedField,
    ValidationError,
    EnumField,
    UserAccountSerializer
)


class BaseUserSerializer(HyperlinkedModelSerializer):
    role = EnumField(enum=UserRole, read_only=True)
    status = EnumField(enum=UserStatus)

    class Meta:
        model = User
        fields = ('url', 'role', 'status', 'username', 'first_name', 'last_name', 'middle_name', 'phone_number',
                  'phone_number_verified', 'email_verified', 'mfa_enabled', 'is_verified',
                  'birth_date', 'last_name', 'email', 'address', 'account', 'title', 'gender', 'country_of_birth',
                  'mother_maiden_name', 'passport_number', 'passport_date_expiry', 'passport_country_origin')


class BaseAuthUserSerializereMixin(AuthSerializerMixin):
    def validate_phone_number(self, value):
        if self.auth.check('phone_number', value):
            self.initial_data['phone_number_verified'] = self.auth.check('phone_number_verified', True)
        else:
            user = self.context.get('request').user
            if user and user.mfa_enabled:
                raise ValidationError('Multi factor authentication enabled.')
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


class SubUserSerializer(BaseUserSerializer):
    related_serializers = {
        'address': 'frontend_api.serializers.UserAddressSerializer',
        'account': 'frontend_api.serializers.SubUserAccountSerializer'
    }

    included_serializers = {
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

    account = PolymorphicResourceRelatedField(
        'SubUserAccountSerializer',
        many=False,
        queryset=SubUserAccount.objects,
        related_link_view_name='sub-user-account-related',
        related_link_url_kwarg='pk',
        self_link_view_name='sub-user-account-relationships',
        required=False
    )

    def create(self, validated_data):
        user = User(**validated_data)
        user.role = UserRole.sub_user
        user.status = UserStatus.pending
        address = Address()
        address.save()
        user.address = address
        user.save()
        owner_account = self.context.get('request').user.account
        account = SubUserAccount(owner_account=owner_account, user=user)
        account.save()
        permission = SubUserPermission(account=account)
        permission.save()
        return user


class AdminUserSerializer(BaseUserSerializer):
    related_serializers = {
        'address': 'frontend_api.serializers.UserAddressSerializer',
        'account': 'frontend_api.serializers.AdminUserAccountSerializer'
    }

    included_serializers = {
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

    account = PolymorphicResourceRelatedField(
        'AdminUserAccountSerializer',
        many=False,
        queryset=AdminUserAccount.objects,
        related_link_view_name='user-related',
        related_link_url_kwarg='pk',
        self_link_view_name='user-relationships',
        required=False
    )

    def create(self, validated_data):
        user = User(**validated_data)
        user.role = UserRole.admin
        user.status = UserStatus.pending
        address = Address()
        address.save()
        user.save()
        account = AdminUserAccount(user=user)
        account.save()
        permission = AdminUserPermission(account=account)
        permission.save()
        return user


class UserSerializer(BaseUserSerializer, BaseAuthUserSerializereMixin):

    related_serializers = {
        'address': 'frontend_api.serializers.UserAddressSerializer',
        'account': 'frontend_api.serializers.UserAccountSerializer'
    }

    included_serializers = {
        'address': 'frontend_api.serializers.UserAddressSerializer',
        'account': 'frontend_api.serializers.UserAccountSerializer'
    }

    address = ResourceRelatedField(
        many=False,
        queryset=Address.objects,
        related_link_view_name='user-related',
        related_link_url_kwarg='pk',
        self_link_view_name='user-relationships',
        required=False
    )

    account = PolymorphicResourceRelatedField(
        UserAccountSerializer,
        many=False,
        queryset=UserAccount.objects,
        related_link_view_name='user-related',
        related_link_url_kwarg='pk',
        self_link_view_name='user-relationships',
        required=False
    )
