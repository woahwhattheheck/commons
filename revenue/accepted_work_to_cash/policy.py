from __future__ import annotations

from datetime import datetime
from typing import Any

from .core import ACCEPTANCE_KINDS, parse_time


def latest(events: list[dict[str, Any]], kinds: set[str] | frozenset[str]) -> dict[str, Any] | None:
    found = [event for event in events if event["kind"] in kinds]
    return found[-1] if found else None


def latest_amount(events: list[dict[str, Any]], kind: str) -> int | None:
    found = [event for event in events if event["kind"] == kind and event["amount_cents"] is not None]
    return found[-1]["amount_cents"] if found else None


def target_amount(events: list[dict[str, Any]], advertised: int | None) -> tuple[int | None, str]:
    for kind in ("INVOICE_ISSUED", "PAYMENT_LINK_ISSUED", "AWARDED", "ACCEPTED", "CLAIM_SUBMITTED"):
        amount = latest_amount(events, kind)
        if amount is not None:
            return amount, kind
    if advertised is not None:
        return advertised, "ADVERTISED"
    return None, "UNKNOWN"


def same_second_amount_conflict(events: list[dict[str, Any]]) -> str | None:
    # Same-second amount disagreement must not be resolved by arbitrary event IDs.
    for kind in ("INVOICE_ISSUED", "PAYMENT_LINK_ISSUED", "AWARDED", "ACCEPTED", "CLAIM_SUBMITTED"):
        grouped: dict[str, set[int]] = {}
        for event in events:
            if event["kind"] == kind and event["amount_cents"] is not None:
                grouped.setdefault(event["observed_at"], set()).add(event["amount_cents"])
        for when, amounts in grouped.items():
            if len(amounts) > 1:
                return f"CONFLICTING_{kind}_AMOUNTS_AT_{when}"
    return None


def fresh(event: dict[str, Any] | None, evaluation_at: datetime, freshness_seconds: int) -> bool:
    if not event:
        return False
    observed = parse_time(event["observed_at"], "event.observed_at")
    age = (evaluation_at - observed).total_seconds()
    return 0 <= age <= freshness_seconds


def terminal_action(
    *,
    events: list[dict[str, Any]],
    evaluation_at: datetime,
    freshness_seconds: int,
    accepted: bool,
    delivered: bool,
    paid_total: int,
    target: int | None,
) -> tuple[str, int, list[str], dict[str, str] | None]:
    latest_dnr = latest(events, {"DNR"})
    latest_reply = latest(events, {"HUMAN_REPLY"})
    latest_rejected = latest(events, {"REJECTED", "CANCELED"})
    latest_accept = latest(events, ACCEPTANCE_KINDS)
    latest_claim_ready = latest(events, {"CLAIM_ROUTE_READY"})
    latest_claim = latest(events, {"CLAIM_SUBMITTED"})
    latest_invoice = latest(events, {"INVOICE_ISSUED"})
    latest_link = latest(events, {"PAYMENT_LINK_ISSUED"})
    latest_contact = latest(events, {"CONTACT_REQUIRED"})
    latest_muse = latest(events, {"MUSE_CLEAR"})
    latest_outbound = latest(events, {"OUTBOUND_SENT"})

    if latest_rejected and latest_accept and latest_rejected["observed_at"] == latest_accept["observed_at"]:
        return "HOLD_CONTRADICTION", 0, ["same-second accepted/rejected evidence conflict"], None
    if latest_rejected and (not latest_accept or latest_rejected["observed_at"] > latest_accept["observed_at"]):
        if paid_total:
            return "RECONCILE_CLOSED_WITH_PAYMENT", 98, ["terminal rejection/cancel follows acceptance but payment exists"], None
        return "CLOSED_NO_CASH", 0, ["terminal rejection/cancel is newer than acceptance"], None

    if paid_total:
        if target is None:
            return "RECONCILE_PAYMENT_TARGET", 100, ["provider-backed payment exists but settlement target is unknown"], None
        if paid_total < target:
            return "COLLECT_REMAINDER_REVIEW", 97, ["provider-backed partial payment"], None
        if paid_total == target:
            return "DONE_PAID", 0, ["provider-backed payment equals settlement target"], None
        return "RECONCILE_OVERPAYMENT", 99, ["provider-backed payment exceeds settlement target"], None

    if latest_dnr and (not latest_reply or latest_dnr["observed_at"] >= latest_reply["observed_at"]):
        return "DNR_WAIT", 5, ["current retained contact state is DNR without newer human reply"], None

    if latest_invoice or latest_link:
        return "COLLECTION_REVIEW", 94, ["accepted work has issued invoice/payment route but no provider-backed cash"], None
    if latest_claim:
        return "AWAIT_CLAIM_ADJUDICATION", 88, ["claim submitted; no provider-backed cash yet"], None
    if accepted and latest_claim_ready:
        if not fresh(latest_claim_ready, evaluation_at, freshness_seconds):
            return "HOLD_STALE_ROUTE", 20, ["claim route evidence is stale"], None
        return "OWNER_CLAIM_ACTION", 92, ["accepted work has a fresh retained claim route"], None

    if accepted and latest_contact:
        if not fresh(latest_contact, evaluation_at, freshness_seconds):
            return "HOLD_STALE_CONTACT", 20, ["contact-required evidence is stale"], None
        if latest_outbound and latest_outbound["observed_at"] >= latest_contact["observed_at"]:
            return "DNR_WAIT", 5, ["contact action already sent; wait for genuine event"], None
        muse_is_fresh = fresh(latest_muse, evaluation_at, freshness_seconds)
        same_scope = bool(
            latest_muse
            and latest_muse["route"] == latest_contact["route"]
            and latest_muse["purpose"] == latest_contact["purpose"]
        )
        packet = {"route": latest_contact["route"], "purpose": latest_contact["purpose"]}
        if muse_is_fresh and same_scope:
            return "OWNER_PROVIDER_PREFLIGHT", 90, ["fresh Muse-clear evidence matches exact route/purpose; provider preflight still required"], packet
        return "MUSE_REQUIRED", 89, ["accepted work needs contact; exact route/purpose requires separate Muse arbitration"], packet

    if accepted:
        return "ROUTE_TO_CASH_REQUIRED", 80, ["acceptance/merge/award exists but no claim/invoice/contact route is retained"], None
    if delivered:
        return "ACCEPTANCE_EVIDENCE_REQUIRED", 50, ["delivery evidence exists but no acceptance/merge/award evidence"], None
    return "HOLD_NO_ACCEPTED_WORK", 0, ["no accepted or delivered work evidence"], None
