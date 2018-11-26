"""customate URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path, re_path
# from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# urlpatterns = [
#     path('api/', include('frontend_api.urls')),
#     path('admin/', admin.site.urls),
# ]

# urlpatterns += staticfiles_urlpatterns()

from rest_framework import routers
from frontend_api import views

router = routers.DefaultRouter()
router.register('users', views.UserViewSet)
router.register('groups', views.GroupViewSet)
router.register('address', views.AddressViewSet)
# router.register('snippet-highlight', views.SnippetHighlight)
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse


from  botocore import regions
# @api_view(['GET'])
# def api_root(request, format=None):
#     return Response({
#         'users': reverse('user-list', request=request, format=format),
#         'snippets': reverse('snippet-list', request=request, format=format),
#     })

#
# for url in router.urls:
#     print('url --- ', url.__dict__)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('admin/', admin.site.urls),
    path(r'', include('frontend_api.urls')),
    path(r'', include('authentication.urls')),
    path(r'', include(router.urls)),
    # path('snippets/<uuid:pk>/highlight/', views.SnippetHighlight.as_view()),
    path(r'api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
