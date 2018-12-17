from django.shortcuts import render

# Create your views here.




from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.reverse import reverse
# from django.http import Http404
from collections import Iterable
from django.db.models.manager import Manager
from frontend_api.models import Address, Account, Company, Shareholder
from frontend_api.serializers import UserAddressSerializer, CompanyAddressSerializer, \
    AccountSerializer, CompanySerializer, ShareholderSerializer, AddressSerializer, \
    RelativeResourceIdentifierObjectSerializer

from rest_framework.exceptions import NotFound
from django.contrib.auth.models import Group
from core.models import User
from rest_framework import viewsets, generics
from rest_framework_json_api import views
from frontend_api.serializers import UserSerializer
from rest_framework import permissions
from frontend_api.permissions import IsOwnerOrReadOnly

from rest_framework import renderers

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


class UserViewSet(views.ModelViewSet, PatchRelatedMixin):
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


class UserRelationshipView(RelationshipView):
    queryset = User.objects

    _related_serializers = {
        'address': UserAddressSerializer
    }

    def get_related_serializer(self, serializer_name):
        return self._related_serializers.get(serializer_name) if serializer_name in self._related_serializers else None

    @transaction.atomic()
    def post(self, request, *args, **kwargs):
        related_serializer = self.get_related_serializer(kwargs.get('related_field'))
        user = self.get_object()
        if related_serializer:
            if user.address:
                raise MethodNotAllowed('POST')

            serializer = related_serializer(data=request.data.get('attributes'), context={'request': request})
            serializer.is_valid(raise_exception=True)
            user.address = serializer.save()
            user.save()
            return Response(serializer.data)
        else:
            return super().post(request, *args, **kwargs)

    # def post(self, request, *args, **kwargs):
    #     logger.error('create')


class AddressRelationshipView(RelationshipView):
    queryset = Address.objects



# class UserAddressRelationshipView(RelationshipView):
#     queryset = Address.objects
#
#
# class CompanyAddressRelationshipView(RelationshipView):
#     queryset = Address.objects


class AccountRelationshipView(RelationshipView):
    queryset = Account.objects

    # def post(self, request, *args, **kwargs):
    #     related_instance = self.get_related_instance()
    #     field_name = self.get_related_field_name()
    #     relations = {'company': Company}
    #     if not related_instance and field_name in relations.keys():
    #         related_model_class = relations.get(field_name)
    #
    #
    #         serializer = self.get_serializer(
    #             data=request.data, model_class=related_model_class, many=True
    #         )
    #         serializer.is_valid(raise_exception=True)
    #         if frozenset(serializer.validated_data) <= frozenset(related_instance_or_manager.all()):
    #             return Response(status=204)
    #         related_instance_or_manager.add(*serializer.validated_data)
    #     else:
    #         raise MethodNotAllowed('POST')
    #     result_serializer = self._instantiate_serializer(related_instance_or_manager)
    #     return Response(result_serializer.data)



class CompanyRelationshipView(RelationshipView):
    queryset = Company.objects

    serializer_class = RelativeResourceIdentifierObjectSerializer

    _related_serializers = {
        'address': CompanyAddressSerializer,
        'shareholders': ShareholderSerializer
    }

    def get_related_serializer(self, serializer_name):
        return self._related_serializers.get(serializer_name) if serializer_name in self._related_serializers else None

    def get_related_handler(self, releted_field):
        try:
            return getattr(self, f'post_{releted_field}')
        except AttributeError:
            raise NotFound

    def post_address(self, request, *args, **kwargs):
        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        user = self.get_object()
        company = user.account.company

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
        user = self.get_object()
        company = user.account.company
        company = model_to_dict(company)
        company['type'] = 'Company'
        data = [rec.get('attributes') for rec in request.data]
        data = []
        for rec in request.data:
            rec = rec.get('attributes')
            rec['company'] = company
            data.append(rec)

        serializer = related_serializer(data=data, context={'request': request}, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return serializer


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



class ShareholderRelationshipView(RelationshipView):
    queryset = Shareholder.objects

# class GroupViewSet(views.ModelViewSet):
#     """
#     API endpoint that allows groups to be viewed or edited.
#     """
#     queryset = Group.objects.all()
#     serializer_class = GroupSerializer


class UserAddressViewSet(views.ModelViewSet, PatchRelatedMixin):

    queryset = Address.objects.all()
    serializer_class = UserAddressSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user
        # serializer.request.user.address = serializer.save(user=self.request.user)
        if not user.address:
            user.address = serializer.save()
            user.save()


class AddressViewSet(views.ModelViewSet, PatchRelatedMixin):

    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = (permissions.IsAuthenticated,)

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

class CompanyAddressViewSet(views.ModelViewSet, PatchRelatedMixin):

    queryset = Address.objects.all()
    serializer_class = CompanyAddressSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user
        # serializer.request.user.address = serializer.save(user=self.request.user)
        if not user.account.company.address:
            user.account.company.address = serializer.save()
            user.account.company.save()

    # def get_queryset(self):
    #     queryset = super(CompanyAddressViewSet, self).get_queryset()
    #     if 'pk' in self.kwargs:
    #         pk = self.kwargs['pk']
    #         queryset.filter(address__pk=pk)
    #
    #     return queryset


class AccountViewSet(views.ModelViewSet, PatchRelatedMixin):

    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user

        if not user.account:
            user.account = serializer.save()
            user.save()


class CompanyViewSet(views.ModelViewSet, PatchRelatedMixin):

    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user

        if not user.account.company:
            user.account.company = serializer.save()
            user.account.save()


class ShareholderViewSet(views.ModelViewSet, PatchRelatedMixin):

    queryset = Shareholder.objects.all()
    serializer_class = ShareholderSerializer
    permission_classes = (permissions.IsAuthenticated,)