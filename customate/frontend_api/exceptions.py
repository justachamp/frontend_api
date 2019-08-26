from rest_framework import status
from rest_framework.exceptions import APIException


class ServiceUnavailable(APIException):
	"""
	Exception for third-party services
	"""
	status_code = status.HTTP_409_CONFLICT
	default_detail = 'Our file upload service is currently unavailable, please try again later'
	default_code = 'service_unavailable'


class GBGVerificationError(APIException):
	status_code = status.HTTP_400_BAD_REQUEST
	default_detail = 'KYC request is unsuccessful. Please, contact the support team.'
	default_code = 'validation_error'
