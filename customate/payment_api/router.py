from rest_framework import routers
from payment_api.views import (
    #SignUpProxy,
    PaymentAccountViewSet,
    WalletViewSet,
    FeeGroupViewSet,
    FeeGroupAccountViewSet,
    TaxViewSet,
    TaxGroupViewSet,
    TransactionViewSet,
    PaymentViewSet,
    FundingSourceViewSet,
    PayeeViewSet,
    IbanValidationViewSet,
)
from customate.routers import router

# from rest_framework import routers

# router = routers.DefaultRouter()

#router.register(r'test', SignUpProxy, basename='test')
router.register('payment_accounts', PaymentAccountViewSet, basename='payment_accounts')
router.register('payments', PaymentViewSet, basename='payments')
router.register('funding_sources', FundingSourceViewSet, basename='funding_sources')
router.register('payees', PayeeViewSet, basename='payees')
router.register('taxes', TaxViewSet, basename='taxes')
router.register('tax_groups', TaxGroupViewSet, basename='tax_groups')
router.register('fee_groups', FeeGroupViewSet, basename='fee_groups')
router.register('fee_group_accounts', FeeGroupAccountViewSet, basename='fee_group_accounts')
router.register('transactions', TransactionViewSet, basename='transactions')
router.register('wallets', WalletViewSet, basename='wallets')
router.register('ibans/validation', IbanValidationViewSet, basename='ibans')
urlpatterns = router.urls
