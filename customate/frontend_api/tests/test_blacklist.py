from django.test import TestCase
import logging
import arrow

from frontend_api.models.blacklist import BlacklistDate

logger = logging.getLogger(__name__)


class BlacklistDateTest(TestCase):
    def setUp(self):
        BlacklistDate.objects.all().update(is_active=False)

    def test_contains_no_match(self):
        BlacklistDate(date="2019-09-03", description="Christmas").save()
        date = arrow.get(2019, 9, 2).datetime.date()

        self.assertFalse(BlacklistDate.contains(date))

    def test_contains_no_active_match(self):
        BlacklistDate(date="2019-09-03", description="Christmas", is_active=False).save()
        date = arrow.get(2019, 9, 3).datetime.date()

        self.assertFalse(BlacklistDate.contains(date))

    def test_contains_match_by_blacklisted_date(self):
        BlacklistDate(date="2019-09-03", description="Christmas").save()
        date = arrow.get(2019, 9, 3).datetime.date()

        self.assertTrue(BlacklistDate.contains(date))

    def test_contains_match_by_weekend(self):
        BlacklistDate(date="2019-09-03", description="Christmas").save()
        date = arrow.get(2019, 9, 1).datetime.date()  # 2019-09-01 is a weekend

        self.assertTrue(BlacklistDate.contains(date))
