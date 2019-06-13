from rest_framework.exceptions import ValidationError

from core.fields import Country, Currency, FundingSourceType
import logging

from payment_api.services import BaseRequestResourceSerializerService
from payment_api.validators import IBANBankValidator, GBPBankValidator

logger = logging.getLogger(__name__)
GB = Country.GB.value
GBG_SUCCESS_STATUS = 'PASS'


class BaseValidationStrategy:

    def __init__(self, resource, data):
        self._resource = resource
        self._data = data

    def is_valid(self, raise_exception=False):
        raise NotImplementedError()


class CreditCardValidationStrategy(BaseValidationStrategy):

    def is_valid(self, raise_exception=False):
        return True


class DirectDebitValidationStrategy(BaseValidationStrategy):

    SOURCE_NAME = FundingSourceType.DIRECT_DEBIT.label
    GBP_CURRENCY_NAME = Currency.GBP.label

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

    def validate_bank_account(self):
        data = self._data
        if data.get('currency') == Currency.GBP.value:
            return GBPBankValidator(self._resource, data).is_valid(True)
        else:
            return IBANBankValidator(self._resource, data).is_valid(True)


class FundingSourcesRequestResourceService(BaseRequestResourceSerializerService):

    def get_validation_strategy(self, source_type, data):
        if source_type == FundingSourceType.DIRECT_DEBIT.value:
            return DirectDebitValidationStrategy(self._resource, data)
        elif source_type == FundingSourceType.CREDIT_CARD.value:
            return CreditCardValidationStrategy(self._resource, data)

    def validate_source(self, data):
        validation_strategy = self.get_validation_strategy(data['type'], data)
        validation_strategy.is_valid(True)
        return data
