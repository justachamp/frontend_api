
from payment_api.views import ItemListProxy, WalletViewSet, WalletRelationshipView, PaymentAccountViewSet, PaymentAccountRelationshipView
from django.conf.urls import url
from django.urls import include, path, re_path
from payment_api.router import urlpatterns as proxy_url

urlpatterns = [
    url(r'^', include(proxy_url)),
    url(r'^item/$', ItemListProxy.as_view(), name='item-list'),

    re_path(r'^payment_account/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            PaymentAccountViewSet.as_view({'get': 'retrieve_related'}), #{'get': 'retrieve_related'}
            name='payment-account-related'),

    re_path(r'^payment_account/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=PaymentAccountRelationshipView.as_view(),
            name='payment-account-relationships'
            ),
]