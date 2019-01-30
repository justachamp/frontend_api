from __future__ import print_function

from requests import Session
from requests.auth import HTTPBasicAuth

import zeep
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken
from functools import lru_cache
from address import settings
import logging.config

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(name)s: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'zeep.transports': {
            'level': 'DEBUG',
            'propagate': True,
            'handlers': ['console'],
        },
    }
})


class ZeepProvider:

    _client = None
    _transport = None
    _session = None

    def __init__(self, user_name, password, wsdl):
        self.user_name = user_name
        self.password = password
        self.wsdl = wsdl
        self.logger = logging.getLogger(__name__)

    @property
    def client(self):
        if not self._client:
            token = UsernameToken(self.user_name, self.password)
            self._client = zeep.Client(wsdl=self.wsdl, transport=self.transport, wsse=token)
        return self._client

    @property
    def service(self):
        return self.bind

    @property
    def transport(self):
        if not self._transport:
            self._transport = Transport(session=self.session)
        return self._transport

    @property
    def session(self):
        if not self._session:
            session = Session()
            session.auth = HTTPBasicAuth(self.user_name, self.password)
            self._session = session
        return self._session

    @lru_cache(maxsize=32)
    def bind(self, service, port):
        return self.client.bind(service, port)


class ID3Client:
    _provider = None
    _parser = None
    _service = {}

    def __init__(self, parser=None):
        self.user_name = getattr(settings, 'GBG_ACCOUNT')
        self.password = getattr(settings, 'GBG_PASSWORD')
        self.wsdl = getattr(settings, 'GBG_WDSL')
        self.profile_id = getattr(settings, 'GBG_PROFILE_ID')
        self.profile_version = getattr(settings, 'GBG_PROFILE_VERSION')
        self._parser = parser
        self.logger = logging.getLogger(__name__)

    @property
    def provider(self):
        if not self._provider:

            self._provider = ZeepProvider(self.user_name, self.password, self.wsdl)

        return self._provider

    @property
    def auth_service(self):
        if not self._service.get('auth'):
            self._service['auth'] = self.provider.service('ID3global', 'basicHttpBinding_GlobalAuthenticate')
        # wsHttpBinding_GlobalAuthenticate
        return self._service['auth']

    @property
    def cred_service(self):
        if not self._service.get('cred'):
            self._service['cred'] = self.provider.service('ID3global', 'wsHttpBinding_GlobalCredentials')

        return self._service['cred']

    def check_credential(self):
        print(f'AccountName={self.user_name} Password={self.password}')
        return self.cred_service.CheckCredentials(AccountName=self.user_name, Password=self.password)

    def auth_sp(self, payload, profile_id=None, profile_version=None):
        input_data = self._parser().parse(payload)
        profile_id = profile_id or self.profile_id
        profile_version = profile_version or self.profile_version
        # '109cd19c-5cc0-4826-8df9-2d544996c844'
        return self.auth_service.AuthenticateSP(ProfileIDVersion={'ID': profile_id, 'Version': profile_version}, InputData=input_data)

    def wsdl_dump(self):
        self.provider.client.wsdl.dump()


class ModelParser(object):

    _data = None

    def __init__(self):
        self._personal_details = None
        self._current_address = None
        self._contact_details = None


    @property
    def personal_details(self):
        return self._personal_details

    @personal_details.setter
    def personal_details(self, user):
        self._personal_details = {
            # 'Title': 'Mr',
            'Forename': user.first_name,
            'MiddleName': user.middle_name,
            'Surname': user.last_name,
            # 'Gender': 'Male',
        }

        if user.birth_date:
            self._personal_details['DOBDay'] = user.birth_date.strftime('%d')
            self._personal_details['DOBMonth'] = user.birth_date.strftime('%m')
            self._personal_details['DOBYear'] = user.birth_date.strftime('%Y')
            self._personal_details['Birth'] = user.birth_date.strftime('%d-%m-%Y')

    @property
    def current_address(self):
        return self._current_address

    @current_address.setter
    def current_address(self, address):

        self._current_address = {
            'Country': address.country,
            'ZipPostcode': address.postcode,
            'AddressLine1': address.address_line_1,
            'AddressLine2': address.address_line_2
        }

    @property
    def contact_details(self):
        return self._contact_details

    @contact_details.setter
    def contact_details(self, user):

        self._contact_details = {
            # 'LandTelephone': 1234567890,
            'MobileTelephone': user.phone_number,
            'WorkTelephone': user.phone_number,
            'Email': user.email
        }

    def parse(self, address):
        user = address.user
        self.personal_details = user
        self.contact_details = user
        self.current_address = address

        self._data = {
            'Personal': {'PersonalDetails': self.personal_details},
            'ContactDetails': self.contact_details,
            'Addresses': {'CurrentAddress': self.current_address}
        }

        return self._data

