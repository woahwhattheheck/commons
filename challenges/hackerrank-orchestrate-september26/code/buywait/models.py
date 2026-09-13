from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable

D = Decimal


def split_pipe(value: str | None) -> frozenset[str]:
    if not value:
        return frozenset()
    return frozenset(x.strip() for x in value.split("|") if x.strip())


def money(value: str | int | float | Decimal | None) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class Profile:
    user_id: str
    home_currency: str
    current_available_balance: Decimal
    minimum_balance_to_keep: Decimal
    financial_priorities: frozenset[str]
    protected_categories: frozenset[str]
    reducible_categories: frozenset[str]
    stoppable_categories: frozenset[str]
    accepted_payment_methods: frozenset[str]
    max_installment_months: int | None


@dataclass(frozen=True)
class FinancialEvent:
    event_id: str
    user_id: str
    event_type: str
    description: str
    category: str
    direction: str
    amount: Decimal | None
    currency: str
    event_date: date
    settlement_date: date
    status: str
    linked_event_id: str | None
    flexibility: str
    minimum_allowed_amount: Decimal | None

    def with_updates(
        self,
        *,
        amount: Decimal | None = None,
        settlement_date: date | None = None,
        status: str | None = None,
    ) -> "FinancialEvent":
        return FinancialEvent(
            event_id=self.event_id,
            user_id=self.user_id,
            event_type=self.event_type,
            description=self.description,
            category=self.category,
            direction=self.direction,
            amount=self.amount if amount is None else amount,
            currency=self.currency,
            event_date=self.event_date,
            settlement_date=self.settlement_date if settlement_date is None else settlement_date,
            status=self.status if status is None else status,
            linked_event_id=self.linked_event_id,
            flexibility=self.flexibility,
            minimum_allowed_amount=self.minimum_allowed_amount,
        )


@dataclass(frozen=True)
class PurchaseRequest:
    request_id: str
    user_id: str
    request_date: date
    request_type: str
    requested_amount: Decimal
    desired_completion_date: date
    allows_partial_payment: bool
    request_text: str


@dataclass(frozen=True)
class PaymentOption:
    payment_option_id: str
    request_id: str
    payment_method: str
    payment_amount: Decimal
    number_of_payments: int
    first_payment_date: date
    payment_frequency_days: int | None
    financing_fee: Decimal
    total_payable_amount: Decimal


@dataclass(frozen=True)
class Message:
    message_id: str
    user_id: str
    request_id: str | None
    related_event_id: str | None
    sent_at: datetime
    source_type: str
    message_text: str


@dataclass(frozen=True)
class ImageRef:
    image_id: str
    user_id: str
    request_id: str | None
    related_event_id: str | None
    path: Path


@dataclass(frozen=True)
class Cashflow:
    date: date
    amount: Decimal  # positive credit, negative debit, home currency
    event_id: str
    category: str
    description: str
    flexibility: str = "fixed"
    minimum_allowed_amount: Decimal | None = None
    generated: bool = False
    source_event_id: str | None = None


@dataclass(frozen=True)
class Payment:
    date: date
    amount: Decimal


@dataclass(frozen=True)
class SpendingChange:
    kind: str  # stop | reduce_to
    event_id: str
    category: str
    new_amount: Decimal | None = None

    def render(self) -> str:
        if self.kind == "stop":
            return f"stop:{self.event_id}"
        assert self.new_amount is not None
        return f"reduce_to:{self.event_id}:{format_decimal(self.new_amount)}"


@dataclass
class Candidate:
    method: str
    payments: list[Payment]
    total_paid: Decimal
    changes: tuple[SpendingChange, ...] = ()
    payment_option_id: str | None = None
    safe: bool = False
    min_balance_seen: Decimal | None = None

    @property
    def start_date(self) -> date:
        return min(p.date for p in self.payments)

    @property
    def completion_date(self) -> date:
        return max(p.date for p in self.payments)


@dataclass(frozen=True)
class Decision:
    request_id: str
    amount_safe_to_pay: Decimal
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str
    earliest_date_for_full_payment: date | None
    spending_changes_needed: str
    decision_explanation: str

    def as_row(self) -> dict[str, str]:
        return {
            "request_id": self.request_id,
            "amount_safe_to_pay": format_decimal(self.amount_safe_to_pay),
            "affordability_status": self.affordability_status,
            "recommended_payment_method": self.recommended_payment_method,
            "payment_plan": self.payment_plan,
            "earliest_date_for_full_payment": self.earliest_date_for_full_payment.isoformat() if self.earliest_date_for_full_payment else "",
            "spending_changes_needed": self.spending_changes_needed,
            "decision_explanation": self.decision_explanation,
        }


def format_decimal(value: Decimal) -> str:
    value = value.quantize(Decimal("0.01")) if value != value.to_integral() else value.quantize(Decimal("1"))
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def render_plan(payments: Iterable[Payment]) -> str:
    items = list(payments)
    if not items:
        return "none"
    return "|".join(f"{p.date.isoformat()}:{format_decimal(p.amount)}" for p in sorted(items, key=lambda p: p.date))
