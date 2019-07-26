from rest_framework import permissions
from rest_framework.exceptions import ValidationError

from authentication.cognito.serializers import CognitoAuthRetrieveSerializer
from core.fields import UserRole

import logging
logger = logging.getLogger(__name__)


class CheckFieldsCredentials(permissions.BasePermission):

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method == 'PATCH':
            if self.check_credentials_required_fields_exists(view):
                return self.check_credentials_required(request, view)
        request.data.pop("credentials", None)
        return True

    def has_object_permission(self, request, view, obj):
        return True

    @staticmethod
    def check_credentials_required_fields_exists(view):
        if hasattr(view, 'credentials_required_fields'):
            return True
        else:
            return False

    def check_credentials_required(self, request, view):
        data = request.data

        # view.credentials_required_fields = {
        #     'key': None - to avoid conditional check
        #     'key': func - to add conditional check before calling validate_credentials
        # }

        for field, skip_validate_credentials_func in view.credentials_required_fields.items():
            if self.check_field_in_request_data(request, field, data) \
                    and (skip_validate_credentials_func is None or (callable(skip_validate_credentials_func) and not skip_validate_credentials_func(request))):
                return self.validate_credentials(request)
        request.data.pop("credentials", None)

        return True


    @staticmethod
    def validate_credentials(request):
        serializer = CognitoAuthRetrieveSerializer(data=request.data.get('credentials'), context={'request': request})
        if serializer.is_valid():
            valdated_data = serializer.validated_data
            if request.user.username != valdated_data.get('preferred_username'):
                raise ValidationError({'credentials': [{'password': 'wrong credentials'}]})
            try:
                return serializer.check_password(serializer.validated_data)
            except Exception as ex:
                raise ValidationError({'credentials': [{'password': ex}]})

        else:
            raise ValidationError({'credentials': ['credentials required']})

    def check_field_in_request_data(self, request, field, data):
        item = data
        entity = self._get_entity(request)
        for key in field.split('.'):
            entity = self._get_entity_by_key(entity, key)
            item = item.get(key)
            if not item or not entity or entity == item:
                return False
        return True

    @staticmethod
    def _get_entity(request):
        # TODO as we need only email and phone_number we may get data directly from user but
        #  as future improvement we should add service for getting profile from request

        return request

    @staticmethod
    def _get_entity_by_key(entity, key):
        return getattr(entity, key) if hasattr(entity, key) else None




class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_anonymous:
            return False 
        return request.user.role == UserRole.owner


class SubUserLoadFundsPermission(permissions.BasePermission):
    """
    Custom permission to only allow subusers of an object to edit it.
    """
    def has_permission(self, request, view):
        return getattr(request.user.account.permission, "load_funds")


class SubUserManageFundingSourcesPermission(permissions.BasePermission):
    """
    Custom permission to only allow subusers of an object to edit it.
    """
    def has_permission(self, request, view):
        return getattr(request.user.account.permission, "manage_funding_sources")


class SubUserManageSchedulesPermission(permissions.BasePermission):
    """
    Custom permission to only allow subusers of an object to edit it.
    """
    def has_permission(self, request, view):
        return getattr(request.user.account.permission, "manage_schedules")


class SubUserManagePayeesPermission(permissions.BasePermission):
    """
    Custom permission to only allow subusers of an object to edit it.
    """
    def has_permission(self, request, view):
        return getattr(request.user.account.permission, "manage_payees")


class IsSuperAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow super admins.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_superuser 


class IsRegularAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow super admins.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff 


class AdminUserTaxPermission(permissions.BasePermission):
    """
    Custom permission to only allow arbitrary admins.
    """
    def has_permission(self, request, view):
        if request.user.is_staff:
            return getattr(request.user.account.permission, "manage_tax")


class AdminUserFeePermission(permissions.BasePermission):
    """
    Custom permission to only allow arbitrary admins.
    """
    def has_permission(self, request, view):
        if request.user.is_staff:
            return getattr(request.user.account.permission, "manage_fee")


class AllowAny(permissions.BasePermission):
    """
    Custom permission to only services users.
    """
    def has_permission(self, request, view):
        return not request.user.is_anonymous


# pull request