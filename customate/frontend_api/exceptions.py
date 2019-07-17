from rest_framework import exceptions, status
from django.utils.translation import ugettext_lazy as _


class NotCancelable(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Cannot cancel')
