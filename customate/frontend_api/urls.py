


# urlpatterns = [
#     path('', views.index, name='index'),
# ]

from django.urls import include, path, re_path
from rest_framework.urlpatterns import format_suffix_patterns
from frontend_api import views
from frontend_api.router import urlpatterns as model_url
from django.conf.urls import url





urlpatterns = [
    url(r'^', include(model_url)),
    re_path(r'^users/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            views.UserViewSet.as_view({'get': 'retrieve_related', 'patch': 'partial_update'}),
            name='user-related'),

    re_path(r'^users/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
        view=views.UserRelationshipView.as_view(),
        name='user-relationships'
    ),

    re_path(r'^address/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            views.AddressViewSet.as_view({'get': 'retrieve_related'}),
            name='address-related'),

    re_path(r'^address/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=views.AddressRelationshipView.as_view(),
            name='address-relationships'
            )
]


# urlpatterns = format_suffix_patterns(urlpatterns)
