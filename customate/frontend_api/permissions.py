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
            if self.check_field_in_request_data(field, data):
                return self.validate_credentials(request)
        request.data.pop("credentials", None)

        return True


    @staticmethod
    def validate_credentials(request):

        serializer = CogrnitoAuthRetrieveSerializer(data=request.data.get('credentials'))
        if serializer.is_valid():
            valdated_data = serializer.validated_data
            if request.user.username != valdated_data.get('preferred_username'):
                raise ValidationError({'/credentials': 'wrong credentials'})

            valdated_data['custom_flow'] = True
            entity = serializer.retrieve(serializer.validated_data)
            request.data['credentials'] = {
                'id_token': entity.id_token,
                'access_token': entity.access_token,
                'refresh_token': entity.refresh_token
            }

            return True

        else:
            raise ValidationError({'/credentials': 'credentials required'})

    @staticmethod
    def check_field_in_request_data(field, data):
        item = data
        for key in field.split('.'):
            item = item.get(key)
            if not item:
                return False
        return True


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