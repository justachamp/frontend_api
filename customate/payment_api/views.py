from django.shortcuts import render

# Create your views here.
from payment_api.core.views import ProxyView
from frontend_api.permissions import IsOwnerOrReadOnly


class ItemListProxy(ProxyView):
    """
    List of items
    """
    permission_classes = (IsOwnerOrReadOnly,)
    resource_name = 'identity'
    source = 'auth/sign_in/'
    verify_ssl = False
    return_raw = True
