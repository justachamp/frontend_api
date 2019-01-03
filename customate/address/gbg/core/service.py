from __future__ import print_function

from requests import Session
from requests.auth import HTTPBasicAuth

import zeep
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken
from functools import lru_cache
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

    def  __init__(self, user_name, password, wsdl):
        self.user_name = user_name
        self.password = password
        self.wsdl = wsdl
        self.logger = logging.getLogger(__name__)

    @property
    def client(self):
        if not self._client:
            token = UsernameToken(self.user_name, self.password)
            # print('token', token, 'wsdl', self.wsdl, 'transport', self.transport, 'token', token)
            # wsse = token
            self._client = zeep.Client(wsdl=self.wsdl, transport=self.transport, wsse=token)
            # self._client = zeep.Client(self.wsdl, transport=self.transport)
            # self._client = zeep.Client(
            #     'https://pilot.id3global.com/ID3gWS/ID3global.svc?wsdl', transport=self.transport, wsse=token)

            # service = client.bind('ID3global', 'wsHttpBinding_GlobalCredentials')
            # service.CheckCredentials('foo', 'bar')

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
    _service = {}

    def __init__(self, user_name, password, wsdl, profile_id, profile_version):
        self.user_name = user_name
        self.password = password
        self.wsdl = wsdl
        self.profile_id = profile_id
        self.profile_version = profile_version
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
        profile_id = profile_id or self.profile_id
        profile_version = profile_version or self.profile_version
        # '109cd19c-5cc0-4826-8df9-2d544996c844'
        return self.auth_service.AuthenticateSP(ProfileIDVersion={'ID': profile_id, 'Version': profile_version}, InputData=payload)

    def wsdl_dump(self):
        self.provider.client.wsdl.dump()



personal_details = {
    'Title': 'Mr',
    'Forename': 'Dworkin',
    'MiddleName': 'John',
    'Surname': 'Barimen',
    'Gender': 'Male',
    'DOBDay': '20',
    'DOBMonth': '8',
    'DOBYear': '1922'
    # 'Birth': '20-08-1922 00:00:00'
}
address_details = {
    'Country': 'uk',
    'ZipPostcode': 90210,
    'AddressLine1': 'Dungeon 1',
    'AddressLine2': 'Courts of Amber'
}

contact_details = {
    # 'LandTelephone': 1234567890,
    'MobileTelephone': 1234567890,
    'WorkTelephone': 1234567890,
    'Email': 'dworkin@thepattern.net'
}

identity = {
    # 'ProfileIDVersion': {'ID': 'PROFILEID', 'Version': 0},
    'Personal': {'PersonalDetails': personal_details},
    'ContactDetails': contact_details,
    'Addresses': {'CurrentAddress': address_details}
}

data = {
'user_name': 'alexander.tarasenko@customate.net',
# 'password': 'Oo8&xvDop*3LEaxT',
#     'password': '__MryBrsQzDzHL9wy',
    'password': '*5rES3JWY5JMVv5C',
'wsdl': 'https://pilot.id3global.com/ID3gWS/ID3global.svc?wsdl',
    'profile_id': '109cd19c-5cc0-4826-8df9-2d544996c844',
    'profile_version': 0
}
# Oo8&xvDop*3LEaxT
# cust05rES3JWY5JMVv5C
# AkmbyvYVAkt2L8M
# __MryBrsQzDzHL9wy
# data = {
# 'user_name': 'alexandertarasenko@customate.net',
# 'password': '*5rES3JWY5JMVv5C',
# 'wsdl': 'https://www.id3global.com/ID3gWS/ID3global.svc?wsdl',
#     'profile_id': 'e8ee100e-57dc-4d70-8538-bd2fa8013096',
#     'profile_version': 0
# }

# data = {
#     'user_name': 'admin@customate.net',
#     'password': 'Customate123456789@',
#     'wsdl': 'https://www.id3global.com/ID3gWS/ID3global.svc?wsdl',
# }


id3 = ID3Client(**data)
# id3.check_credential()
id3.auth_sp(payload=identity)
# id3.wsdl_dump()
# service.CheckCredentials(AccountName=userName, Password=password)

#
# Title: xsd:string,
# Forename: xsd:string,
# MiddleName: xsd:string,
# Surname: xsd:string,
# Gender: {http://www.id3global.com/ID3gWS/2013/04}GlobalGender,
# DOBDay: xsd:int,
# DOBMonth: xsd:int,
# DOBYear: xsd:int,
# Birth: {http://www.id3global.com/ID3gWS/2013/04}GlobalUKBirth,
# CountryOfBirth: xsd:string,
# SecondSurname: xsd:string,
# AdditionalMiddleNames: {http://schemas.microsoft.com/2003/10/Serialization/Arrays}ArrayOfstring`

# service.CheckCredentialsWithPIN(AccountName=userName, Password=password, PINSequence='1234')
# service.Address()
#
# print(service)
# service
# service.AuthenticateSP(InputData=identity)
# ProfileIDVersion='1235test'

# # service.AddressLookup('AccountName', 'Password')
# service.AddressLookup({
#     # 'country': 'nz',
#     'ZipPostcode': '90210',
#     # 'AddressLine1': 'Dungeon 1',
#     # 'AddressLine2': 'Courts of Amber'
# })

# client.wsdl.dump()
# http://www.id3globalsupport.com/Website/content/Web-Service/WSDL%20Page/WSDL%20HTML/ID3%20Global%20WSDL-%20Live.xhtml#op.d1e6784
# http://www.id3globalsupport.com/Website/content/Web-Service/WSDL%20Page/WSDL%20HTML/ID3%20Global%20WSDL-%20Live.xhtml#src.d1e6784
# http://www.id3globalsupport.com/Website/content/Web-Service/WSDL%20Page/WSDL%20HTML/ID3%20Global%20WSDL-%20Live.xhtml#port.d1e6783
# http://www.id3globalsupport.com/Website/content/Sample%20Code/Web%20Dev%20Guide%20HTML/html/9f536f03-cd64-63b3-d21b-b400994ff43e.htm#
# http://www.id3globalsupport.com/Website/content/Sample%20Code/Web%20Dev%20Guide%20HTML/html/aedc65f7-bb15-7d52-cd85-f14cdb124075.htm
# http://www.id3globalsupport.com/Website/content/Sample%20Code/Web%20Dev%20Guide%20HTML/html/11998094-bef9-97b0-6af3-350de9749e6c.htm
# http://www.id3globalsupport.com/Website/content/Sample%20Code/Web%20Dev%20Guide%20HTML/html/11998094-bef9-97b0-6af3-350de9749e6c.htm
# https://www.id3global.com/ID3gWS/ID3global.svc?wsdl=
# http://www.id3globalsupport.com/Website/content/Web-Service/WSDL%20Page/WSDL%20HTML/ID3%20Global%20WSDL-%20Live.xhtml#op.d1e6784

