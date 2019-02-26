
from frontend_api import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register('users', views.UserViewSet)
router.register('admins', views.AdminUserViewSet, basename='admins')
router.register('user_accounts', views.UserAccountViewSet)
router.register('admin_user_accounts', views.AdminUserAccountViewSet)
router.register('admin_user_permission', views.AdminUserPermissionViewSet)
router.register('sub_user_accounts', views.SubUserAccountViewSet)
router.register('sub_user_permission', views.SubUserPermissionViewSet)
router.register('company', views.CompanyViewSet)
router.register('shareholders', views.ShareholderViewSet)
router.register('addresses', views.AddressViewSet)
router.register('accounts', views.AccountViewSet)
router.register('dataset', views.DatasetView, base_name='dataset')
# router.register('profiles', views.ProfileView.as_view())


urlpatterns = router.urls
