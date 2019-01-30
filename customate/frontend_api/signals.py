from frontend_api.models import Address, SubUserPermission, AdminUserPermission
from core.models import User
from core.fields import UserRole
from django.db.models.signals import pre_save
from django.dispatch import receiver
from address.gbg.core.service import ID3Client, ModelParser
import logging
GBG_SUCCESS_STATUS = 'PASS'


# Get an instance of a logger
logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Address)
def verify_address(sender, **kwargs):
    address = kwargs['instance']
    try:
        user = address.user
        if user:
            gbg = ID3Client(parser=ModelParser)
            verification = gbg.auth_sp(address)
            band_text = verification.Score
            address.is_verified = band_text == GBG_SUCCESS_STATUS
            logger.error(f'instance.is_verified: {address.is_verified}, band text: {band_text}')
            user.check_verification()
            user.save()

    except Exception as e:
        pass
