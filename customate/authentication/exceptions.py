from rest_framework import exceptions, status
from django.utils.translation import ugettext_lazy as _

HTTP_419_AUTHENTICATION_TIMEOUT = 419


class ProlongedUserInactivityIssue(exceptions.APIException):
    status_code = HTTP_419_AUTHENTICATION_TIMEOUT
    default_detail = _('User was inactive for too long. Must re-authenticate.')
