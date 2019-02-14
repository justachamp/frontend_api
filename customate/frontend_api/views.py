from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import MethodNotAllowed
from rest_framework import response
from collections import Iterable
from frontend_api.models import Address, Account, Company, Shareholder, SubUserAccount, AdminUserAccount, \
    SubUserPermission, AdminUserPermission, UserAccount
from frontend_api.serializers import UserAddressSerializer, CompanyAddressSerializer, \
    AccountSerializer, CompanySerializer, ShareholderSerializer, AddressSerializer, \
    SubUserAccountSerializer, AdminUserAccountSerializer, SubUserSerializer, SubUserPermissionSerializer, \
    AdminUserSerializer, AdminUserPermissionSerializer, UserAccountSerializer

from address.loqate.serializers import RetrieveAddressSerializer, SearchAddressSerializer
from authentication.cognito.serializers import CognitoInviteUserSerializer
from rest_framework.exceptions import NotFound
from django.contrib.auth.models import Group, AnonymousUser
from core.models import User

from core import views
from core.serializers import BulkExtensionMixin
from frontend_api.serializers import UserSerializer
from core.fields import UserRole, UserStatus
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated
from frontend_api.permissions import IsOwnerOrReadOnly

from rest_framework_json_api.views import RelationshipView
from django.db import transaction
from django.forms.models import model_to_dict

import logging
logger = logging.getLogger(__name__)


class PatchRelatedMixin(object):
    def patch_related(self, request, *args, **kwargs):
        serializer_kwargs = {}
        instance = self.get_related_instance()

        if hasattr(instance, 'all'):
            instance = instance.all()

        if callable(instance):
            instance = instance()

        if instance is None:
            return Response(data=None)

        if isinstance(instance, Iterable):
            serializer_kwargs['many'] = True
        serializer_kwargs['data'] = request.data

        serializer = self.get_serializer(instance, **serializer_kwargs)
        serializer.is_valid(True)
        serializer.save()
        return Response(serializer.data)


class RelationshipMixin(object):
    _related_serializers = {}

    def get_related_serializer(self, serializer_name):
        return self._related_serializers.get(serializer_name) if serializer_name in self._related_serializers else None


class RelationshipPostMixin(RelationshipMixin):
    # serializer_class = RelativeResourceIdentifierObjectSerializer


    def get_related_handler(self, releted_field):
        try:
            return getattr(self, f'post_{releted_field}')
        except AttributeError:
            raise NotFound

    @transaction.atomic()
    def post(self, request, *args, **kwargs):
        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        if related_serializer:
            handler = self.get_related_handler(related_field)
            serializer = handler(request, *args, **kwargs)

            return Response(serializer.data)
        else:
            raise MethodNotAllowed('POST')


