from rest_framework import routers
from payment_api.views import SignUpProxy, PaymentAccountViewSet, WalletViewSet, FeeGroupViewSet
from customate.routers import router

router.register(r'test', SignUpProxy, basename='test')
router.register('payment_accounts', PaymentAccountViewSet, basename='payment_accounts')
router.register('fee_groups', FeeGroupViewSet, basename='fee_groups')
router.register('wallets', WalletViewSet, basename='wallets')
urlpatterns = router.urls
