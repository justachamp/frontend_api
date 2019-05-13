from rest_framework.filters import SearchFilter

from rest_framework_json_api.filters import QueryParameterValidationFilter

from payment_api.core.resource.filters import (
    InclusionFiler, IbanGeneralPartFiler,
    ResourceFilterBackend,
    OrderingFilter
)
from payment_api.core.resource.views import ResourceViewSet, ResourceRelationshipView
from payment_api.views.wallet import WalletViewSet, WalletRelationshipView
from payment_api.views.payment_account import PaymentAccountViewSet, PaymentAccountRelationshipView
from payment_api.views.fee import FeeGroupViewSet, FeeGroupRelationshipView, FeeGroupAccountViewSet, FeeGroupAccountRelationshipView
from payment_api.views.tax import TaxViewSet, TaxRelationshipView, TaxGroupViewSet, TaxGroupRelationshipView
from payment_api.views.transaction import TransactionViewSet, TransactionRelationshipView
from payment_api.views.payment import PaymentViewSet, PaymentRelationshipView
from payment_api.views.funding_source import FundingSourceViewSet, FundingSourceRelationshipView
from payment_api.views.payee import PayeeViewSet, PayeeRelationshipView

#from payment_api.views._raw_proxy_views import ItemListProxy, SignUpProxy


__all__ = [
    InclusionFiler,
    IbanGeneralPartFiler,
    QueryParameterValidationFilter,
    OrderingFilter,
    SearchFilter,
    ResourceFilterBackend,
    ResourceRelationshipView,
    ResourceViewSet,
    WalletViewSet,
    WalletRelationshipView,
    PaymentAccountViewSet,
    PaymentAccountRelationshipView,
    FeeGroupViewSet,
    FeeGroupRelationshipView,
    FeeGroupAccountViewSet,
    FeeGroupAccountRelationshipView,
    TaxViewSet,
    TaxRelationshipView,
    TaxGroupViewSet,
    TaxGroupRelationshipView,
    TransactionViewSet,
    TransactionRelationshipView,
    PaymentViewSet,
    PaymentRelationshipView,
    FundingSourceViewSet,
    FundingSourceRelationshipView,
    PayeeViewSet,
    PayeeRelationshipView,
    #ItemListProxy,
    #SignUpProxy
]
