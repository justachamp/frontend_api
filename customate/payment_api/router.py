from rest_framework import routers
from payment_api.views import (
    SignUpProxy,
    PaymentAccountViewSet,
    WalletViewSet,
    FeeGroupViewSet,
    TaxViewSet,
    TransactionViewSet,
    PaymentViewSet,
    FundingSourceViewSet
)
from customate.routers import router

# from rest_framework import routers

# router = routers.DefaultRouter()

router.register(r'test', SignUpProxy, basename='test')
router.register('payment_accounts', PaymentAccountViewSet, basename='payment_accounts')
router.register('payments', PaymentViewSet, basename='payments')
router.register('funding_sources', FundingSourceViewSet, basename='payments')
router.register('taxes', TaxViewSet, basename='taxes')
router.register('fee_groups', FeeGroupViewSet, basename='fee_groups')
router.register('transactions', TransactionViewSet, basename='transactions')
router.register('wallets', WalletViewSet, basename='wallets')
urlpatterns = router.urls
