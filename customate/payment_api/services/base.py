from django.utils.functional import cached_property


class BaseRequestResourceSerializerService:

    def __init__(self, resource, context=None):
        self._context = context
        self._resource = resource

    @cached_property
    def user(self):
        return self._context.get('request').user

    @cached_property
    def user_id(self):
        return str(self.user.id) if hasattr(self.user, 'id') else None

