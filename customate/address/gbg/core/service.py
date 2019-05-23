from functools import wraps
import datetime

from requests import Session
from requests.auth import HTTPBasicAuth

import zeep
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken
from functools import lru_cache
from address import settings
import logging.config

from address.gbg.core.utils import set_value_at_keypath
from core.models import User


def format_country_data(identity_key, post_data=None):
    def wrapper(f):
        @wraps(f)
        def wrapped(self, *args, **kwargs):
            identity = {}
            kwargs['identity'] = identity
            f(self, *args, **kwargs)
            if len(identity):
                if post_data and len(post_data):
                    for key, value in post_data.items():
                        set_value_at_keypath(identity, key, value)
            return {identity_key: identity} if len(identity) else None

        return wrapped

    return wrapper


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


class BaseID3Client:
    _provider = None
    _parser = None
    _service = {}

    def __init__(self, parser, country_code):

        self.country_code = country_code
        self._apply_profile(country_code)
        self._apply_credentials(country_code)
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
        self.logger.info(f'AccountName={self.user_name} Password={self.password}')
        return self.cred_service.CheckCredentials(AccountName=self.user_name, Password=self.password)

    def auth_sp(self, payload, profile_id=None, profile_version=None):
        input_data = self._parser(self.country_code).parse(payload)
        profile_id = profile_id or self.profile_id
        profile_version = profile_version or self.profile_version

        if not profile_id:
            raise ValueError('Unsupported profile')

        return self.auth_service.AuthenticateSP(
            ProfileIDVersion={'ID': profile_id,
                              'Version': profile_version
                              }, InputData=input_data)

    def wsdl_dump(self):
        self.provider.client.wsdl.dump()

    def _apply_profile(self, country_code):
        raise NotImplementedError

    def _apply_credentials(self, country_code):
        raise NotImplementedError


class ID3Client(BaseID3Client):

    def _apply_profile(self, country_code):
        self.profile_id = getattr(settings, f'GBG_{country_code}_PROFILE_ID', None)
        self.profile_version = getattr(settings, 'GBG_PROFILE_VERSION')

    def _apply_credentials(self, country_code):
        self.user_name = getattr(settings, 'GBG_ACCOUNT')
        self.password = getattr(settings, 'GBG_PASSWORD')
        self.wsdl = getattr(settings, 'GBG_WDSL')


class ID3BankAccountClient(BaseID3Client):
    # TODO: what is this for?  Looks like copy-pase of the above

    def _apply_profile(self, country_code):
        self.profile_id = getattr(settings, f'GBG_{country_code}_BANK_VALIDATION_PROFILE_ID', None)
        self.profile_version = getattr(settings, 'GBG_PROFILE_VERSION')

    def _apply_credentials(self, country_code):
        self.user_name = getattr(settings, 'GBG_BANK_VALIDATION_ACCOUNT')
        self.password = getattr(settings, 'GBG_BANK_VALIDATION_PASSWORD')
        self.wsdl = getattr(settings, 'GBG_BANK_VALIDATION_WDSL')


class ModelParser(object):
    _data = None

    def __init__(self, country_code):
        self._personal_details = None
        self._current_address = None
        self._contact_details = None
        self.country_code = country_code

    @property
    def personal_details(self):
        return self._personal_details

    @personal_details.setter
    def personal_details(self, user):
        self._personal_details = {
            'Title': user.title,
            'Forename': user.first_name,
            'MiddleName': user.middle_name,
            'Surname': user.last_name,
            'Gender': user.gender,
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
            'AddressLine2': address.address_line_2,
            'AddressLine3': address.address_line_3,
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

    def parse(self, user: User):
        self.personal_details = user
        self.contact_details = user
        self.current_address = user.address

        self._data = {
            'Personal': {'PersonalDetails': self.personal_details},
            'ContactDetails': self.contact_details,
            'Addresses': {'CurrentAddress': self.current_address}
        }

        self.apply_additional_data(user)

        return self._data

    def apply_additional_data(self, user: User):
        code = self.country_code
        country_identity_name = f'_{code.lower()}_identity' if code else None
        country_identity = getattr(self, country_identity_name, None)
        source = user.account.country_fields
        country_identity_data = country_identity(source) if callable(country_identity) else None

        if country_identity_data:
            self._data['IdentityDocuments'] = country_identity_data

    @staticmethod
    def apply_if_exists(source, identity, params):
        if not source:
            return None

        if isinstance(source, dict):
            for key, param in params.items():
                param = source.get(param, None)
                if param:
                    set_value_at_keypath(identity, key, param)
        else:
            for key, param in params.items():
                if hasattr(source, param):
                    set_value_at_keypath(identity, key, getattr(source, param))

    @format_country_data(identity_key='UK')
    def _gb_identity(self, source, identity):

        schema = {
            'DrivingLicence.Number': 'driver_licence_number',
            'DrivingLicence.Postcode': 'driver_licence_postcode'
        }
        date_schema = {
            'DrivingLicence.IssueDay': 'day',
            'DrivingLicence.IssueMonth': 'month',
            'DrivingLicence.IssueYear': 'year'
        }

        self.apply_if_exists(source, identity, schema)
        self.apply_if_exists(source.get('driver_licence_issue_date'), identity, date_schema)

    @format_country_data(identity_key='IdentityCard', post_data={'Country': 'Italy'})
    def _it_identity(self, source, identity):
        self.apply_if_exists(source, identity, {'Number': 'tax_code'})

    @format_country_data(identity_key='IdentityCard', post_data={'Country': 'Denmark'})
    def _dk_identity(self, source, identity):
        self.apply_if_exists(source, identity, {'Number': 'id_card_number'})

    @format_country_data(identity_key='Spain')
    def _sp_idenity(self, source, identity):
        self.apply_if_exists(source, identity, {'TaxIDNumber.Number': 'tax_id'})


class BankAccountParser:
    _data = None

    def __init__(self, country_code):
        self._personal_details = None
        self._current_address = None
        self._banking_details = None
        self.country_code = country_code

    @property
    def personal_details(self):
        return self._personal_details

    @personal_details.setter
    def personal_details(self, user):
        self._personal_details = {
            'Forename': user.get('first_name'),
            'Surname': user.get('last_name'),
        }

    @property
    def banking_details(self):
        return self._personal_details

    @banking_details.setter
    def banking_details(self, account):
        self._banking_details = {
            'SortCode': account.get('sortCode'),
            'AccountNumber': account.get('accountNumber'),
        }

    @property
    def current_address(self):
        return self._current_address

    @current_address.setter
    def current_address(self, address):
        self._current_address = {
            'Country': address.get('country'),
            'City': address.get('city'),
            'ZipPostcode': address.get('postcode'),
            'AddressLine1': address.get('address_line_1', ''),
            'AddressLine2': address.get('address_line_2', ''),
            'AddressLine3': address.get('address_line_3', ''),
        }

    def parse(self, source):
        self.personal_details = source.get('recipient', {})
        self.banking_details = source.get('account', {})
        self.current_address = source.get('recipient', {}).get('address', {})

        self._data = {
            'Personal': {'PersonalDetails': self.personal_details},
            'BankingDetails': {'BankAccount': self.banking_details},
            'Addresses': {'CurrentAddress': self.current_address}
        }

        return self._data
