from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .models import (
    FinancialEvent,
    ImageRef,
    Message,
    PaymentOption,
    Profile,
    PurchaseRequest,
    money,
    parse_date,
    parse_datetime,
    split_pipe,
)


@dataclass
class Dataset:
    root: Path
    profiles: dict[str, Profile]
    events: list[FinancialEvent]
    requests: list[PurchaseRequest]
    payment_options: list[PaymentOption]
    messages: list[Message]
    images: list[ImageRef]
    exchange_rates: list[dict[str, str]]

    @classmethod
    def load(cls, root: Path) -> "Dataset":
        root = root.resolve()
        return cls(
            root=root,
            profiles=_load_profiles(root / "financial_profiles.csv"),
            events=_load_events(root / "financial_events.csv"),
            requests=_load_requests(root / "requests.csv"),
            payment_options=_load_options(root / "request_payment_options.csv"),
            messages=_load_messages(root / "messages.csv"),
            images=_load_images(root),
            exchange_rates=_read_rows(root / "exchange_rates.csv"),
        )

    def user_events(self, user_id: str) -> list[FinancialEvent]:
        return [e for e in self.events if e.user_id == user_id]

    def request_options(self, request_id: str) -> list[PaymentOption]:
        return [o for o in self.payment_options if o.request_id == request_id]

    def evidence_messages(self, request: PurchaseRequest) -> list[Message]:
        return [m for m in self.messages if m.user_id == request.user_id and (not m.request_id or m.request_id == request.request_id)]

    def evidence_images(self, request: PurchaseRequest) -> list[ImageRef]:
        return [i for i in self.images if i.user_id == request.user_id and (not i.request_id or i.request_id == request.request_id)]


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _load_profiles(path: Path) -> dict[str, Profile]:
    out: dict[str, Profile] = {}
    for r in _read_rows(path):
        max_months = int(r["max_installment_months"]) if r.get("max_installment_months") else None
        out[r["user_id"]] = Profile(
            user_id=r["user_id"],
            home_currency=r["home_currency"],
            current_available_balance=Decimal(r["current_available_balance"]),
            minimum_balance_to_keep=Decimal(r["minimum_balance_to_keep"]),
            financial_priorities=split_pipe(r.get("financial_priorities")),
            protected_categories=split_pipe(r.get("expense_categories_to_protect")),
            reducible_categories=split_pipe(r.get("expense_categories_user_is_willing_to_reduce")),
            stoppable_categories=split_pipe(r.get("expense_categories_user_is_willing_to_stop")),
            accepted_payment_methods=split_pipe(r.get("payment_methods_user_will_consider")),
            max_installment_months=max_months,
        )
    return out


def _load_events(path: Path) -> list[FinancialEvent]:
    out: list[FinancialEvent] = []
    for r in _read_rows(path):
        out.append(
            FinancialEvent(
                event_id=r["event_id"], user_id=r["user_id"], event_type=r["event_type"],
                description=r["description"], category=r["category"], direction=r["direction"],
                amount=money(r.get("amount")), currency=r["currency"],
                event_date=parse_date(r["event_date"]), settlement_date=parse_date(r["settlement_date"]),
                status=r["status"], linked_event_id=r.get("linked_event_id") or None,
                flexibility=r.get("flexibility") or "fixed",
                minimum_allowed_amount=money(r.get("minimum_allowed_amount")),
            )
        )
    return out


def _load_requests(path: Path) -> list[PurchaseRequest]:
    out: list[PurchaseRequest] = []
    for r in _read_rows(path):
        out.append(PurchaseRequest(
            request_id=r["request_id"], user_id=r["user_id"], request_date=parse_date(r["request_date"]),
            request_type=r["request_type"], requested_amount=Decimal(r["requested_amount"]),
            desired_completion_date=parse_date(r["desired_completion_date"]),
            allows_partial_payment=r["allows_partial_payment"].strip().lower() == "true",
            request_text=r["request_text"],
        ))
    return out


def _load_options(path: Path) -> list[PaymentOption]:
    out: list[PaymentOption] = []
    for r in _read_rows(path):
        out.append(PaymentOption(
            payment_option_id=r["payment_option_id"], request_id=r["request_id"], payment_method=r["payment_method"],
            payment_amount=Decimal(r["payment_amount"]), number_of_payments=int(r["number_of_payments"]),
            first_payment_date=parse_date(r["first_payment_date"]),
            payment_frequency_days=int(r["payment_frequency_days"]) if r.get("payment_frequency_days") else None,
            financing_fee=Decimal(r["financing_fee"]), total_payable_amount=Decimal(r["total_payable_amount"]),
        ))
    return out


def _load_messages(path: Path) -> list[Message]:
    out: list[Message] = []
    for r in _read_rows(path):
        out.append(Message(
            message_id=r["message_id"], user_id=r["user_id"], request_id=r.get("request_id") or None,
            related_event_id=r.get("related_event_id") or None, sent_at=parse_datetime(r["sent_at"]),
            source_type=r["source_type"], message_text=r["message_text"],
        ))
    return out


def _load_images(root: Path) -> list[ImageRef]:
    out: list[ImageRef] = []
    for r in _read_rows(root / "images.csv"):
        out.append(ImageRef(
            image_id=r["image_id"], user_id=r["user_id"], request_id=r.get("request_id") or None,
            related_event_id=r.get("related_event_id") or None,
            path=root / "media" / "images" / f"{r['image_id']}.png",
        ))
    return out
