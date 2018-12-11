
from frontend_api import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register('users', views.UserViewSet)
router.register('company', views.CompanyViewSet)
# router.register('groups', views.GroupViewSet)
router.register('addresses', views.AddressViewSet)
router.register('accounts', views.AccountViewSet)


urlpatterns = router.urls
