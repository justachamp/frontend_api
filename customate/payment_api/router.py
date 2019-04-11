from rest_framework import routers
from payment_api.views import SignUpProxy, PaymentAccountViewSet, WalletViewSet, FeeGroupViewSet
router = routers.DefaultRouter()

router.register(r'test', SignUpProxy, basename='test')
router.register('payment-accounts', PaymentAccountViewSet, basename='payment-accounts')
router.register('fee-groups', FeeGroupViewSet, basename='fee-groups')
router.register('wallets', WalletViewSet, basename='wallets')
urlpatterns = router.urls