from rest_framework import routers
from payment_api.views import SignUpProxy, PaymentAccountViewSet, WalletViewSet
router = routers.DefaultRouter()
router.register(r'test', SignUpProxy, basename='test')
router.register('payment-accounts', PaymentAccountViewSet, basename='payment-accounts')
router.register('wallets', WalletViewSet, basename='wallets')
urlpatterns = router.urls