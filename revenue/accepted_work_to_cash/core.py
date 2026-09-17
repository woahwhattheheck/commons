from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

SCHEMA = "TJL_ACCEPTED_WORK_TO_CASH_V1"
BUNDLE_SCHEMA = "TJL_ACCEPTED_WORK_TO_CASH_BUNDLE_V1"
MAX_BYTES = 4_000_000
MAX_ITEMS = 5_000
MAX_EVENTS_PER_ITEM = 2_000

AUTHORITY = {
    "external_send": False,
    "muse_selection": False,
    "provider_mutation": False,
    "invoice_creation": False,
    "payment_movement": False,
    "receivable_establishment": False,
    "accounting_entry": False,
    "revenue_recognition": False,
}

LANES = frozenset({"BOUNTY", "CONTRACT", "SUBCONTRACT", "COMPETITION", "PLATFORM", "PRODUCT", "OTHER"})
SOURCE_CLASSES = frozenset({
    "GITHUB", "BUYER_MESSAGE", "SPONSOR_MESSAGE", "PLATFORM_RECEIPT",
    "PROVIDER_RECEIPT", "PAYMENT_PROVIDER", "SLACK", "INTERNAL_RETAINED",
})
KINDS = frozenset({
    "DELIVERED", "MERGED", "ACCEPTED", "AWARDED",
    "CLAIM_ROUTE_READY", "CLAIM_SUBMITTED", "INVOICE_ISSUED", "PAYMENT_LINK_ISSUED",
    "PAYMENT_RECEIVED", "CONTACT_REQUIRED", "MUSE_CLEAR", "OUTBOUND_SENT",
    "HUMAN_REPLY", "DNR", "REJECTED", "CANCELED",
})
AMOUNT_KINDS = frozenset({
    "ACCEPTED", "AWARDED", "CLAIM_SUBMITTED", "INVOICE_ISSUED",
    "PAYMENT_LINK_ISSUED", "PAYMENT_RECEIVED",
})
CONTACT_KINDS = frozenset({"CONTACT_REQUIRED", "MUSE_CLEAR", "OUTBOUND_SENT"})
ACCEPTANCE_KINDS = frozenset({"MERGED", "ACCEPTED", "AWARDED"})


class ReconcileError(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ReconcileError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_json_loads(text: str) -> Any:
    def reject_constant(value: str) -> None:
        raise ReconcileError(f"non-finite JSON number: {value}")
    try:
        return json.loads(text, object_pairs_hook=_strict_object, parse_constant=reject_constant)
    except ReconcileError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ReconcileError(f"invalid JSON: {exc}") from exc


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ReconcileError(f"value is not canonical JSON: {exc}") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def exact_dict(value: Any, keys: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ReconcileError(f"{where}: exact object required")
    missing = keys - set(value)
    extra = set(value) - keys
    if missing or extra:
        raise ReconcileError(
            f"{where}: exact keys required; missing={sorted(missing)} extra={sorted(extra)}"
        )
    return value


def text(value: Any, where: str, maximum: int) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise ReconcileError(f"{where}: bounded nonempty string required")
    if any(ord(ch) < 32 for ch in value):
        raise ReconcileError(f"{where}: control characters forbidden")
    return value


def optional_text(value: Any, where: str, maximum: int) -> str | None:
    if value is None:
        return None
    return text(value, where, maximum)


def money(value: Any, where: str, optional: bool = False) -> int | None:
    if optional and value is None:
        return None
    if type(value) is not int or value < 0 or value > 10**15:
        raise ReconcileError(f"{where}: bounded nonnegative integer cents required")
    return value


def positive_int(value: Any, where: str, maximum: int) -> int:
    if type(value) is not int or value <= 0 or value > maximum:
        raise ReconcileError(f"{where}: bounded positive integer required")
    return value


def sha256_text(value: Any, where: str) -> str:
    value = text(value, where, 64)
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ReconcileError(f"{where}: lowercase sha256 required")
    return value


def parse_time(value: Any, where: str) -> datetime:
    if type(value) is not str or not value.endswith("Z") or "." in value:
        raise ReconcileError(f"{where}: whole-second RFC3339 UTC Z required")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ReconcileError(f"{where}: invalid timestamp") from exc


def validate_event(raw: Any, item_id: str, evaluation_at: datetime) -> dict[str, Any]:
    keys = {"id", "kind", "observed_at", "source_class", "ref", "sha256", "amount_cents", "route", "purpose"}
    event = exact_dict(raw, keys, f"{item_id}.event")
    event_id = text(event["id"], f"{item_id}.event.id", 120)
    kind = text(event["kind"], f"{event_id}.kind", 40)
    if kind not in KINDS:
        raise ReconcileError(f"{event_id}: unsupported event kind")
    observed = parse_time(event["observed_at"], f"{event_id}.observed_at")
    if observed > evaluation_at:
        raise ReconcileError(f"{event_id}: future evidence")
    source_class = text(event["source_class"], f"{event_id}.source_class", 40)
    if source_class not in SOURCE_CLASSES:
        raise ReconcileError(f"{event_id}: unsupported source class")
    ref = text(event["ref"], f"{event_id}.ref", 512)
    sha = sha256_text(event["sha256"], f"{event_id}.sha256")
    amount = money(event["amount_cents"], f"{event_id}.amount_cents", optional=True)
    route = optional_text(event["route"], f"{event_id}.route", 320)
    purpose = optional_text(event["purpose"], f"{event_id}.purpose", 320)

    if amount is not None and kind not in AMOUNT_KINDS:
        raise ReconcileError(f"{event_id}: amount not allowed for {kind}")
    if kind == "PAYMENT_RECEIVED":
        if amount is None or amount <= 0:
            raise ReconcileError(f"{event_id}: positive payment amount required")
        if source_class != "PAYMENT_PROVIDER":
            raise ReconcileError(f"{event_id}: PAYMENT_RECEIVED requires PAYMENT_PROVIDER evidence")
    if kind == "MERGED" and source_class != "GITHUB":
        raise ReconcileError(f"{event_id}: MERGED requires GITHUB evidence")
    if kind == "ACCEPTED" and source_class not in {"BUYER_MESSAGE", "SPONSOR_MESSAGE", "PLATFORM_RECEIPT"}:
        raise ReconcileError(f"{event_id}: ACCEPTED requires buyer/sponsor/platform evidence")
    if kind == "AWARDED" and source_class not in {"BUYER_MESSAGE", "SPONSOR_MESSAGE", "PLATFORM_RECEIPT"}:
        raise ReconcileError(f"{event_id}: AWARDED requires buyer/sponsor/platform evidence")
    if kind in {"INVOICE_ISSUED", "PAYMENT_LINK_ISSUED", "CLAIM_SUBMITTED"} and source_class not in {"PROVIDER_RECEIPT", "PLATFORM_RECEIPT"}:
        raise ReconcileError(f"{event_id}: {kind} requires provider/platform receipt evidence")
    if kind in CONTACT_KINDS:
        if route is None or purpose is None:
            raise ReconcileError(f"{event_id}: {kind} requires exact route and purpose")
    elif route is not None or purpose is not None:
        raise ReconcileError(f"{event_id}: route/purpose only allowed on contact-control events")

    return {
        "id": event_id,
        "kind": kind,
        "observed_at": observed.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_class": source_class,
        "ref": ref,
        "sha256": sha,
        "amount_cents": amount,
        "route": route,
        "purpose": purpose,
    }
