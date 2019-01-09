
from frontend_api import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register('users', views.UserViewSet)
router.register('sub_user_accounts', views.SubUserAccountViewSet)
router.register('sub_user_permission', views.SubUserPermissionViewSet)
router.register('company', views.CompanyViewSet)
# router.register('groups', views.GroupViewSet)
router.register('shareholders', views.ShareholderViewSet)
router.register('addresses', views.AddressViewSet)
router.register('accounts', views.AccountViewSet)
# router.register('useraccounts', views.AccountViewSet)


urlpatterns = router.urls
