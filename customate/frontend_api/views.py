from django.shortcuts import render

# Create your views here.




from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
# from django.http import Http404

from frontend_api.models import Address
from frontend_api.serializers import AddressSerializer

from django.contrib.auth.models import Group
from core.models import User
from rest_framework import viewsets, generics
from rest_framework_json_api import views
from frontend_api.serializers import UserSerializer, GroupSerializer
from rest_framework import permissions
from frontend_api.permissions import IsOwnerOrReadOnly

from rest_framework import renderers

from rest_framework_json_api.views import RelationshipView





class UserViewSet(views.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer

    permission_classes = (IsOwnerOrReadOnly,)

    # def get_permissions(self):
    #     """
    #     Instantiates and returns the list of permissions that this view requires.
    #     """
    #     if self.action == 'list':
    #         permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    #     else:
    #         permission_classes = (permissions.IsAuthenticated,)
    #     return [permission() for permission in permission_classes]


class UserRelationshipView(RelationshipView):
    queryset = User.objects

class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class AddressViewSet(views.ModelViewSet):

    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        queryset = super(AddressViewSet, self).get_queryset()

        # if this viewset is accessed via the 'order-lineitems-list' route,
        # it wll have been passed the `order_pk` kwarg and the queryset
        # needs to be filtered accordingly; if it was accessed via the
        # unnested '/lineitems' route, the queryset should include all LineItems
        if 'user_pk' in self.kwargs:
            user_pk = self.kwargs['user_pk']
            queryset.filter(user__pk=user_pk)

        return queryset

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