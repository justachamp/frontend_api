from django.db import transaction
from django.contrib.auth.models import AnonymousUser

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.exceptions import MethodNotAllowed, NotFound
from rest_framework import response
from rest_framework_json_api.views import RelationshipView

from authentication.cognito.serializers import CognitoInviteUserSerializer
from core.fields import UserRole
from core import views
from core.models import User

from frontend_api.models import (
    Account,
    UserAccount,
    SubUserAccount,
    AdminUserAccount,
    SubUserPermission,
    AdminUserPermission
)
from frontend_api.serializers import (
    AccountSerializer,
    CompanySerializer,
    SubUserAccountSerializer,
    BaseUserResendInviteSerializer,
    AdminUserAccountSerializer,
    SubUserSerializer,
    SubUserPermissionSerializer,
    AdminUserSerializer,
    AdminUserPermissionSerializer,
    UserAccountSerializer,
    UserSerializer
)

from frontend_api.permissions import ( 
    IsOwnerOrReadOnly, 
    IsSuperAdminOrReadOnly,
    IsRegularAdminOrReadOnly,
    IsRegularSubUserOrReadOnly,
    IsActive,
    IsNotBlocked )

from ..views import (
    PatchRelatedMixin,
    RelationshipMixin,
    RelationshipPostMixin
)

from rest_framework_json_api import filters
from rest_framework_json_api import django_filters
from rest_framework.filters import SearchFilter


import logging
logger = logging.getLogger(__name__)


class AccountRelationshipView(RelationshipPostMixin, RelationshipView):
    queryset = Account.objects

    serializer_class = AccountSerializer

    _related_serializers = {
        'company': CompanySerializer,
        'sub_user_accounts': SubUserAccount
    }
    permission_classes = (  IsAuthenticated, 
                            IsActive,
                            IsNotBlocked,
                            IsSuperAdminOrReadOnly |
                            IsOwnerOrReadOnly ) 

    def post_company(self, request, *args, **kwargs):
        logger.info("Handle account's company creation request")

        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        account = self.get_object()
        company = account.company

        if company:
            logger.info("Company already exists(account=%s), do nothing" % account.id)
            raise MethodNotAllowed('POST')

        serializer = related_serializer(data=request.data.get('attributes'), context={'request': request})
        serializer.is_valid(raise_exception=True)
        account.company = serializer.save()
        account.save()

        logger.info("Company (id=%s) was successfully created" % account.company.id)
        return serializer


class UserAccountRelationshipView(RelationshipView):
    queryset = UserAccount.objects
    serializer_class = UserAccountSerializer
    permission_classes = (  IsAuthenticated,
                            IsActive,
                            IsNotBlocked,
                            IsSuperAdminOrReadOnly |
                            IsOwnerOrReadOnly )


class AdminUserAccountRelationshipView(RelationshipView):
    queryset = AdminUserAccount.objects
    serializer_class = AdminUserAccountSerializer
    permission_classes = (  IsAuthenticated, 
                            IsActive,
                            IsNotBlocked,
                            IsSuperAdminOrReadOnly )


class SubUserAccountRelationshipView(RelationshipView):
    queryset = SubUserAccount.objects
    serializer_class = SubUserAccountSerializer
    permission_classes = (IsAuthenticated, 
                          IsActive,
                          IsNotBlocked,
                          IsSuperAdminOrReadOnly|
                          IsOwnerOrReadOnly )


