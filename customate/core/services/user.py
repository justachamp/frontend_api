from django.db import transaction
from django.contrib.auth import get_user_model

from core.models import Address
from core.fields import UserRole, UserStatus

import external_apis.payment.service as payment_service


from frontend_api.fields import AccountType
from frontend_api.models import Company, AdminUserAccount, SubUserAccount, UserAccount
from authentication.cognito.middleware import helpers


class UserService(object):
    user_class = get_user_model()

    @property
    def user_role(self) -> UserRole.owner:
        return UserRole.owner

    @transaction.atomic
    def create_user(self, user_name, account_type, cognito_user_id):
        address = Address()
        address.save()
        user = self.user_class.objects.create(
            username=user_name,
            email=user_name,
            role=self.user_role,
            cognito_id=cognito_user_id,
            address=address
        )
        account = UserAccount.objects.create(account_type=account_type, user=user)

        if account_type == AccountType.business.value:
            company = Company()
            address = Address()
            address.save()
            company.address = address

            company.save()
            account.company = company

        account.save()
        user.save()

    def get_user_by_external_identity(self, identity, user_data=None, auto_create=False):
        try:
            user = get_user_model().objects.get(cognito_id=identity)
        except Exception as e:
            user = None
        if not user and auto_create:
            with transaction.atomic():
                user = self.user_class.objects.create(**user_data)
                user.save()
                self._restore_account(user)

        if not user:
            raise Exception("User not found")
        elif user.status == UserStatus.inactive:
            raise Exception("User is inactive")
        elif user.status == UserStatus.banned:
            raise Exception('User is banned')

        return user

    @staticmethod
    def get_user_from_token(access_token, id_token=None, refresh_token=None):
        user, _, _, _ = helpers.get_tokens(access_token, id_token, refresh_token)
        return user

    @staticmethod
    def activate_user(user):
        user.status = UserStatus.active
        user.save()

    @staticmethod
    def verify_attribute(user, attribute):
        if getattr(user, attribute):
            if attribute == 'email':
                user.email_verified = True
            elif attribute == 'phone_number':
                user.phone_number_verified = True

            if user.contact_verified:
                user.contact_info_once_verified = True

            if user.is_owner and user.contact_verified and not user.account.payment_account_id:
                # Call payment API to create PaymentAccount if there's no one already
                payment_account_id = payment_service.PaymentAccount.create(
                    user_account_id=user.account.id,
                    email=user.email,
                    full_name=user.get_full_name()
                )
                user.assign_payment_account(payment_account_id)

            user.save()

    def user_exists(self, email):
        return self.user_class.objects.filter(email=email).exists()

    @staticmethod
    def _restore_account(user):
        role = user.role
        address = Address()
        address.save()
        user.address = address
        user.save()
        if role == UserRole.owner:
            account = UserAccount.objects.create(account_type=AccountType.personal, user=user)
            account.save()
        elif role == UserRole.admin:
            account = AdminUserAccount.objects.create(user=user)
            account.save()
        elif role == UserRole.sub_user:
            account = SubUserAccount.objects.create(user=user)
            account.save()
