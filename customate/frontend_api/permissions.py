# -*- coding: utf-8 -*-

from uuid import UUID
from typing import Callable
import logging
import traceback

from rest_framework import permissions
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from authentication.cognito.serializers import CognitoAuthRetrieveSerializer
from core.fields import UserRole, UserStatus

from frontend_api.models import Schedule, Document
from frontend_api.fields import ScheduleStatus

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
        schedule_id = request.query_params.get("schedule_id")
        # The case where files handling happens on the 'create schedule' page.
        if not schedule_id:
            return True

        schedule = get_object_or_404(Schedule, id=schedule_id)
        recipient = schedule.recipient_user
        user = request.user
        # Check if recipient or sender have common account with user from request (or user's subusers)
        related_account_ids = user.get_all_related_account_ids()

        # Check if schedule has status 'cancelled'
        #    need to avoid documents handling for such schedules
        if schedule.status == ScheduleStatus.cancelled:
            return False

        if user.role == UserRole.owner:
            return (recipient and recipient.account.id in related_account_ids) \
                   or schedule.origin_user.account.id in related_account_ids

        # Check if subuser from request is subuser of recipient or sender
        if user.role == UserRole.sub_user:
            return getattr(user.account.permission, "manage_schedules") and \
                   any([recipient == user.account.owner_account.user,
                        schedule.origin_user == user.account.owner_account.user,
                        schedule.origin_user == user])
        return False

    def has_get_permission(self, request) -> bool:
        """
        Check permissions for getting document from particular schedule
        """
        document_id = request.query_params.get("document_id")
        if not document_id:
            logger.error("The 'document_id' parameter has not been passed %r" % traceback.format_exc())
            raise ValidationError("The 'document_id' field is requred.")
        document = get_object_or_404(Document, id=document_id)
        schedule = document.schedule
        # The case where files handling happens on the 'create schedule' page.
        if not schedule and document.user == request.user:
            return True
        recipient = schedule.recipient_user
        user = request.user
        # Check if user from request is recipient or sender
        if user.role == UserRole.owner:
            return any([recipient == user, schedule.origin_user == user])
        # Check if subuser from request is subuser of recipient or sender
        if user.role == UserRole.sub_user:
            return getattr(user.account.permission, "manage_schedules") and \
                   any([recipient == user.account.owner_account.user,
                        schedule.origin_user == user.account.owner_account.user,
                        schedule.origin_user == user])

    def has_delete_permission(self, request) -> bool:
        """
        Check if user able to delete document
        """
        document_id = request.query_params.get("document_id")
        if not document_id:
            logger.error("The 'document_id' parameter has not been passed %r" % traceback.format_exc())
            raise ValidationError("The 'document_id' field is requred.")
        document = get_object_or_404(Document, id=document_id)
        if not document.schedule and document.user == request.user:
            return True
        user = request.user
        # Check if schedule has status 'cancelled'
        #    need to avoid documents handling for such schedules
        schedule = document.schedule
        if schedule:
            if schedule.status == ScheduleStatus.cancelled:
                return False
        schedule_creator_account = document.schedule.origin_user.account.owner_account if \
            hasattr(document.schedule.origin_user.account, "owner_account") else \
            document.schedule.origin_user.account
        # If document has created by subuser and owner wants to remove it.
        if all([document.user.role == UserRole.sub_user,
                user.role == UserRole.owner]):
            # Check if schedule belongs to user from request
            return all([schedule_creator_account == user.account,
                        # And check if subuser is subuser of user from request
                        user.account.sub_user_accounts.filter(user=document.user)])
        return user == document.user

    def has_permission(self, request, view) -> Callable:
        methods = {
            "get_s3_object": self.has_get_permission,
            "post_s3_object": self.has_post_permission,
            "delete_s3_object": self.has_delete_permission
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


class IsBlockedUsersUpdateContactInfoRequest(permissions.BasePermission):
    """
    Custom permission to allow access for contact information's update for blocked user
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.method == 'PATCH' and request.user.status == UserStatus.blocked \
               and self._is_contact_info_updated_only(request)

    def _is_contact_info_updated_only(self, request):
        user_data = request.data.get('user', {})
        return len(user_data) == 1 and ('email' in user_data or 'phone_number' in user_data)


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
