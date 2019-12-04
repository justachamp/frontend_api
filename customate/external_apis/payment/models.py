from uuid import UUID
from dataclasses import dataclass
from core.fields import PaymentStatusType, Currency, PayeeType, FundingSourceType


@dataclass(frozen=True)
class FundingSourceDetails:
    id: UUID
    currency: Currency
    type: FundingSourceType
    payment_account_id: UUID


@dataclass(frozen=True)
class PayeeDetails:
    id: UUID
    title: str
    type: PayeeType
    iban: str
    recipient_name: str
    recipient_email: str
    payment_account_id: UUID


@dataclass(frozen=True)
class PaymentResult:
    id: UUID
    status: PaymentStatusType


@dataclass(frozen=True)
class WalletDetails:
    id: UUID
    currency: Currency
    iban: str
    balance: int
    is_virtual: bool
    payment_account_id: UUID
    payee_id: UUID
    funding_source_id: UUID
