from payment_api.views import (
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

)

from payment_api.views.cat import CatView

from django.conf.urls import url
from django.urls import include, re_path, path
from payment_api.router import urlpatterns as proxy_url

urlpatterns = [
    url(r'^', include(proxy_url)),

    re_path(r'^payment_accounts/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            PaymentAccountViewSet.as_view({'get': 'retrieve_related'}),  # {'get': 'retrieve_related'}
            name='payment-account-related'),

    re_path(r'^payment_accounts/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=PaymentAccountRelationshipView.as_view(),
            name='payment-account-relationships'
            ),

    re_path(r'^wallets/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            WalletViewSet.as_view({'get': 'retrieve_related'}),  # {'get': 'retrieve_related'}
            name='wallet-related'),

    re_path(r'^wallets/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=WalletRelationshipView.as_view(),
            name='wallet-relationships'
            ),

    re_path(r'^fee_groups/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            FeeGroupViewSet.as_view({'get': 'retrieve_related'}),
            name='fee-group-related'),

    re_path(r'^fee_groups/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=FeeGroupRelationshipView.as_view(),
            name='fee-group-relationships'
            ),

    re_path(r'^fee_group_accounts/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            FeeGroupAccountViewSet.as_view({'get': 'retrieve_related'}),
            name='fee-group-account-related'),

    re_path(r'^fee_group_accounts/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=FeeGroupAccountRelationshipView.as_view(),
            name='fee-group-account-relationships'
            ),

    re_path(r'^taxes/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            TaxViewSet.as_view({'get': 'retrieve_related'}),  # {'get': 'retrieve_related'}
            name='tax-related'),

    re_path(r'^taxes/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=TaxRelationshipView.as_view(),
            name='tax-relationships'
            ),

    re_path(r'^tax_groups/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            TaxGroupViewSet.as_view({'get': 'retrieve_related'}),
            name='tax-group-related'),

    re_path(r'^tax_groups/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=TaxGroupRelationshipView.as_view(),
            name='tax-group-relationships'
            ),

    re_path(r'^transactions/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            TransactionViewSet.as_view({'get': 'retrieve_related'}),  # {'get': 'retrieve_related'}
            name='transaction-related'),

    re_path(r'^transactions/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=TransactionRelationshipView.as_view(),
            name='transaction-relationships'
            ),

    re_path(r'^payments/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            PaymentViewSet.as_view({'get': 'retrieve_related'}),  # {'get': 'retrieve_related'}
            name='payment-related'),

    re_path(r'^payments/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=PaymentRelationshipView.as_view(),
            name='payment-relationships'
            ),

    re_path(r'^funding_sources/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            FundingSourceViewSet.as_view({'get': 'retrieve_related'}),  # {'get': 'retrieve_related'}
            name='funding-source-related'),

    re_path(r'^funding_sources/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=FundingSourceRelationshipView.as_view(),
            name='funding-source-relationships'
            ),

    re_path(r'^payees/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            PayeeViewSet.as_view({'get': 'retrieve_related'}),  # {'get': 'retrieve_related'}
            name='payee-related'),

    re_path(r'^payees/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=PayeeRelationshipView.as_view(),
            name='payee-relationships'
            ),

    # re_path(r'^cats/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
    #         CatView.as_view(),  # {'get': 'retrieve_related'}
    #         name='cat-related'),

    path('cats/', CatView.as_view()),
    #path('snippets/<int:pk>/', views.SnippetDetail.as_view()),
]
