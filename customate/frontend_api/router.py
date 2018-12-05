from .api.base.router import api_urlpatterns as api_v1

urlpatterns = [
    url(r'^api/v1/', include(api_v1)),
]