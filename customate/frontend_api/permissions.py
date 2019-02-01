from rest_framework import permissions
import logging
logger = logging.getLogger(__name__)


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