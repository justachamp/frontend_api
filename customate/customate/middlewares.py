import logging


class RequestDetailsLoggingMiddleware:
    def __init__(self, get_response=None):
        # One-time configuration and initialization.
        self.get_response = get_response
        super().__init__()

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        logging.init_shared_extra()

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
        return response
