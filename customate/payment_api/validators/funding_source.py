
from rest_framework.exceptions import ValidationError

from address.gbg.core.service import ID3BankAccountClient, BankAccountParser
from core.fields import Country, Currency, FundingSourceType
import logging

logger = logging.getLogger(__name__)
GBG_SUCCESS_STATUS = 'Pass'


class BaseBankValidator:

    def __init__(self, resource, data):
        self._resource = resource
        self._data = data

    def validate_bank_account(self):
        raise NotImplementedError()

    def is_valid(self, raise_exception=False):
        try:
            self.validate_bank_account()
        except ValidationError as ex:
            logger.error(ex)
            if raise_exception:
                raise ex

        except Exception as ex:
            logger.error(ex)
            if raise_exception:
                raise ex


class IBANBankValidator(BaseBankValidator):

    def validate_bank_account(self):
        return true


class GBPBankValidator(BaseBankValidator):

    @property
    def gbg_client(self):
        return ID3BankAccountClient(parser=BankAccountParser, country_code=Country.GB.value)

    def validate_currency(self, currency):
        if currency != Currency.GBP.value:
            raise ValidationError({
                "currency": f'{FundingSourceType.DIRECT_DEBIT.label} funding source supports {Currency.GBP.label} only'
            })

    def validate_gbg(self, data):
        self.validate_currency(data.get('currency'))

        gbg = self.gbg_client
        verification = gbg.auth_sp(data)
        band_text = verification.BandText
        data['data'] = {**data.get('data', {}), 'bank_account_verification': {
            'gbg_authentication_identity': verification.AuthenticationID,
            'gbg_verification_status': band_text
        }}
        logger.info(f'instance.is_verified: {band_text}')
        return band_text == GBG_SUCCESS_STATUS

    def validate_bank_account(self):
        if not self.validate_gbg(self._data):
            raise ValidationError("GBG validation failed")
        return self._data