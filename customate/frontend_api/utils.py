from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm, remove_perm
from frontend_api.models import Address, SubUserPermission, AdminUserPermission
from core.models import User
from core.fields import UserRole

SUB_USER_PERMS = ('manage_sub_user', 'manage_funding_sources', 'manage_unload_accounts', 'manage_contract')
ADMIN_USER_PERMS = ('manage_admin_user', 'manage_tax', 'manage_fee', 'can_login_as_user')

def _assign_sub_user_perms(user, account):
    perms = SubUserPermission(instance=user.account.permission)
    for perm in SUB_USER_PERMS:
        if getattr(perms, perm):
            assign_perm(perm, user, account)


def _assign_admin_user_perms(user):
    perms = AdminUserPermission(instance=user.account.permission)
    for perm in ADMIN_USER_PERMS:
        if getattr(perms, perm):
            assign_perm(f'frontend_api.{perm}', user)


def assign_role_user_perms(user, account):
    user_type = str(user.role).lower()
    role_group = Group.objects.get_or_create(name=f'{user_type}')[0]
    user_group = Group.objects.get_or_create(name=f'{user_type}_account_{account.id}')[0]
    user_group.save()
    role_group.save()
    user.groups.add(role_group)
    user.groups.add(user_group)
    user.save()
    assign_perm(f'frontend_api.{user_type}_access', user)
    assign_perm(f'{user_type}_account_access', user, account)
    assign_perm(f'{user_type}_group_account_access', user_group, account)
    return role_group, user_group


def assign_permissions(user):
    if user.role == UserRole.owner:
        account = user.account
        assign_role_user_perms(user, account)

    elif user.role == UserRole.sub_user:
        account = user.account.owner_account
        assign_role_user_perms(user, account)
        _assign_sub_user_perms(account, user)

    elif user.role == UserRole.admin:
        account = user.account
        assign_role_user_perms(user, account)
        _assign_admin_user_perms(account, user)


def sync_sub_user_permissions(permissions):
    sub_user_account = permissions.account
    account = sub_user_account.owner_account
    user = sub_user_account.user

    for perm in SUB_USER_PERMS:
        if getattr(permissions, perm):
            assign_perm(perm, user, account)
        elif user.has_perm(perm, account):
            remove_perm(perm, user, account)


def sync_admin_user_permissions(permissions):
    account = permissions.account
    user = account.user

    for perm in ADMIN_USER_PERMS:
        if getattr(permissions, perm):
            assign_perm(f'frontend_api.{perm}', user)
        elif user.has_perm(f'frontend_api.{perm}'):
            remove_perm(f'frontend_api.{perm}', user)
