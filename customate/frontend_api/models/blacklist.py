from colorlog import logging
from django.db import models
from core.models import Model
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

BLACKLISTED_DAYS_MAX_RETRY_COUNT = 10  # max number of retries to find next non-blacklisted day


class BlacklistDate(Model):
    date = models.DateField(unique=True)
    is_active = models.BooleanField(_('active'), default=True)
    description = models.CharField(max_length=250, blank=True, null=True)

    @staticmethod
    def contains(date) -> bool:
        # Check if specified date falls in blacklist (weekend + holidays/special days)
        result = BlacklistDate._is_weekend(date) or BlacklistDate._is_blacklisted_date(date)
        logger.info(f"Blacklist verification (data={date}) returned: {result}.")
        return result

    @staticmethod
    def _is_weekend(date) -> bool:
        return date.isoweekday() >= 6

    @staticmethod
    def _is_blacklisted_date(date) -> bool:
        return BlacklistDate.objects.filter(is_active=True, date=date).exists()
