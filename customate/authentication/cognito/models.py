
class Entity(object):
    fields = []

    def __init__(self, **kwargs):
        for field in self.fields:
            setattr(self, field, kwargs.get(field, None))

        self.pk = getattr(self, 'id')


class Identity(Entity):
    fields = ('id', 'preferred_username', 'user_attributes', 'id_token', 'access_token', 'refresh_token',
             'account_type', 'user')


class Invitation(Entity):
    fields = ('id', 'username', 'temporary_password', 'action', 'delivery', 'user_attributes')


class Challenge(Entity):
    fields = ('id', 'username', 'challenge_name', 'challenge_delivery', 'destination', 'session')


class Verification(Entity):
    fields = ('id', 'attribute_name', 'destination')
