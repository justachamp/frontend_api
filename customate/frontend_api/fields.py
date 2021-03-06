from enumfields import Enum


class CompanyType(Enum):
    public_limited = 'public_limited'
    private_limited_by_shares = 'private_limited_by_shares'
    limited_by_guarantee = 'limited_by_guarantee'
    unlimited = 'unlimited'
    limited_liability_partnership = 'limited_liability_partnership'
    community_interest = 'community_interest'
    industrial_provident_society = 'industrial_provident_society'
    royal_charter = 'royal_charter'

    class Labels:
        public_limited = 'PUBLIC LIMITED COMPANY (PLC)'
        private_limited_by_shares = 'PRIVATE COMPANY LIMITED BY SHARES (LTD)'
        limited_by_guarantee = 'COMPANY LIMITED BY GUARANTEE'
        unlimited = 'UNLIMITED COMPANY (UNLTD)'
        limited_liability_partnership = 'LIMITED LIABILITY PARTNERSHIP (LLP)'
        community_interest = 'COMMUNITY INTEREST COMPANY'
        industrial_provident_society = 'INDUSTRIAL AND PROVIDENT SOCIETY (IPS)'
        royal_charter = 'ROYAL CHARTER (RC)'


class AccountType(Enum):
    personal = 'personal'
    business = 'business'

    class Labels:
        personal = 'Personal'
        business = 'Business'

    def __repr__(self):
        return self.value


class ScheduleStatus(Enum):
    open = 'open'
    closed = 'closed'
    stopped = 'stopped'
    pending = 'pending'  # for 'receive funds' scenario only(wait for other part to accept proposed payment schedule)
    rejected = 'rejected'  # for 'receive funds' scenario only

    class Labels:
        open = 'Open'
        closed = 'Closed'
        stopped = 'Stopped'
        pending = 'Pending'
        rejected = 'Rejected'


class SchedulePurpose(Enum):
    receive = 'receive'
    pay = 'pay'

    class Labels:
        receive = 'Receive funds'
        pay = 'Pay funds'


class SchedulePeriod(Enum):
    one_time = 'one_time'
    weekly = 'weekly'
    monthly = 'monthly'
    quarterly = 'quarterly'
    yearly = 'yearly'

    class Labels:
        one_time = 'One time payment'
        weekly = 'Weekly'
        monthly = 'Monthly'
        quarterly = 'Quarterly'
        yearly = 'Yearly'


class SchedulePaymentType(Enum):
    """
    This is intrinsic type of PaymentAPI. Calculated dynamically based on other fields related to payment
    """
    internal = 'internal'
    external = 'external'

    class Labels:
        receive = 'internal'
        pay = 'external'


class EscrowStatus(Enum):
    pending = 'pending'  # escrow is waiting to be accepted
    pending_funding = 'pending_funding'  # escrow is waiting for initial funds
    ongoing = 'ongoing'  # escrow was accepted and request/load of funds ops are ongoing
    closed = 'closed'  # closed by mutual agreement of counterparts
    terminated = 'terminated'  # 'closed' automatically due to inaction of parties involved
    rejected = 'rejected'  # was rejected for some reason by either counterpart

    class Labels:
        pending = 'Pending'
        ongoing = 'Ongoing'
        closed = 'Closed'
        terminated = 'Terminated'
        rejected = 'Rejected'


class EscrowOperationType(Enum):
    """
    Possible operations on Escrow
    """
    load_funds = 'load_funds'  # Load funds
    release_funds = 'release_funds'  # Release funds
    close_escrow = 'close_escrow'  # Request to close escrow
    create_escrow = 'create_escrow'  # Initial request to create escrow

    class Labels:
        load_funds = 'Load funds'
        release_funds = 'Release funds'
        close_escrow = 'Close escrow'
        create_escrow = 'Create escrow'


class EscrowOperationStatus(Enum):
    """
    Possible statuses of specific escrow operations
    """
    pending = 'pending'
    rejected = 'rejected'
    approved = 'approved'

    class Labels:
        pending = 'Pending'
        rejected = 'Rejected'
        approved = 'Approved'

