from enumfields import Enum


class UserStatus(Enum):
    inactive = 'inactive'
    active = 'active'
    blocked = 'blocked'
    banned = 'banned'
    pending = 'pending'

    class Labels:
        inactive = 'Inactive'
        active = 'Active'
        blocked = 'Blocked'
        banned = 'Banned'
        pending = 'Pending'

    def __repr__(self):
        return self.value


class UserRole(Enum):
    admin = 'admin'
    owner = 'owner'
    sub_user = 'sub_user'

    class Labels:
        admin = 'Administrator'
        owner = 'Owner'
        sub_user = 'Sub user'

    def __repr__(self):
        return self.value
