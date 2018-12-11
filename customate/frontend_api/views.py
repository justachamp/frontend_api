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
    AccountSerializer, CompanySerializer, ShareholderSerializer, AddressSerializer

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

import logging
logger = logging.getLogger(__name__)



class UserViewSet(views.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer

    permission_classes = (IsOwnerOrReadOnly,)

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

    _related_serializers = {
        'address': CompanyAddressSerializer
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
            related_instance_or_manager = self.get_related_instance()

            if isinstance(related_instance_or_manager, Manager):
                related_model_class = related_instance_or_manager.model
                serializer = self.get_serializer(
                    data=request.data, model_class=related_model_class, many=True
                )
                serializer.is_valid(raise_exception=True)
                if frozenset(serializer.validated_data) <= frozenset(related_instance_or_manager.all()):
                    return Response(status=204)
                related_instance_or_manager.add(*serializer.validated_data)
            else:
                raise MethodNotAllowed('POST')
            result_serializer = self._instantiate_serializer(related_instance_or_manager)
            return Response(result_serializer.data)

            # return super().post(request, *args, **kwargs)


class ShareholderRelationshipView(RelationshipView):
    queryset = Shareholder.objects


# class GroupViewSet(views.ModelViewSet):
#     """
#     API endpoint that allows groups to be viewed or edited.
#     """
#     queryset = Group.objects.all()
#     serializer_class = GroupSerializer


class UserAddressViewSet(views.ModelViewSet):

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

    # def perform_update(self, serializer):
    #     logger.error('perform гзвфеу')
    #     user = self.request.user
    #     # serializer.request.user.address = serializer.save(user=self.request.user)
    #     if user.address:
    #        pass
    #     user.address = serializer.save()
    #     user.save()

    # def update(self, request, *args, **kwargs):
    #     logger.error('update')
    #     user = self.request.user


    # def get_queryset(self):
    #     queryset = super(UserAddressViewSet, self).get_queryset()
    #
    #     # if this viewset is accessed via the 'order-lineitems-list' route,
    #     # it wll have been passed the `order_pk` kwarg and the queryset
    #     # needs to be filtered accordingly; if it was accessed via the
    #     # unnested '/lineitems' route, the queryset should include all LineItems
    #     if 'pk' in self.kwargs:
    #         pk = self.kwargs['pk']
    #         queryset.filter(user__pk=pk)
    #
    #     return queryset


class AddressViewSet(views.ModelViewSet):

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

class CompanyAddressViewSet(views.ModelViewSet):

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


class AccountViewSet(views.ModelViewSet):

    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user

        if not user.account:
            user.account = serializer.save()
            user.save()

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

    # def get_queryset(self):
    #     queryset = super(AccountViewSet, self).get_queryset()
    #
    #     # if this viewset is accessed via the 'order-lineitems-list' route,
    #     # it wll have been passed the `order_pk` kwarg and the queryset
    #     # needs to be filtered accordingly; if it was accessed via the
    #     # unnested '/lineitems' route, the queryset should include all LineItems
    #     if 'pk' in self.kwargs:
    #         pk = self.kwargs['pk']
    #         queryset.filter(account__pk=pk)
    #
    #     return queryset


class CompanyViewSet(views.ModelViewSet):

    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        logger.error('perform create')
        user = self.request.user

        if not user.account.company:
            user.account.company = serializer.save()
            user.account.save()

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


    # def get_queryset(self):
    #     queryset = super(CompanyViewSet, self).get_queryset()
    #
    #     # if this viewset is accessed via the 'order-lineitems-list' route,
    #     # it wll have been passed the `order_pk` kwarg and the queryset
    #     # needs to be filtered accordingly; if it was accessed via the
    #     # unnested '/lineitems' route, the queryset should include all LineItems
    #     if 'pk' in self.kwargs:
    #         pk = self.kwargs['pk']
    #         queryset.filter(company__pk=pk)
    #
    #     return queryset


class ShareholderViewSet(views.ModelViewSet):

    queryset = Shareholder.objects.all()
    serializer_class = ShareholderSerializer
    permission_classes = (permissions.IsAuthenticated,)

    # def get_queryset(self):
    #     queryset = super(ShareholderViewSet, self).get_queryset()
    #
    #     # if this viewset is accessed via the 'order-lineitems-list' route,
    #     # it wll have been passed the `order_pk` kwarg and the queryset
    #     # needs to be filtered accordingly; if it was accessed via the
    #     # unnested '/lineitems' route, the queryset should include all LineItems
    #     if 'pk' in self.kwargs:
    #         pk = self.kwargs['pk']
    #         queryset.filter(shareholder__pk=pk)
    #
    #     return queryset

    # def get_permissions(self):
    #     """
    #     Instantiates and returns the list of permissions that this view requires.
    #     """
    #     if self.action == 'list':
    #         permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    #     else:
    #         permission_classes = (permissions.IsAuthenticated,)
    #     return [permission() for permission in permission_classes]


# class SnippetHighlight(views.generics.GenericAPIView):
#     queryset = Snippet.objects.all()
#     renderer_classes = (renderers.StaticHTMLRenderer,)
#
#     def get(self, request, *args, **kwargs):
#         snippet = self.get_object()
#         return Response(snippet.highlighted)
#
#     @classmethod
#     def get_extra_actions(cls):
#         return []




# @api_view(['GET'])
# def api_root(request, format=None):
#     return Response({
#         'users': reverse('user-list', request=request, format=format),
#         'snippets': reverse('snippet-list', request=request, format=format)
#     })