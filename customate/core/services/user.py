from django.db import transaction
from django.contrib.auth import get_user_model

from core.models import Address
from core.fields import UserRole, UserStatus

from frontend_api.utils import assign_permissions
from frontend_api.fields import AccountType
from frontend_api.models import Account, Company, AdminUserAccount, SubUserAccount, UserAccount
from authentication.cognito.middleware import helpers


class UserService(object):

    user_class = get_user_model()

    @property
    def user_role(self)->UserRole.owner:
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
            company.save()
            account.company = company

        account.save()
        user.save()

        assign_permissions(user)

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
    def enable_mfa(user, enable, propagate_error=False):
        if enable and not user.phone_number_verified and propagate_error:
            raise ValueError("Phone number unverified")

        user.mfa_enabled = enable
        user.save()

    @staticmethod
    def verify_attribute(user, attribute):
        if getattr(user, attribute):
            if attribute == 'email':
                user.email_verified = True
            elif attribute == 'phone_number':
                user.phone_number_verified = True
            user.check_verification()
            user.save()

    def user_exists(self, email):
        return self.user_class.objects.filter(email=email).exists()

    @staticmethod
    def _restore_account(user):
        role = user.role
        if role == UserRole.owner:
            account = UserAccount.objects.create(account_type=AccountType.personal, user=user)
            account.save()
        elif role == UserRole.admin:
            account = AdminUserAccount.objects.create(user=user)
            account.save()
        elif role == UserRole.sub_user:
            account = SubUserAccount.objects.create(user=user)
            account.save()
            # company = Company.objects.create(is_active=(account_type == BUSINESS_ACCOUNT))
            # account.company = company
            # company.save()
