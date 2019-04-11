from payment_api.views import ItemListProxy, WalletViewSet, WalletRelationshipView
from payment_api.views import PaymentAccountViewSet, PaymentAccountRelationshipView
from payment_api.views import TaxViewSet, TaxRelationshipView

from payment_api.views import (
    ItemListProxy,
    WalletViewSet,
    WalletRelationshipView,
    PaymentAccountViewSet,
    PaymentAccountRelationshipView,
    FeeGroupViewSet,
    FeeGroupRelationshipView
)

from django.conf.urls import url
from django.urls import include, path, re_path
from payment_api.router import urlpatterns as proxy_url

urlpatterns = [
    url(r'^', include(proxy_url)),
    url(r'^item/$', ItemListProxy.as_view(), name='item-list'),

    # /api/v1/payment_account
    re_path(r'^payment_account/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            PaymentAccountViewSet.as_view({'get': 'retrieve_related'}),  # {'get': 'retrieve_related'}
            name='payment-account-related'),

    re_path(r'^payment_account/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=PaymentAccountRelationshipView.as_view(),
            name='payment-account-relationships'
            ),

    re_path(r'^fee_group/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            FeeGroupViewSet.as_view({'get': 'retrieve_related'}),
            name='fee-group-related'),

    re_path(r'^fee_group/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=FeeGroupRelationshipView.as_view(),
            name='fee-group-relationships'
            ),

    # /api/v1/tax
    re_path(r'^tax/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            TaxViewSet.as_view({'get': 'retrieve_related'}),  # {'get': 'retrieve_related'}
            name='payment-account-related'),

    re_path(r'^tax/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=TaxRelationshipView.as_view(),
            name='payment-account-relationships'
            ),
]
