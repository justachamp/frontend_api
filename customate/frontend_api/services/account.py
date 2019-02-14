from django.db import transaction

from core.models import User
from address.gbg.core.service import ID3Client, ModelParser

import logging


# Get an instance of a logger
logger = logging.getLogger(__name__)


class AccountService:

    def verify(self, user: User):
        try:
            account = user.account
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
