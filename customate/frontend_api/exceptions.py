from rest_framework.exceptions import APIException

class ServiceUnavailable(APIException):
	"""
	Exception for third-party services
	"""
	status_code = 409
	default_detail = 'Our file upload service is currently unavailable, please try again later'
	default_code = 'service_unavailable'