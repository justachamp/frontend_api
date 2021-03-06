from django.utils.functional import cached_property
from rest_framework.exceptions import status, ValidationError

from payment_api.core.resource.models import ResourceQueryset


class ValidationMixin:

    def get_attr(self, attr_name, raise_exception=False, source=None):
        if not source:
            source = self

        attr = getattr(source, attr_name, None)

        if not attr and raise_exception:
            raise ValidationError({attr_name: 'Not found'}, code=status.HTTP_404_NOT_FOUND)

        return attr


class RequestResourcePaymentAccountMixin:

    @cached_property
    def payment_account_id(self):
        user = self.user
        payment_account_id = None
        if user and not user.is_anonymous:
            if user.is_owner:
                payment_account_id = user.account.payment_account_id
            if user.is_subuser:
                payment_account_id = user.account.owner_account.payment_account_id

        return str(payment_account_id) if payment_account_id else None


class RequestResourceQuerysetMixin:

    @property
    def queryset(self):
        return ResourceQueryset(self.Meta.resource_name, self._resource.client, 'get')
