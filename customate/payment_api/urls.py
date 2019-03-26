
from payment_api.views import ItemListProxy
from django.conf.urls import url

urlpatterns = [url(r'^item/$', ItemListProxy.as_view(), name='item-list')]