class AccountViewSet(RelationshipMixin, PatchRelatedMixin, views.ModelViewSet):

    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (  IsAuthenticated, 
                            IsActive,
                            IsNotBlocked,
                            IsSuperAdminOrReadOnly |
                            IsOwnerOrReadOnly ) 

    filter_backends = (filters.QueryParameterValidationFilter, filters.OrderingFilter,
                       django_filters.DjangoFilterBackend, SearchFilter)
    filterset_fields = {
        'user__status': ('exact', 'in'),
        'user__email': ('icontains', 'contains', 'iexact', 'exact'),
        'user__username': ('icontains', 'contains', 'iexact', 'exact'),
    }
    search_fields = ('user__email', 'user__username',)

    _related_serializers = {
        'sub_user_accounts': SubUserAccountSerializer,
        'admin_user_accounts': AdminUserAccountSerializer,
        'company': CompanySerializer,
        'user': UserSerializer
    }

    def get_serializer_class(self):
        # user = self.request.user
        id = self.kwargs.get('pk')
        related_field = self.kwargs.get('related_field')
        if related_field:
            related_serializer = self.get_related_serializer(related_field)
            return related_serializer or super().get_serializer_class()

        elif id:
            try:
                account = Account.objects.get(id=id)
                user = account.user

                if user.is_owner:
                    return UserAccountSerializer
                elif user.is_subuser:
                    return SubUserAccountSerializer
                elif user.is_admin:
                    return AdminUserAccountSerializer

            except Exception as e:
                raise NotFound(f'Account not found {id}')
        else:
            return super().get_serializer_class()

    def perform_create(self, serializer):
        logger.info('Handle account creation')
        user = self.request.user

        if not user.account:
            user.account = serializer.save()
            user.save()

            logger.info("Account (id=%s) was successfully created" % user.account.id)

    @action(methods=['POST'], detail=True, name='Invite sub user')
    @transaction.atomic
    def invite(self, request, pk):
        logger.info("Handle sending invite request")

        username = request.data.get('username').lower()
        data = {
            'username': username,
            'email': username,
            'role': UserRole.sub_user.value,
            'first_name': request.data.get('first_name', ''),
            'middle_name': request.data.get('middle_name', ''),
            'last_name': request.data.get('last_name', ''),
        }

        logger.info("Invited sub-user's data: %s" % data)
        serializer = SubUserSerializer(data=data, context={'request': request})
        if serializer.is_valid(True):
            invitation = CognitoInviteUserSerializer.invite(data)
            user = serializer.save()
            user.cognito_id = invitation.id
            user.email_verified = True
            user.save()
            invitation.pk = user.id
            resp = CognitoInviteUserSerializer(instance=invitation, context={'request': request}).data
            return response.Response(resp)

    @action(methods=['POST'], detail=True, name='Invite sub user')
    @transaction.atomic
    def resend_invite(self, request, pk):
        logger.info("Handle re-sending invite request")

        username = request.data.get('username').lower()
        data = {
            'username': username,
            'email': username,
            'role': UserRole.sub_user.value,
            'action': 'RESEND'
        }

        logger.info("Invite data: %s" % data)
        serializer = BaseUserResendInviteSerializer(data=data, context={'request': request})
        if serializer.is_valid(True):
            invitation = CognitoInviteUserSerializer.invite(data)

            return response.Response(
                CognitoInviteUserSerializer(instance=invitation, context={'request': request}).data
            )


class UserAccountViewSet(PatchRelatedMixin, RelationshipPostMixin, views.ModelViewSet):

    queryset = UserAccount.objects.all()
    serializer_class = UserAccountSerializer
    permission_classes = (  IsAuthenticated,
                            IsActive,
                            IsNotBlocked,
                            IsSuperAdminOrReadOnly|
                            IsOwnerOrReadOnly )

    ordering_fields = ('user__email', 'user__username', 'user__status', 'user__first_name',
                       'user__last_name', 'user_middle_name', 'user__phone_number',
                       'user__title', 'user__gender', )

    filter_backends = (filters.QueryParameterValidationFilter, filters.OrderingFilter,
                      django_filters.DjangoFilterBackend, SearchFilter)

    filterset_fields = {
        'user__status': ('exact', 'in'),
        'user__email': ('icontains', 'contains', 'iexact', 'exact'),
        'user__username': ('icontains', 'contains', 'iexact', 'exact'),
    }
    search_fields = ('user__email', 'user__status', 'user__username',)

    def perform_create(self, serializer):
        logger.info("Handle user's account creation request")
        user = self.request.user

        if not user.account:
            user.account = serializer.save()
            user.save()


