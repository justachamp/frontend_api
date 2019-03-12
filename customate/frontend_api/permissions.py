from rest_framework import permissions
from rest_framework.exceptions import ValidationError

from authentication.cognito.serializers import CogrnitoAuthRetrieveSerializer

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
        for field in view.credentials_required_fields:
            if self.check_field_in_request_data(request, field, data):
                return self.validate_credentials(request)
        request.data.pop("credentials", None)

        return True


    @staticmethod
    def validate_credentials(request):
        serializer = CogrnitoAuthRetrieveSerializer(data=request.data.get('credentials'), context={'request': request})
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

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        logger.error('IsOwnerOrReadOnly')
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        # raise Exception(f'obj {obj}')

        return True #obj.owner == request.user


class UserPermission(permissions.BasePermission):


    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        logger.error('IsOwnerOrReadOnly')
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        # raise Exception(f'obj {obj}')


        return True #obj.owner == request.user

    # account = models.OneToOneField(SubUserAccount, on_delete=models.CASCADE, related_name="permission")
    #
    #
    # # manage_sub_user
    # # view, create, update, delete
    # manage_funding_sources = models.BooleanField(_('manage funding sources'), default=False)
    # # view, create, update, delete
    #
    # manage_unload_accounts = models.BooleanField(_('manage unload accounts'), default=False)
    # # view, create, update, delete
    #
    #
    # create_transaction = models.BooleanField(_('create transaction'), default=False)
    #
    #
    # create_contract = models.BooleanField(_('create contract'), default=False)
    #
    # load_funds = models.BooleanField(_('create transaction'), default=False)
    # unload_funds = models.BooleanField(_('create transaction'), default=False)


class AccountUserPermission(UserPermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        logger.error('IsOwnerOrReadOnly')
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        # raise Exception(f'obj {obj}')

        return True  # obj.owner == request.user


class SubUserPermission(UserPermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        logger.error('IsOwnerOrReadOnly')
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        # raise Exception(f'obj {obj}')

        return True  # obj.owner == request.user



class AdminUserPermission(UserPermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        logger.error('IsOwnerOrReadOnly')
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        # raise Exception(f'obj {obj}')

        return True  # obj.owner == request.user