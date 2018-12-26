from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import MethodNotAllowed
from rest_framework import response
from collections import Iterable
from frontend_api.models import Address, Account, Company, Shareholder, SubUserAccount, AdminUserAccount
from frontend_api.serializers import UserAddressSerializer, CompanyAddressSerializer, \
    AccountSerializer, CompanySerializer, ShareholderSerializer, AddressSerializer, \
    SubUserAccountSerializer, AdminUserAccountSerializer, \
    SubUserSerializer

from authentication.cognito.serializers import CognitoInviteUserSerializer
from rest_framework.exceptions import NotFound
from django.contrib.auth.models import Group
from core.models import User

from rest_framework_json_api import views
from frontend_api.serializers import UserSerializer
from core.fields import UserRole, UserStatus
from rest_framework import permissions
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


class RelationshipPostMixin(object):
    # serializer_class = RelativeResourceIdentifierObjectSerializer
    _related_serializers = {}

    def get_related_serializer(self, serializer_name):
        return self._related_serializers.get(serializer_name) if serializer_name in self._related_serializers else None

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


class UserViewSet(PatchRelatedMixin, views.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer

    permission_classes = (IsOwnerOrReadOnly,)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()


class UserRelationshipView(RelationshipPostMixin, RelationshipView):
    queryset = User.objects

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


class AccountRelationshipView(RelationshipPostMixin, RelationshipView):
    queryset = Account.objects

    # serializer_class = RelativeResourceIdentifierObjectSerializer

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

    # serializer_class = RelativeResourceIdentifierObjectSerializer

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

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user
        # serializer.request.user.address = serializer.save(user=self.request.user)
        if not user.account.company.address:
            user.account.company.address = serializer.save()
            user.account.company.save()
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


class AccountViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (IsOwnerOrReadOnly,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user

        if not user.account:
            user.account = serializer.save()
            user.save()

    @action(methods=['POST'], detail=True, name='Invite sub user')
    @transaction.atomic()
    def invite(self, request, pk):
        username = request.data.get('username').lower()
        data = {
            'username': username,
            'email': username,
            'role': UserRole.sub_user.value,
            'status': UserStatus.pending.value,
            'first_name': request.data.get('first_name', ''),
            'middle_name': request.data.get('middle_name', ''),
            'last_name': request.data.get('last_name', ''),
        }

        serializer = SubUserSerializer(data=data, context={'request': request})
        if serializer.is_valid(True):
            user = serializer.save()
            invitation = CognitoInviteUserSerializer.invite(data)
            user.cognito_id = invitation.id
            user.save()

            return response.Response(
                CognitoInviteUserSerializer(instance=invitation, context={'request': request}).data)


class AdminUserAccountViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = AdminUserAccount.objects.all()
    serializer_class = AdminUserAccountSerializer
    permission_classes = (IsOwnerOrReadOnly,)


class SubUserAccountViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = SubUserAccount.objects.all()
    serializer_class = SubUserAccountSerializer
    permission_classes = (IsOwnerOrReadOnly,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user

        if not user.account:
            user.account = serializer.save()
            user.save()


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


class ShareholderViewSet(PatchRelatedMixin, views.ModelViewSet):

    queryset = Shareholder.objects.all()
    serializer_class = ShareholderSerializer
    permission_classes = (IsOwnerOrReadOnly,)