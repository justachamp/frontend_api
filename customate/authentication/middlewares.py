import arrow
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse

from authentication.cognito.core import helpers
from authentication.exceptions import ProlongedUserInactivityIssue
from customate.settings import MAX_ALLOW_USER_INACTIVITY


class UserActivityMonitoringMiddleware:
    def __init__(self, get_response=None):
        # One-time configuration and initialization.
        self.get_response = get_response
        super().__init__()

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
        try:
            self._control_user_inactivity(request, response)
            self._update_user_last_activity(request)
        except ProlongedUserInactivityIssue as ex:
            response = HttpResponse(status=ex.status_code)

        return response

    def _control_user_inactivity(self, request, response):
        if isinstance(request.user, AnonymousUser):
            return

        # Don't check last activity if it's some type of sign-in request (that returns "access_token")
        if 'access_token' in response.data:
            return

        if request.user.remember_me:
            return

        inactivity_bound = arrow.utcnow().replace(minutes=-MAX_ALLOW_USER_INACTIVITY).datetime
        if request.user.last_activity is not None and request.user.last_activity <= inactivity_bound:
            self._sign_out(request)
            raise ProlongedUserInactivityIssue()

    def _sign_out(self, request):
        helpers.sign_out({'access_token': request.META.get('HTTP_ACCESSTOKEN')})

    def _update_user_last_activity(self, request):
        if isinstance(request.user, AnonymousUser):
            return

        request.user.last_activity = arrow.utcnow().datetime
        request.user.save(update_fields=["last_activity"])