class AdminUserViewSet(PatchRelatedMixin, views.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().filter(role=UserRole.admin).order_by('-date_joined')
    serializer_class = AdminUserSerializer

    permission_classes = (IsOwnerOrReadOnly,)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()

    def get_serializer_class(self):

        field = self.kwargs.get('related_field')

        if field == 'account':
            user = self.request.user
            pk = self.kwargs.get('pk')

            try:
                user = User.objects.get(id=pk)
            except Exception as e:
                raise NotFound(f'Account not found {pk}')

            if user.is_owner:
                return UserAccountSerializer
            elif user.is_subuser:
                return SubUserAccountSerializer
            elif user.is_admin:
                return AdminUserAccountSerializer

        else:
            return super().get_serializer_class()


class UserViewSet(PatchRelatedMixin, views.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = User.objects.all().exclude(email='AnonymousUser').order_by('-date_joined')
    serializer_class = UserSerializer

    permission_classes = (IsOwnerOrReadOnly,)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()

    def get_serializer_class(self):

        field = self.kwargs.get('related_field')
        user = self.request.user
        id = self.kwargs.get('pk')
        if id:
            try:
                user = User.objects.get(id=id)
            except Exception as e:
                raise NotFound(f'Account not found {id}')

            if field:
                if field == 'account':
                    if user.is_owner:
                        return UserAccountSerializer
                    elif user.is_subuser:
                        return SubUserAccountSerializer
                    elif user.is_admin:
                        return AdminUserAccountSerializer
                else:
                    return super().get_serializer_class()
            else:
                if user.is_owner:
                    return UserSerializer
                elif user.is_subuser:
                    return SubUserSerializer
                elif user.is_admin:
                    return AdminUserSerializer
                else:
                    return super().get_serializer_class()
        else:
            return super().get_serializer_class()


class UserRelationshipView(RelationshipPostMixin, RelationshipView):
    queryset = User.objects
    permission_classes = (AllowAny,)
    _related_serializers = {
        'address': UserAddressSerializer
    }

    def post_address(self, request, *args, **kwargs):
        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        user = self.get_object()

        if user.address:
                raise MethodNotAllowed('POST')

        serializer = related_serializer(data=request.data.get('attributes'), context={'request': request})
        serializer.is_valid(raise_exception=True)
        user.address = serializer.save()
        user.save()

        return serializer


class AddressRelationshipView(RelationshipView):
    queryset = Address.objects


class AdminUserAccountRelationshipView(RelationshipView):
    queryset = AdminUserAccount.objects


class SubUserAccountRelationshipView(RelationshipView):
    queryset = SubUserAccount.objects


class SubUserPermissionRelationshipView(RelationshipView):
    queryset = SubUserPermission.objects


class AdminUserPermissionRelationshipView(RelationshipView):
    queryset = AdminUserPermission.objects


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


class CompanyRelationshipView(RelationshipPostMixin, RelationshipView):
    queryset = Company.objects
    permission_classes = (AllowAny,)
    _related_serializers = {
        'address': CompanyAddressSerializer,
        'shareholders': ShareholderSerializer
    }

    def post_address(self, request, *args, **kwargs):
        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        company = self.get_object()

        if company.address:
            raise MethodNotAllowed('POST')

        serializer = related_serializer(data=request.data.get('attributes'), context={'request': request})
        serializer.is_valid(raise_exception=True)
        company.address = serializer.save()
        company.save()

        return serializer

    def post_shareholders(self, request, *args, **kwargs):
        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        company = self.get_object()
        company = model_to_dict(company)
        company['type'] = 'Company'
        data = []
        for rec in request.data:
            rec = rec.get('attributes')
            rec['company'] = company
            data.append(rec)

        serializer = related_serializer(data=data, context={'request': request}, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return serializer


class ShareholderRelationshipView(RelationshipView):
    queryset = Shareholder.objects

# class GroupViewSet(views.ModelViewSet):
#     """
#     API endpoint that allows groups to be viewed or edited.
#     """
#     queryset = Group.objects.all()
#     serializer_class = GroupSerializer


class UserAddressViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = Address.objects.all()
    serializer_class = UserAddressSerializer
    permission_classes = (IsOwnerOrReadOnly,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user
        if not user.address:
            user.address = serializer.save()
            user.save()


class AddressViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = (IsOwnerOrReadOnly,)

    # def perform_create(self, serializer):
    #     logger.error('perform create')
    #     user = self.request.user
    #     # serializer.request.user.address = serializer.save(user=self.request.user)
    #     if not user.account.company.address:
    #         user.account.company.address = serializer.save()
    #         user.account.company.save()

    @action(methods=['POST'], detail=False, name='Search address')
    def search(self, request):
        data = request.data
        serializer = SearchAddressSerializer(data=data)
        if serializer.is_valid(True) and serializer.validated_data.get('Text'):
            return response.Response(serializer.find(serializer.validated_data))

        return response.Response([])

    @action(methods=['POST'], detail=False, name='Retrieve address detail')
    def search_detail(self, request):
        data = request.data
        id = data.get('id')
        serializer = RetrieveAddressSerializer(data={'Id': id})
        if serializer.is_valid(True):
            return response.Response(serializer.retrieve(id))
    #
    # def get_queryset(self):
    #     queryset = super(CompanyAddressViewSet, self).get_queryset()
    #     if 'company_pk' in self.kwargs:
    #         company_pk = self.kwargs['company_pk']
    #         queryset.filter(company__pk=company_pk)
    #
    #     return queryset


class CompanyAddressViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = Address.objects.all()
    serializer_class = CompanyAddressSerializer
    permission_classes = (IsOwnerOrReadOnly,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user
        if not user.account.company.address:
            user.account.company.address = serializer.save()
            user.account.company.save()


class AccountViewSet(RelationshipMixin, PatchRelatedMixin, views.ModelViewSet):

    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (IsOwnerOrReadOnly,)

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
            user = serializer.save()
            invitation = CognitoInviteUserSerializer.invite(data)
            user.cognito_id = invitation.id
            user.email_verified = True
            user.save()
            invitation.pk = user.id

            return response.Response(
                CognitoInviteUserSerializer(instance=invitation, context={'request': request}).data)


class AdminUserAccountViewSet(PatchRelatedMixin, RelationshipPostMixin, views.ModelViewSet):

    queryset = AdminUserAccount.objects.all()
    serializer_class = AdminUserAccountSerializer
    permission_classes = (AllowAny,)

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
        # account.permission = serializer.save()
        # account.save()

        return serializer


    @staticmethod
    def _initiate_admin(data):
        return User.objects.filter(role=UserRole.admin).count() == 0 and data.get('initiate', False)

    @action(methods=['POST'], detail=False, name='Invite admin')
    @transaction.atomic()
    def invite(self, request):
        user = request.user
        request_data = request.data
        if (type(user) is not AnonymousUser and user.is_admin) or self._initiate_admin(request_data):
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
            user = serializer.save()
            invitation = CognitoInviteUserSerializer.invite(data)
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


class SubUserPermissionViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = SubUserPermission.objects.all()
    serializer_class = SubUserPermissionSerializer
    permission_classes = (IsOwnerOrReadOnly,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user

        if not user.account.permission:
            user.account.permission = serializer.save()
            user.account.save()


class AdminUserPermissionViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = AdminUserPermission.objects.all()
    serializer_class = AdminUserPermissionSerializer
    permission_classes = (IsOwnerOrReadOnly,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user

        if not user.account.permission:
            user.account.permission = serializer.save()
            user.account.save()


class CompanyViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = (IsOwnerOrReadOnly,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user

        if not user.account.company:
            user.account.company = serializer.save()
            user.account.save()


class ShareholderViewSet(BulkExtensionMixin, PatchRelatedMixin, views.ModelViewSet):

    queryset = Shareholder.objects.all()
    serializer_class = ShareholderSerializer
    permission_classes = (AllowAny,)

    @transaction.atomic
    def perform_create(self, serializer):
        company = self.request.user.account.company
        company.shareholders.all().delete()
        company.shareholders.set(serializer.save())
        company.save()
