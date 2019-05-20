from django.utils.functional import cached_property

from address.gbg.core.service import ID3BankAccountClient, BankAccountParser
from core.fields import Country
import logging
logger = logging.getLogger(__name__)
GB = Country.GB.value
GBG_SUCCESS_STATUS = 'PASS'


class FundingSourceService:

    def __init__(self, funding_source):
        self.funding_source = funding_source

    def validate_bank_account(self):
        funding_source = self.funding_source
        if self.country != Country.GB.value:
            return funding_source

        gbg = self.gbg_client
        verification = gbg.auth_sp(funding_source)
        band_text = verification.BandText
        funding_source.data['bank_account_verification'] = {}
        bank_account_verification = funding_source.data['bank_account_verification']
        bank_account_verification['gbg_authentication_identity'] = verification.AuthenticationID
        bank_account_verification['gbg_verification_status'] = band_text
        logger.info(f'instance.is_verified: {band_text}')

        return band_text == GBG_SUCCESS_STATUS

    @property
    def country(self):
        return self.address.get('country')

    @cached_property
    def bank(self):
        return self.funding_source.get('bank', {})

    @cached_property
    def address(self):
        return self.bank.get('address', {})


    @property
    def gbg_client(self):
        return ID3BankAccountClient(parser=BankAccountParser, country_code=GB)


