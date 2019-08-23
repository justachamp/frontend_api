from traceback import format_exc
import logging
from collections import namedtuple
import arrow
from django.utils.functional import cached_property
from rest_framework.exceptions import ValidationError
from phonenumbers.phonenumberutil import region_code_for_country_code
from core.fields import Dataset, Country
from core.models import User, USER_MIN_AGE, Address as CoreAddress
from frontend_api.models import Account
from frontend_api.core.client import PaymentApiClient
from external_apis.gbg.models import ContactDetails, PersonalDetails, Address
from external_apis.gbg.models import IdentityDocument, UKIdentityDocument, SpainIdentityDocument, IdentityCard
from external_apis.gbg.service import validate_identity_details

logger = logging.getLogger(__name__)

ProfileRecord = namedtuple('ProfileRecord', 'pk, id, user, account, address, credentials, data')

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

# TODO: Refactor 'service' classes to remove them at all (move logic to Views/Models as appropriate)

class AccountService:
    _profile = None

    def __init__(self, profile):
        self._profile = profile

    def get_account_country(self):
        if not self._profile:
            return None
        address = self._profile.user.address if self._profile.user else None
        current_country = address.country.value if address and address.country else None
        return self._profile.data.get('address', {}).get('country', current_country)

    def get_user_role(self):
        if not self._profile:
            return None
        user = self._profile.user
        return user.role.value if user and user.role else None

    def save_profile(self, data):
        pass


class ProfileService:
    _user = None
    _data = None

    def __init__(self, user: User, data=None):
        self._user = user

        if data:
            account = data.get('account', {})
            account['type'] = user.account.__class__.__name__
            data['account'] = account
        self._data = data or {}

    @property
    def profile(self):
        user = self._user
        return ProfileRecord(
            pk=user.id,
            id=user.id,
            user=user,
            address=user.address,
            account=user.account,
            credentials=self._data.get('credentials'),
            data=self._data
        )


class ProfileValidationService:
    _profile = None
    _errors = None
    _payment_service = None

    def __init__(self, profile: ProfileRecord):
        self._profile = profile
        self._errors = {}

    @cached_property
    def payment_client(self):
        return PaymentApiClient(self.profile.user)

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
        if phone_number:
            self.profile.user.phone_number = phone_number

            if self.phone_country not in self.available_countries:
                self.errors = ('address', {'phone_number': 'Unsupported country code'})

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

        if address_country and address_country.value not in self.available_countries:
            self.errors = ('address', {'phone_number': 'Unsupported country code'})

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
        return self._profile

    @staticmethod
    def get_identity_document(country: Country, account: Account, user: User) -> IdentityDocument:
        """
        Returns IdentityData for specific country
        :param country:
        :param account:
        :param user:
        :return:
        """
        id_doc = None
        if country == Country.GB:
            dli_date = account.country_fields.get("driver_licence_issue_date")
            dli_date = arrow.get(dli_date, "YYYY-MM-DD", tzinfo='local').datetime.date() \
                if isinstance(dli_date, str) else dli_date
            id_doc = UKIdentityDocument(
                passport_number=user.passport_number,
                passport_expiry_date=user.passport_date_expiry,
                driving_licence_number=account.country_fields.get("driver_licence_number"),
                driving_licence_postcode=account.country_fields.get("driver_licence_postcode"),
                driving_licence_issue_date=dli_date
            )
        elif country == Country.IT:  # Italy
            id_doc = IdentityCard(number=account.country_fields.get("tax_code"), country=country)
        elif country == Country.DK:  # Denmark
            id_doc = IdentityCard(number=account.country_fields.get("id_card_number"), country=country)
        elif country == Country.SP:  # Spain
            id_doc = SpainIdentityDocument(tax_id_number=account.country_fields.get("tax_id"))

        return id_doc

    def verify_profile(self, instance):

        account = getattr(instance, 'account', None)
        if not account:
            return None

        user = getattr(instance, 'user', None)
        if not user or user.is_admin:
            return None

        # a phone number should be verified before a user is allowed to pass KYC(Know Your Customer).
        address = getattr(instance, 'address', None)  # type: CoreAddress
        country_val = address.country.value if address and address.country else None  # 2-letter country code
        self.payment_client.assign_payment_account()

        if not user.is_verified:
            return None

        if not (account.can_be_verified and country_val):
            return None

        try:
            logger.info("GBG user verification (user=%r)" % user)

            gbg_result = validate_identity_details(
                country=address.country,
                personal_details=PersonalDetails(
                    first_name=user.first_name,
                    middle_name=user.middle_name,
                    last_name=user.last_name,
                    birth_date=user.birth_date,
                    gender=user.gender,
                    title=user.title,
                    mothers_maiden_name=user.mother_maiden_name,
                    country_of_birth=user.country_of_birth
                ), current_address=Address(
                    city=address.city,
                    post_code=address.postcode,
                    address_line_1=address.address_line_1,
                    address_line_2=address.address_line_2,
                    locality=address.locality,
                    country=address.country.value,
                ), contact_details=ContactDetails(
                    mobile_phone=str(user.phone_number),
                    email=user.email
                ),
                identity_document=ProfileValidationService.get_identity_document(address.country, account, user)
            )

            # TODO: use "IncrementalVerification endpoint if we already have authentication_id
            # TODO: for now we just store it

            account.gbg_authentication_identity = gbg_result.AuthenticationID
            account.verification_status = gbg_result.BandText
            account.gbg_authentication_count += 1

            account.save()

        except Exception as e:
            logger.error("GBG verification (user=%s, address=%s) exception: %r" % (user, address, format_exc()))
            # raise ValidationError("KYC request is unsuccessful. Please, contact the support team.")
