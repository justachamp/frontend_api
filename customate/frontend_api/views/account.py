from django.db import transaction
from django.contrib.auth.models import AnonymousUser

from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
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

from frontend_api.permissions import IsOwnerOrReadOnly

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

    def post_company(self, request, *args, **kwargs):
        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        account = self.get_object()
        company = account.company

        if company:
            raise MethodNotAllowed('POST')

        serializer = related_serializer(data=request.data.get('attributes'), context={'request': request})
        serializer.is_valid(raise_exception=True)
        account.company = serializer.save()
        account.save()

        return serializer


class UserAccountRelationshipView(RelationshipView):
    queryset = UserAccount.objects


class AdminUserAccountRelationshipView(RelationshipView):
    queryset = AdminUserAccount.objects


class SubUserAccountRelationshipView(RelationshipView):
    queryset = SubUserAccount.objects


class AccountViewSet(RelationshipMixin, PatchRelatedMixin, views.ModelViewSet):

    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (IsOwnerOrReadOnly,)

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
        logger.error('perform create')
        user = self.request.user

        if not user.account:
            user.account = serializer.save()
            user.save()

    @action(methods=['POST'], detail=True, name='Invite sub user')
    @transaction.atomic
    def invite(self, request, pk):
        username = request.data.get('username').lower()
        data = {
            'username': username,
            'email': username,
            'role': UserRole.sub_user.value,
            'first_name': request.data.get('first_name', ''),
            'middle_name': request.data.get('middle_name', ''),
            'last_name': request.data.get('last_name', ''),
        }

        serializer = SubUserSerializer(data=data, context={'request': request})
        if serializer.is_valid(True):
            invitation = CognitoInviteUserSerializer.invite(data)
            user = serializer.save()
            user.cognito_id = invitation.id
            user.email_verified = True
            user.save()
            invitation.pk = user.id

            return response.Response(
                CognitoInviteUserSerializer(instance=invitation, context={'request': request}).data)

    @action(methods=['POST'], detail=True, name='Invite sub user')
    @transaction.atomic
    def resend_invite(self, request, pk):
        username = request.data.get('username').lower()
        data = {
            'username': username,
            'email': username,
            'role': UserRole.sub_user.value,
            'action': 'RESEND'
        }

        serializer = BaseUserResendInviteSerializer(data=data, context={'request': request})
        if serializer.is_valid(True):
            invitation = CognitoInviteUserSerializer.invite(data)

            return response.Response(
                CognitoInviteUserSerializer(instance=invitation, context={'request': request}).data
            )


class UserAccountViewSet(PatchRelatedMixin, RelationshipPostMixin, views.ModelViewSet):

    queryset = UserAccount.objects.all()
    serializer_class = UserAccountSerializer
    permission_classes = (AllowAny,)

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
        logger.error('perform create')
        user = self.request.user

        if not user.account:
            user.account = serializer.save()
            user.save()


class AdminUserAccountViewSet(PatchRelatedMixin, RelationshipPostMixin, views.ModelViewSet):

    queryset = AdminUserAccount.objects.all()
    serializer_class = AdminUserAccountSerializer
    permission_classes = (AllowAny,)

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
        logger.error('perform create')
        user = self.request.user

        if not user.account:
            user.account = serializer.save()
            user.save()

    def post_permission(self, request, *args, **kwargs):
        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        account = self.get_object()

        if account.permission:
            raise MethodNotAllowed('POST')
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


class SubUserAccountViewSet(PatchRelatedMixin, RelationshipPostMixin, views.ModelViewSet):

    queryset = SubUserAccount.objects.all()
    serializer_class = SubUserAccountSerializer
    permission_classes = (IsOwnerOrReadOnly,)

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
        logger.error('perform create')
        user = self.request.user

        if not user.account:
            user.account = serializer.save()
            user.save()

    def post_permission(self, request, *args, **kwargs):
        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        account = self.get_object()

        if account.permission:
            raise MethodNotAllowed('POST')
        data = request.data.get('attributes') or {}
        data['account'] = account
        data['account_id'] = account.id
        serializer = related_serializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        permission = SubUserPermission(**serializer.validated_data, account=account)
        permission.save()
        return serializer
