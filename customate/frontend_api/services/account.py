from django.db import transaction

from core.models import User
from address.gbg.core.service import ID3Client, ModelParser

import logging


# Get an instance of a logger
from frontend_api.models import Account

logger = logging.getLogger(__name__)


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
        return self.__account.user.address.country if self.__account else None

    def save_profile(self, data):
        pass
