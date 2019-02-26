from django.db import transaction
from rest_framework.exceptions import ValidationError

from core.models import User, USER_MIN_AGE
from address.gbg.core.service import ID3Client, ModelParser

import logging


# Get an instance of a logger
from frontend_api.models import Account

logger = logging.getLogger(__name__)

from collections import namedtuple

ProfileRecord = namedtuple('ProfileRecord', 'pk, id, user, account, address')


class AccountService:

    __account = None

    def __init__(self, account: Account):
        if isinstance(account, Account):
            self.__account = account

    def verify(self):
        try:
            account = self.__account
            if not account:
                return None

            user = account.user
            """
            a phone number should be verified before a user is allowed to pass KYC.
            """

            if user.is_verified and account.need_to_verify:
                gbg = ID3Client(parser=ModelParser)
                authentication_id = account.gbg_authentication_identity
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

    def get_account_country(self):
        has_address = self.__account and self.__account.user and self.__account.user.address
        return self.__account.user.address.country if has_address else None

    def save_profile(self, data):
        pass


class ProfileService:

    __user = None

    def __init__(self, user: User):
        self.__user = user

    def phone_country(self, phone):
        return False

    def validate_age(self):
        user = self.__user
        if not user.age_verified:
            raise ValidationError(f'User age should be more than {USER_MIN_AGE}')

    def validate_phone_number(self):
        user = self.__user
        if self.phone_country(user.phone_number) != user.address.country:
            raise ValidationError('Phone number should have the same country as address')


    @property
    def profile(self):
        user = self.__user
        return ProfileRecord(pk=user.id, id=user.id, user=user, address=user.address, account=user.account)





class ProfileValidationService:

    __profile = None

    def __init__(self, profile: ProfileRecord):
        self.__profile = profile

    @property
    def phone_country(self):
        return False

    def validate_age(self):

        if not self.profile.user.age_verified:
            raise ValidationError({'age': f'User age should be more than {USER_MIN_AGE}'})

    def validate_phone_number(self):
        phone_country = self.phone_country
        address_country = self.profile.address.country
        if phone_country and address_country and phone_country != address_country:
            raise ValidationError({'address/country': 'Phone number should have the same country as address'})

    def validate_address_country(self):
        phone_country = self.phone_country
        address_country = self.profile.address.country
        if phone_country and address_country and phone_country != address_country:
            raise ValidationError({'address/country': 'Phone number should have the same country as address'})

    @property
    def profile(self):
        return self.__profile

