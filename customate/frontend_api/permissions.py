# -*- coding: utf-8 -*-

from uuid import UUID
from typing import Callable
import logging
import traceback

from rest_framework import permissions
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from authentication.cognito.serializers import CognitoAuthRetrieveSerializer
from core.fields import UserRole, UserStatus

from frontend_api.models.document import Document, get_relation_class

logger = logging.getLogger(__name__)


class CheckFieldsCredentials(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method == 'PATCH':
            if self.check_credentials_required_fields_exists(view):
                return self.check_credentials_required(request, view)
        request.data.pop("credentials", None)
        return True

    @staticmethod
    def check_credentials_required_fields_exists(view):
        print(getattr(view, 'credentials_required_fields'))
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
                    and (skip_validate_credentials_func is None or (
                    callable(skip_validate_credentials_func) and not skip_validate_credentials_func(request))):
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
            except ValidationError as ex:
                raise ex
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
        return request.user.role == UserRole.owner


class HasParticularDocumentPermission(permissions.BasePermission):
    """
    Custom permission to allow documents handling
    """

    def has_post_permission(self, request) -> bool:
        """
        Check permissions for posting document to particular schedule
        """
        relation_id = request.query_params.get("relation_id")
        relation_name = request.query_params.get("relation_name")
        # The case where files handling happens on the 'create schedule or escrow' page.
        if not relation_id:
            return True
        relation_class = get_relation_class(relation_name)
        relation = get_object_or_404(relation_class, id=relation_id)
        user = request.user
        allowed = relation.allow_post_document(user)
        return allowed

    def has_get_permission(self, request) -> bool:
        """
        Check permissions for getting document from particular schedule
        """
        key = request.query_params.get("key")
        if not key:
            logger.error("The 'key' parameter has not been passed %r" % traceback.format_exc())
            raise ValidationError("The 'key' field is requred.")
        document = get_object_or_404(Document, key=key)
        user = request.user
        allowed = document.allow_get_document(user)
        return allowed

    def has_delete_permission(self, request) -> bool:
        """
        Check if user able to delete document
        """
        key = request.query_params.get("key")
        if not key:
            logger.error("The 'key' parameter has not been passed %r" % traceback.format_exc())
            raise ValidationError("The 'key' field is requred.")
        document = get_object_or_404(Document, key=key)
        user = request.user
        allowed = document.allow_delete_document(user)
        return allowed

    def has_permission(self, request, view) -> Callable:
        methods = {
            "get_s3_object": self.has_get_permission,
            "post_s3_object": self.has_post_permission,
        }
        if request.method == "DELETE":
            return self.has_delete_permission(request)
        method_name = request.query_params.get("method_name")
        try:
            return methods[method_name](request)
        except KeyError:
            logger.error("Got unrecognized method name %r" % traceback.format_exc())
            raise ValidationError("Unrecognized method: {}".format(method_name))


class SubUserLoadFundsPermission(permissions.BasePermission):
    """
    Custom permission to only allow subusers of an object to edit it.
    """

    def has_permission(self, request, view):
        if request.user.role == UserRole.sub_user:
            return getattr(request.user.account.permission, "load_funds")
        return False


class SubUserManageFundingSourcesPermission(permissions.BasePermission):
    """
    Custom permission to only allow subusers of an object to edit it.
    """

    def has_permission(self, request, view):
        if request.user.role == UserRole.sub_user:
            return getattr(request.user.account.permission, "manage_funding_sources")
        return False


class SubUserManageSchedulesPermission(permissions.BasePermission):
    """
    Custom permission to only allow subusers of an object to edit it.
    """

    def has_permission(self, request, view):
        if request.user.role == UserRole.sub_user:
            return getattr(request.user.account.permission, "manage_schedules")
        return False


class SubUserManagePayeesPermission(permissions.BasePermission):
    """
    Custom permission to only allow subusers of an object to edit it.
    """

    def has_permission(self, request, view):
        if request.user.role == UserRole.sub_user:
            return getattr(request.user.account.permission, "manage_payees")
        return False


class IsSuperAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow super admins.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_superuser


class IsRegularSubUserOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow super admins.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role == UserRole.sub_user


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


class IsActive(permissions.BasePermission):
    """
    Custom permission to restrict access for inactive users
    """

    def has_permission(self, request, view):
        if request.user.status in [UserStatus.inactive, UserStatus.banned, UserStatus.pending]:
            return False
        return True


class IsNotBlocked(permissions.BasePermission):
    """
    Custom permission to restrict access for blocked users
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.status != UserStatus.blocked


class IsVerified(permissions.BasePermission):
    """
    Custom permission to restrict access for unverified users
    Restricts outgoing transactions but allows GET OPTIONS HEAD methods
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_verified and request.user.contact_verified


class IsAccountVerified(permissions.BasePermission):
    """
    Custom permission to restrict access for users with unverified account or owner's account
    Restricts outgoing transactions but allows GET OPTIONS HEAD methods
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.account.is_verified \
               and (not request.user.is_subuser or request.user.is_owner_account_verified)


class HasParticularSchedulePermission(permissions.BasePermission):
    """
    Custom permission for verifying if current user is payer or is subuser of schedules owner.
        Appropriate rights of subuser verified by preceded 'SubUserManageSchedulesPermission'
        permission class.
    """

    def has_object_permission(self, request, view, obj):
        if request.method == "PATCH":
            return self.has_patch_permission(request, obj)
        return True

    def has_patch_permission(self, request, obj):
        return request.user.account.id in obj.origin_user.get_all_related_account_ids()

