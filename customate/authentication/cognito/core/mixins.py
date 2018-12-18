from authentication.cognito.core.service import Identity
from authentication.cognito.core.actions import admin_update_user_attributes, admin_get_user
from authentication.cognito.middleware import helpers as m_helpers


class Auth(object):
    __identity = None
    __request = None
    __user = None

    def __init__(self, request):
        self.__request = request

    def check(self, name, value):
        rec = filter(lambda in_rec: in_rec.get('Name') == name, self.user.get('UserAttributes'))
        rec = list(rec)
        return True if rec and len(rec) and rec[0]['Value'] == value else False

    @property
    def user(self):

        if not self.__user:
            self.__user = admin_get_user(str(self.__request.user.cognito_id))
        return self.__user

    def update_attribute(self, name, value):
        return admin_update_user_attributes(str(self.__request.user.cognito_id), [{'Name': name, 'Value': value}])

    @property
    def idenity(self):
        if not self.__identity:
            self.__identity = Identity()
        return self.__identity


class AuthSerializerMixin(object):
    __auth = None

    @property
    def auth(self):
        if not self.__auth:
            self.__auth = Auth(self.context.get('request'))



        return self.__auth