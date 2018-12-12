from enumfields import Enum, EnumField  # Uses Ethan Furman's "enum34" backport


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


