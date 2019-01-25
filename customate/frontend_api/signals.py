from frontend_api.models import Address
from core.models import User
from core.fields import UserRole
from django.db.models.signals import pre_save
from django.dispatch import receiver
from address.gbg.core.service import ID3Client, ModelParser
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Address)
def verify_address(sender, instance, **kwargs):
    try:
        gbg = ID3Client(parser=ModelParser)
        verification = gbg.auth_sp(instance)
        score = verification.Score
        instance.is_verified = score > 5
        logger.error(f'instance.is_verified: {instance.is_verified}, score: {score}')

    # user = instance.user
    # user.check_verification()
    # user.save()

    except Exception as e:
        pass
