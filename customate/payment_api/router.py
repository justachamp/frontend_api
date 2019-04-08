from rest_framework import routers
from payment_api.views import SignUpProxy, PaymentAccountViewSet, WalletViewSet
router = routers.DefaultRouter()
router.register(r'test', SignUpProxy, base_name='test')
router.register('payment-accounts', PaymentAccountViewSet, base_name='accounts')
router.register('wallets', WalletViewSet, base_name='wallets')
urlpatterns = router.urls