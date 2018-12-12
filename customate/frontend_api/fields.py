from enumfields import Enum  # Uses Ethan Furman's "enum34" backport

class CompanyType(Enum):

        PUBLIC_LIMITED = 'public_limited'
        SHARE_LIMITED = 'private_limited_by_shares'
        GUARANTEE_LIMITED = 'limited_by_guarantee'
        UNLIMITED = 'unlimited'
        PARTNERSHIP_LIMITED = 'limited_liability_partnership'
        COMMUNITY_INTEREST = 'community_interest'
        INDUSTRIAL_PROVIDENT = 'industrial_provident_society'
        ROYAL_CHARTER = 'royal_charter'

        class Labels:
            PUBLIC_LIMITED = 'PUBLIC LIMITED COMPANY (PLC)'
            SHARE_LIMITED = 'PRIVATE COMPANY LIMITED BY SHARES (LTD)'
            GUARANTEE_LIMITED = 'COMPANY LIMITED BY GUARANTEE'
            UNLIMITED = 'UNLIMITED COMPANY (UNLTD)'
            PARTNERSHIP_LIMITED = 'LIMITED LIABILITY PARTNERSHIP (LLP)'
            COMMUNITY_INTEREST = 'COMMUNITY INTEREST COMPANY'
            INDUSTRIAL_PROVIDENT = 'INDUSTRIAL AND PROVIDENT SOCIETY (IPS)'
            ROYAL_CHARTER = 'ROYAL CHARTER (RC)'


class AccountType(Enum):

    PERSONAL = 'personal'
    BUSINESS = 'business'

    class Labels:
        PERSONAL = 'Personal'
        BUSINESS = 'Business'


