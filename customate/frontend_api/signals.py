from frontend_api.models import Address
from django.db.models.signals import pre_save
from django.dispatch import receiver
from address.gbg.core.service import ID3Client, ModelParser


@receiver(pre_save, sender=Address)
def verify_address(sender, instance, **kwargs):
    try:
        gbg = ID3Client(parser=ModelParser)
        verification = gbg.auth_sp(instance)
        score = verification.Score
        instance.verified = score > 5

        # user = instance.user
        # user.check_verification()
        # user.save()

    except Exception as e:
        pass
