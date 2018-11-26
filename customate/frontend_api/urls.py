from rest_framework import routers
router = routers.DefaultRouter()

# urlpatterns = [
#     path('', views.index, name='index'),
# ]

from django.urls import include, path, re_path
from rest_framework.urlpatterns import format_suffix_patterns
from frontend_api import views






urlpatterns = [
    # path('', views.index, name='index'),
    # path('snippets/', views.SnippetList.as_view()),
    # path('snippets/<pk>/', views.SnippetDetail.as_view()),
    # path('snippets/<uuid:pk>/highlight/', views.SnippetHighlight.as_view()),
# path('snippets/<uuid:pk>/highlight/', views.SnippetHighlight.as_view(),  name='snippet-highlight'),
re_path(r'^users/(?P<pk>[^/.]+)/$',
        views.UserViewSet.as_view({'get': 'retrieve'}),
        name='user-detail'),
re_path(r'^users/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
        views.UserViewSet.as_view({'get': 'retrieve_related'}),
        name='user-related'),

re_path(r'^users/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
    view=views.UserRelationshipView.as_view(),
    name='user-relationships'
)
]


urlpatterns = format_suffix_patterns(urlpatterns)
