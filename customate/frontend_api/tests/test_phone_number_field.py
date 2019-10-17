from django.test import TestCase
from django.contrib.auth import get_user_model


class TestPhoneNumberField(TestCase):

    def test_if_users_has_phone_number_field_as_string(self):
        users = get_user_model().objects.all()
        self.assertEqual(True, all([isinstance(user.phone_number, str) for user in users][:1000]))