class AdminUserAccountViewSet(PatchRelatedMixin, RelationshipPostMixin, views.ModelViewSet):

    queryset = AdminUserAccount.objects.all()
    serializer_class = AdminUserAccountSerializer
    permission_classes = (  IsAuthenticated, 
                            IsActive,
                            IsNotBlocked,
                            IsSuperAdminOrReadOnly )

    ordering_fields = ('user__email', 'user__username', 'user__status', 'user__first_name',
                       'user__last_name', 'user_middle_name', 'user__phone_number',
                       'user__title', 'user__gender',)

    filter_backends = (filters.QueryParameterValidationFilter, filters.OrderingFilter,
                      django_filters.DjangoFilterBackend, SearchFilter)
    filterset_fields = {
        'user__status': ('exact', 'in'),
        'user__email': ('icontains', 'contains', 'iexact', 'exact'),
        'user__username': ('icontains', 'contains', 'iexact', 'exact'),
    }
    search_fields = ('user__email', 'user__status', 'user__username',)

    _related_serializers = {
        'permission': AdminUserPermissionSerializer
    }

    def perform_create(self, serializer):
        logger.info("Handle admin user's account creation request")
        user = self.request.user

        if not user.account:
            user.account = serializer.save()
            user.save()

    def post_permission(self, request, *args, **kwargs):
        logger.info("Handle admin's account permissions creation request")

        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        account = self.get_object()

        logger.info("Permissions for account: %s" % account.id)
        data = request.data.get('attributes') or {}
        data['account'] = account
        data['account_id'] = account.id
        serializer = related_serializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        permission = AdminUserPermission(**serializer.validated_data, account=account)
        permission.save()

        return serializer

    @action(methods=['POST'], detail=False, name='Invite admin')
    @transaction.atomic()
    def invite(self, request):
        logger.info("Handle sending admin's invite request")

        user = request.user
        request_data = request.data
        if type(user) is AnonymousUser or not user.is_admin:
            raise MethodNotAllowed('invite')

        username = request_data.get('username').lower()
        data = {
            'username': username,
            'email': username,
            'role': UserRole.admin.value,
            'first_name': request_data.get('first_name', ''),
            'middle_name': request_data.get('middle_name', ''),
            'last_name': request_data.get('last_name', ''),
        }

        logger.info("Invited user's data: %s" % data)
        serializer = AdminUserSerializer(data=data, context={'request': request})
        if serializer.is_valid(True):
            invitation = CognitoInviteUserSerializer.invite(data)
            user = serializer.save()
            user.cognito_id = invitation.id
            user.email_verified = True
            user.save()
            invitation.pk = user.id

            return response.Response(
                CognitoInviteUserSerializer(instance=invitation, context={'request': request}).data)

    @action(methods=['POST'], detail=True, name='Invite admin')
    @transaction.atomic
    def resend_invite(self, request, pk):
        logger.info("Handle re-sending admin invite request")

        username = request.data.get('username').lower()
        data = {
            'username': username,
            'email': username,
            'role': UserRole.admin.value,
            'action': 'RESEND'
        }

        logger.info("Invite data: %s" % data)
        serializer = BaseUserResendInviteSerializer(data=data, context={'request': request})
        if serializer.is_valid(True):
            invitation = CognitoInviteUserSerializer.invite(data)

            return response.Response(
                CognitoInviteUserSerializer(instance=invitation, context={'request': request}).data
            )


class SubUserAccountViewSet(PatchRelatedMixin, RelationshipPostMixin, views.ModelViewSet):

    queryset = SubUserAccount.objects.all()
    serializer_class = SubUserAccountSerializer
    permission_classes = (IsAuthenticated, 
                          IsActive,
                          IsNotBlocked,
                          IsSuperAdminOrReadOnly|
                          IsOwnerOrReadOnly )

    # TODO move to service
    def get_owner_account(self):
        user = self.request.user
        account = None
        if type(user) is not AnonymousUser:
            return user.account if not user.is_subuser else user.account.owner_account
        return account

    # TODO move to service
    def get_owner_id(self):
        owner_account = self.get_owner_account()
        return owner_account.user.id if owner_account else None
    
    def get_queryset(self, *args, **kwargs):
        if self.action == 'list':
            return self.queryset.filter(owner_account__user__id=self.get_owner_id())
        else:
            return super().get_queryset(*args, **kwargs)

    ordering_fields = ('user__email', 'user__username', 'user__status', 'user__first_name',
                       'user__last_name', 'user_middle_name', 'user__phone_number', 'user__title',
                       'user__gender', )

    filter_backends = (filters.QueryParameterValidationFilter, filters.OrderingFilter,
                       django_filters.DjangoFilterBackend, SearchFilter)
    filterset_fields = {
        'user__status': ('exact', 'in'),
        'user__email': ('icontains', 'contains', 'iexact', 'exact'),
        'user__username': ('icontains', 'contains', 'iexact', 'exact'),
    }
    search_fields = (
        'user__email', 'user__status', 'user__username',
    )

    _related_serializers = {
        'permission': SubUserPermissionSerializer
    }

    def perform_create(self, serializer):
        logger.info("Handle sub-user's account creation request")
        user = self.request.user

        if not user.account:
            user.account = serializer.save()
            user.save()

    def post_permission(self, request, *args, **kwargs):
        logger.info("Handle sub-user's account permissions creation request")

        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        account = self.get_object()

        logger.info("Permissions for account: %s" % account.id)
        data = request.data.get('attributes') or {}
        data['account'] = account
        data['account_id'] = account.id
        serializer = related_serializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        permission = SubUserPermission(**serializer.validated_data, account=account)
        permission.save()
        return serializer
