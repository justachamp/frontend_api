from collections import namedtuple
from django.utils.functional import cached_property
from rest_framework.exceptions import ValidationError
from phonenumbers.phonenumberutil import region_code_for_country_code

from core.fields import Dataset
from core.models import User, USER_MIN_AGE
from address.gbg.core.service import ID3Client, ModelParser

import logging

logger = logging.getLogger(__name__)

ProfileRecord = namedtuple('ProfileRecord', 'pk, id, user, account, address, data')

IMMUTABLE_USER_FIELDS_IF_VERIFIED = (
    'first_name',
    'last_name',
    'middle_name',
    'birth_date',
    'title',
    'gender',
    'country_of_birth',
    'mother_maiden_name',
)


class AccountService:
    __profile = None

    def __init__(self, profile):
        self.__profile = profile

    def get_account_country(self):
        if not self.__profile:
            return None
        address = self.__profile.user.address if self.__profile.user else None
        current_country = address.country.value if address and address.country else None
        return self.__profile.data.get('address', {}).get('country', current_country)

    def get_user_role(self):
        if not self.__profile:
            return None
        user = self.__profile.user
        return user.role.value if user and user.role else None

    def save_profile(self, data):
        pass


class ProfileService:
    __user = None
    __data = None

    def __init__(self, user: User, data=None):
        self.__user = user

        if data:
            account = data.get('account', {})
            account['type'] = user.account.__class__.__name__
            data['account'] = account
        self.__data = data or {}

    @property
    def profile(self):
        user = self.__user
        return ProfileRecord(
            pk=user.id, id=user.id, user=user, address=user.address, account=user.account, data=self.__data
        )


class ProfileValidationService:
    __profile = None
    _errors = None

    def __init__(self, profile: ProfileRecord):
        self.__profile = profile
        self._errors = {}

    @property
    def errors(self):
        return self.errors

    @errors.setter
    def errors(self, item):
        key = item[0]
        data = item[1]

        error_item = self._errors.get(key, [])
        error_item.append(data)
        self._errors[key] = error_item

    @property
    def phone_country(self):
        phone_number = self.profile.user.phone_number
        country_code = region_code_for_country_code(phone_number.country_code) if phone_number else None
        return country_code

    @cached_property
    def available_countries(self):
        return Dataset.available_country_codes()

    def validate_age(self, user):
        birth_date = user.get('birth_date')
        if birth_date:
            self.profile.user.birth_date = birth_date

            if not self.profile.user.age_verified:
                self.errors = ('user', {'age': f'User age should be more than {USER_MIN_AGE}'})

    def validate_phone_number(self, data):
        phone_number = data.get('user').get('phone_number')
        current_number = self.profile.user.phone_number
        country_code = self.profile.user.phone_number.country_code if current_number else None
        account_verified = self.profile.account.is_verified
        if phone_number:
            self.profile.user.phone_number = phone_number
            if country_code and country_code != self.profile.user.phone_number.country_code and account_verified:
                self.errors = ('user', {'phone_number': 'Phone number should have the same country code'})

            # if self.phone_country not in self.available_countries:
            #     self.errors = ('address', {'phone_number': 'Phone number has unsupported country'})

    def validate_address_country(self, data):
        address_country = data.get('address', {}).get('country')
        phone_number = data.get('user').get('phone_number')
        if phone_number:
            self.profile.user.phone_number = phone_number

        if address_country:
            self.profile.address.country = address_country

        phone_country = self.phone_country
        address_country = self.profile.address.country
        if phone_country and address_country and phone_country != address_country.value:
            self.errors = ('address', {'country': 'Phone number should have the same country as address'})

        # if address_country and address_country.value not in self.available_countries:
        #     self.errors = ('address', {'phone_number': 'Address has unsupported country'})

    def validate_immutable_fields(self, data):
        account = self.profile.account
        if account.is_verified:
            user = self.profile.user
            user_data = data.get('user')
            for key in IMMUTABLE_USER_FIELDS_IF_VERIFIED:
                if key in user_data and getattr(user, key) != user_data[key]:
                    self.errors = (f'user', {key: f'Impossible to change after verification'})

    def validate_profile(self, attrs, raise_exception=False):
        self.validate_age(attrs['user'])
        self.validate_phone_number(attrs)
        self.validate_address_country(attrs)
        self.validate_immutable_fields(attrs)

        if self._errors and raise_exception:
            raise ValidationError(self._errors)

        return not bool(self._errors)

    @property
    def profile(self):
        return self.__profile

    def verify_profile(self, instance):

        try:
            account = instance.account
            if not account:
                return None

            user = instance.user
            """
            a phone number should be verified before a user is allowed to pass KYC.
            """
            country = instance.address.country.value if instance.address and instance.address.country else None
            # account.gbg_authentication_count = 1
            # account.verification_status = 'Fail'
            if user.is_verified and account.can_be_verified and country in self.available_countries:
                gbg = ID3Client(parser=ModelParser, country_code=country)
                # authentication_id = account.gbg_authentication_identity
                # TODO in phase we should use IncrementalVerification endpoint if we already have authentication_id
                # TODO for now we just store it

                verification = gbg.auth_sp(user)
                band_text = verification.BandText
                account.gbg_authentication_identity = verification.AuthenticationID
                account.gbg_authentication_count += 1
                account.verification_status = band_text
                account.save()
                logger.error(f'instance.is_verified: {account.verification_status}, band text: {band_text}')

        except Exception as e:
            logger.error(f'GBG verification exception: {e}')
