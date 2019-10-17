from rest_framework import exceptions, status
from django.utils.translation import ugettext_lazy as _


class GeneralCognitoException(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Cognito exception.')


class Unauthorized(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Unauthorized.')


class TokenIssue(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('There is an issue with access token.')
