import logging

from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework_json_api.serializers import (
    HyperlinkedModelSerializer)
from core.fields import UserRole, UserStatus, UserTitle, Gender, Country
from core.models import User
from frontend_api.models import (
    SubUserAccount,
    AdminUserAccount,
    AdminUserPermission,
    SubUserPermission,
    UserAccount,
    Address
)
from authentication.cognito.core import helpers
from core.fields import UserRole, UserStatus

from ..serializers import (
    ResourceRelatedField,
    PolymorphicResourceRelatedField,
    EnumField,
    EmailField,
    CharField,
    UserAccountSerializer,
    UniqueValidator,
)

logger = logging.getLogger(__name__)


class PhoneField(PhoneNumberField):
    def to_internal_value(self, value):
        super().to_internal_value(value)  # Returns PhoneNumber instance, that couldn't be adapted to SQL parameter
        return value


class BaseUserSerializer(HyperlinkedModelSerializer):
    role = EnumField(enum=UserRole, read_only=True)
    username = CharField(required=False)
    status = EnumField(enum=UserStatus, required=False, read_only=True)
    email = EmailField(required=False, validators=[UniqueValidator(
        queryset=User.objects.all(), message="Someone's already using that e-mail")])
    phone_number = PhoneField(required=False, validators=[
        UniqueValidator(queryset=User.objects.all(), message="Someone's already using that phone number", lookup='iexact')
    ])
    title = EnumField(enum=UserTitle, required=False, allow_null=True, allow_blank=True)
    gender = EnumField(enum=Gender, required=False, allow_null=True, allow_blank=True)
    country_of_birth = EnumField(enum=Country, required=False, allow_null=True, allow_blank=True)
    passport_country_origin = EnumField(enum=Country, required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = User
        fields = ('url', 'role', 'status', 'username', 'first_name', 'last_name', 'middle_name', 'phone_number',
                  'phone_number_verified', 'email_verified', 'contact_info_once_verified', 'is_verified', 'is_superuser',
                  'birth_date', 'last_name', 'email', 'address', 'account', 'title', 'gender', 'country_of_birth',
                  'mother_maiden_name', 'passport_number', 'passport_date_expiry', 'passport_country_origin')


class BaseUserResendInviteSerializer(HyperlinkedModelSerializer):
    email = EmailField(required=True)

    class Meta:
        model = User
        fields = ('email',)


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
        if isinstance(owner_account, SubUserAccount):
            owner_account = owner_account.owner_account
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
        user.is_staff = True
        address = Address()
        address.save()
        user.address = address
        user.save()
        account = AdminUserAccount(user=user)
        account.save()
        permission = AdminUserPermission(account=account)
        permission.save()
        return user

    def to_representation(self, instance):
        """
        If owner is blocked or banned so subuser should have the same status
        """
        data = super().to_representation(instance)
        owner = instance.account.owner_account.user
        if owner.status in [UserStatus.blocked, UserStatus.banned]:
            data["status"] = owner.status
        return data


class UserStatusSerializer(HyperlinkedModelSerializer):
    status = EnumField(enum=UserStatus, required=True)

    def check_status(self, user):
        user.status = self.data['status']
        user.save()

        if user.status == UserStatus.banned or user.status == UserStatus.blocked:
            helpers.admin_sign_out({'username': user.email})

    class Meta:
        model = User
        fields = ('status',)


class UserSerializer(BaseUserSerializer):

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
