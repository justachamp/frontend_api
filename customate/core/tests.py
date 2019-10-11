from traceback import format_exc
from unittest import TestCase

from botocore.exceptions import ClientError
from django.test import SimpleTestCase

from authentication.cognito.core.actions import admin_delete_user, \
    admin_update_user_attributes, admin_disable_user
from authentication.cognito.core.helpers import sign_up

import logging

from core.fields import PaymentScenario, PayeeType, FundingSourceType
from core.logger import SensitiveDataObfuscator

logger = logging.getLogger(__name__)


class TestUserManagementMixin(object):
    username = "testuser@test.com"
    email = "testuser@test.com"
    password = "Testpass123$"

    @classmethod
    def disable_and_delete_test_user(cls):
        try:
            admin_disable_user(cls.username)
            admin_delete_user(cls.username)
        except ClientError as ex:
            if cls._is_specific_client_error(ex, 'UserNotFoundException'):
                # Intentionally ignore if UserNotFoundException error was raised
                logger.debug("Test user doesn't exist")
                pass
            else:
                logger.error("Disable and delete test user thrown an exception: %r" % format_exc())
                raise ex

    @classmethod
    def _is_specific_client_error(cls, ex: ClientError, expected_code: str):
        return ex.response is not None and ex.response.get('Error', {}).get('Code') == expected_code

    @classmethod
    def initialise_test_user(cls):
        try:
            data = {
                "username": cls.username,
                "password": cls.password,
                "account_type": "personal",
                "user_attributes": [
                    {"Name": "given_name", "Value": "Test"},
                    {"Name": "family_name", "Value": "User"},
                    {"Name": "email", "Value": cls.email}
                ]
            }

            sign_up(data)
            admin_update_user_attributes(cls.username, [{"Name": "email_verified", "Value": "true"}])
        except Exception as ex:
            logger.error("Could not create a test user for use with other test methods: %r" % format_exc())
            raise ex


class TestSensitiveDataObfuscator(TestCase):
    def setUp(self):
        self.filter = SensitiveDataObfuscator()

    def test_obfuscate_empty_argument(self):
        self.assertIsNone(self.filter.obfuscate(None))

    def test_obfuscate_str_iban(self):
        iban = '"iban":"DE05202208445090025780"'
        expected = '"iban":"DE0' + self.filter._placeholder + '780"'
        self.assertEqual(expected, self.filter.obfuscate(iban))

    def test_obfuscate_str_encoded_iban(self):
        iban = '\"iban\":\"DE05202208445090025780\"'
        expected = '\"iban\":\"DE0' + self.filter._placeholder + '780\"'
        self.assertEqual(expected, self.filter.obfuscate(iban))

    def test_obfuscate_str_bic(self):
        iban = '"bic": "SXPYDEHH"'
        expected = '"bic": "SX' + self.filter._placeholder + '"'
        self.assertEqual(expected, self.filter.obfuscate(iban))

    def test_obfuscate_str_email(self):
        iban = '"email": "user_for_testing@mailinator.com"'
        expected = '"email": "' + self.filter._placeholder + '"'
        self.assertEqual(expected, self.filter.obfuscate(iban))

    def test_obfuscate_str_recipient_email(self):
        iban = '"recipient_email": "user_for_testing@mailinator.com"'
        expected = '"recipient_email": "' + self.filter._placeholder + '"'
        self.assertEqual(expected, self.filter.obfuscate(iban))

    def test_obfuscate_str_address(self):
        iban = '"address_line_1": "14 Portland Chambers"'
        expected = '"address_line_1": "' + self.filter._placeholder + '"'
        self.assertEqual(expected, self.filter.obfuscate(iban))
