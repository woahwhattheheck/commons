#!/usr/bin/env python3
"""Deterministic paid-fulfillment release authority.

The gate consumes normalized, read-only snapshots from payment, operations,
order, and fulfillment systems. It never calls those systems or performs a
release. A RELEASE decision is a machine-checkable statement that the supplied
snapshot proves the order is fully paid, operationally ready, not cancelled or
reversed, and not already released.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable

SCHEMA_VERSION = 1
MAX_EVENTS = 10_000
MAX_AMOUNT_MINOR = 10**15
MAX_FRESHNESS_SECONDS = 7 * 24 * 60 * 60
REQUIRED_SOURCES = (
    "PAYMENT_PROVIDER",
    "OPERATIONS_SYSTEM",
    "ORDER_SYSTEM",
    "FULFILLMENT_SYSTEM",
)
SOURCE_FOR_KIND = {
    "PAYMENT_CAPTURED": "PAYMENT_PROVIDER",
    "PAYMENT_REFUNDED": "PAYMENT_PROVIDER",
    "PAYMENT_CHARGEBACK": "PAYMENT_PROVIDER",
    "FULFILLMENT_READY": "OPERATIONS_SYSTEM",
    "FULFILLMENT_NOT_READY": "OPERATIONS_SYSTEM",
    "ORDER_CANCELLED": "ORDER_SYSTEM",
    "FULFILLMENT_RELEASED": "FULFILLMENT_SYSTEM",
}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class GateInputError(ValueError):
    """Raised when the input cannot be interpreted unambiguously."""


@dataclass(frozen=True)
class SourceState:
    complete: bool
    observed_at: datetime


@dataclass(frozen=True)
class Event:
    event_id: str
    kind: str
    source: str
    order_id: str
    occurred_at: datetime
    data: dict[str, Any]


def _no_duplicate_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GateInputError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GateInputError(f"cannot read input: {exc}") from exc
    try:
        value = json.loads(text, object_pairs_hook=_no_duplicate_object_keys)
    except (json.JSONDecodeError, GateInputError) as exc:
        raise GateInputError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise GateInputError("top-level JSON value must be an object")
    return value


def _require_exact_keys(obj: dict[str, Any], expected: set[str], where: str) -> None:
    actual = set(obj)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        parts: list[str] = []
        if missing:
            parts.append(f"missing={','.join(missing)}")
        if extra:
            parts.append(f"extra={','.join(extra)}")
        raise GateInputError(f"{where} keys mismatch ({'; '.join(parts)})")


def _require_id(value: Any, where: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise GateInputError(f"{where} must be a 1-128 character stable identifier")
    return value


def _require_currency(value: Any, where: str) -> str:
    if not isinstance(value, str) or not CURRENCY_RE.fullmatch(value):
        raise GateInputError(f"{where} must be a three-letter uppercase currency")
    return value


def _require_int(value: Any, where: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not (minimum <= value <= maximum):
        raise GateInputError(f"{where} must be an integer in [{minimum}, {maximum}]")
    return value


def _parse_time(value: Any, where: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise GateInputError(f"{where} must be an RFC3339 timestamp")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise GateInputError(f"{where} must be an RFC3339 timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise GateInputError(f"{where} must include a timezone")
    return dt.astimezone(timezone.utc)


def _format_time(dt: datetime) -> str:
    value = dt.astimezone(timezone.utc).isoformat(timespec="microseconds")
    return value.replace("+00:00", "Z")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _normalize_source_states(raw: Any, snapshot_at: datetime, freshness: int) -> tuple[dict[str, SourceState], list[str]]:
    if not isinstance(raw, dict):
        raise GateInputError("sources must be an object")
    _require_exact_keys(raw, set(REQUIRED_SOURCES), "sources")
    result: dict[str, SourceState] = {}
    blockers: list[str] = []
    for source in REQUIRED_SOURCES:
        item = raw[source]
        if not isinstance(item, dict):
            raise GateInputError(f"sources.{source} must be an object")
        _require_exact_keys(item, {"complete", "observed_at"}, f"sources.{source}")
        if not isinstance(item["complete"], bool):
            raise GateInputError(f"sources.{source}.complete must be boolean")
        observed_at = _parse_time(item["observed_at"], f"sources.{source}.observed_at")
        if observed_at > snapshot_at:
            raise GateInputError(f"sources.{source}.observed_at is after snapshot_at")
        age = int((snapshot_at - observed_at).total_seconds())
        if not item["complete"]:
            blockers.append(f"SOURCE_INCOMPLETE:{source}")
        if age > freshness:
            blockers.append(f"SOURCE_STALE:{source}")
        result[source] = SourceState(item["complete"], observed_at)
    return result, blockers


def _event_expected_keys(kind: str) -> set[str]:
    common = {"event_id", "kind", "source", "order_id", "occurred_at"}
    if kind == "PAYMENT_CAPTURED":
        return common | {"payment_id", "amount_minor", "currency"}
    if kind == "PAYMENT_REFUNDED":
        return common | {"payment_id", "refund_id", "amount_minor", "currency"}
    if kind == "PAYMENT_CHARGEBACK":
        return common | {"payment_id", "chargeback_id"}
    if kind == "ORDER_CANCELLED":
        return common | {"cancellation_id"}
    if kind == "FULFILLMENT_RELEASED":
        return common | {"release_id"}
    if kind in {"FULFILLMENT_READY", "FULFILLMENT_NOT_READY"}:
        return common
    raise GateInputError(f"unsupported event kind: {kind}")


def _normalize_event(raw: Any, index: int, order_id: str, sources: dict[str, SourceState]) -> Event:
    where = f"events[{index}]"
    if not isinstance(raw, dict):
        raise GateInputError(f"{where} must be an object")
    kind = raw.get("kind")
    if not isinstance(kind, str) or kind not in SOURCE_FOR_KIND:
        raise GateInputError(f"{where}.kind is unsupported")
    _require_exact_keys(raw, _event_expected_keys(kind), where)
    event_id = _require_id(raw["event_id"], f"{where}.event_id")
    source = raw["source"]
    if source != SOURCE_FOR_KIND[kind]:
        raise GateInputError(f"{where}.source must be {SOURCE_FOR_KIND[kind]} for {kind}")
    event_order_id = _require_id(raw["order_id"], f"{where}.order_id")
    if event_order_id != order_id:
        raise GateInputError(f"{where}.order_id does not match order.order_id")
    occurred_at = _parse_time(raw["occurred_at"], f"{where}.occurred_at")
    if occurred_at > sources[source].observed_at:
        raise GateInputError(f"{where}.occurred_at is newer than its source snapshot")

    normalized = dict(raw)
    normalized["occurred_at"] = _format_time(occurred_at)
    for key in ("payment_id", "refund_id", "chargeback_id", "cancellation_id", "release_id"):
        if key in normalized:
            normalized[key] = _require_id(normalized[key], f"{where}.{key}")
    if "currency" in normalized:
        normalized["currency"] = _require_currency(normalized["currency"], f"{where}.currency")
    if "amount_minor" in normalized:
        normalized["amount_minor"] = _require_int(
            normalized["amount_minor"], f"{where}.amount_minor", minimum=1, maximum=MAX_AMOUNT_MINOR
        )
    return Event(event_id, kind, source, event_order_id, occurred_at, normalized)


def _dedupe_events(events: Iterable[Event]) -> tuple[list[Event], int]:
    by_id: dict[str, Event] = {}
    duplicates = 0
    for event in events:
        prior = by_id.get(event.event_id)
        if prior is None:
            by_id[event.event_id] = event
            continue
        if prior.data != event.data:
            raise GateInputError(f"event_id reused with different content: {event.event_id}")
        duplicates += 1
    ordered = sorted(by_id.values(), key=lambda event: (event.occurred_at, event.event_id))
    return ordered, duplicates


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    _require_exact_keys(
        payload,
        {"schema_version", "decision_id", "snapshot_at", "freshness_window_seconds", "order", "sources", "events"},
        "top-level",
    )
    if payload["schema_version"] != SCHEMA_VERSION:
        raise GateInputError(f"schema_version must be {SCHEMA_VERSION}")
    decision_id = _require_id(payload["decision_id"], "decision_id")
    snapshot_at = _parse_time(payload["snapshot_at"], "snapshot_at")
    freshness = _require_int(
        payload["freshness_window_seconds"],
        "freshness_window_seconds",
        minimum=1,
        maximum=MAX_FRESHNESS_SECONDS,
    )

    order = payload["order"]
    if not isinstance(order, dict):
        raise GateInputError("order must be an object")
    _require_exact_keys(order, {"order_id", "currency", "required_amount_minor"}, "order")
    order_id = _require_id(order["order_id"], "order.order_id")
    currency = _require_currency(order["currency"], "order.currency")
    required_amount = _require_int(
        order["required_amount_minor"], "order.required_amount_minor", minimum=1, maximum=MAX_AMOUNT_MINOR
    )

    sources, source_blockers = _normalize_source_states(payload["sources"], snapshot_at, freshness)
    raw_events = payload["events"]
    if not isinstance(raw_events, list):
        raise GateInputError("events must be an array")
    if len(raw_events) > MAX_EVENTS:
        raise GateInputError(f"events exceeds maximum of {MAX_EVENTS}")
    normalized = [_normalize_event(item, i, order_id, sources) for i, item in enumerate(raw_events)]
    events, duplicate_count = _dedupe_events(normalized)

    reasons: list[str] = list(source_blockers)
    exception_reasons: list[str] = []
    captures: dict[str, dict[str, Any]] = {}
    refunds: dict[str, dict[str, Any]] = {}
    chargebacks: dict[str, str] = {}
    cancellation_events: list[Event] = []
    readiness_events: list[Event] = []
    release_events: list[Event] = []

    for event in events:
        data = event.data
        if event.kind == "PAYMENT_CAPTURED":
            if data["currency"] != currency:
                exception_reasons.append(f"PAYMENT_CURRENCY_MISMATCH:{event.event_id}")
                continue
            pid = data["payment_id"]
            candidate = {"amount_minor": data["amount_minor"], "currency": data["currency"], "event_id": event.event_id}
            prior = captures.get(pid)
            if prior and (prior["amount_minor"], prior["currency"]) != (candidate["amount_minor"], candidate["currency"]):
                exception_reasons.append(f"PAYMENT_ID_CONFLICT:{pid}")
            elif not prior:
                captures[pid] = candidate
        elif event.kind == "PAYMENT_REFUNDED":
            if data["currency"] != currency:
                exception_reasons.append(f"REFUND_CURRENCY_MISMATCH:{event.event_id}")
                continue
            rid = data["refund_id"]
            candidate = {
                "payment_id": data["payment_id"],
                "amount_minor": data["amount_minor"],
                "currency": data["currency"],
                "event_id": event.event_id,
                "occurred_at": event.occurred_at,
            }
            prior = refunds.get(rid)
            if prior and (prior["payment_id"], prior["amount_minor"], prior["currency"]) != (
                candidate["payment_id"], candidate["amount_minor"], candidate["currency"]
            ):
                exception_reasons.append(f"REFUND_ID_CONFLICT:{rid}")
            elif not prior:
                refunds[rid] = candidate
        elif event.kind == "PAYMENT_CHARGEBACK":
            cid = data["chargeback_id"]
            pid = data["payment_id"]
            prior = chargebacks.get(cid)
            if prior and prior != pid:
                exception_reasons.append(f"CHARGEBACK_ID_CONFLICT:{cid}")
            else:
                chargebacks[cid] = pid
        elif event.kind == "ORDER_CANCELLED":
            cancellation_events.append(event)
        elif event.kind in {"FULFILLMENT_READY", "FULFILLMENT_NOT_READY"}:
            readiness_events.append(event)
        elif event.kind == "FULFILLMENT_RELEASED":
            release_events.append(event)

    for refund_id, refund in refunds.items():
        capture = captures.get(refund["payment_id"])
        if capture is None:
            exception_reasons.append(f"REFUND_WITHOUT_CAPTURE:{refund_id}")
    for chargeback_id, payment_id in chargebacks.items():
        if payment_id not in captures:
            exception_reasons.append(f"CHARGEBACK_WITHOUT_CAPTURE:{chargeback_id}")

    refund_totals: dict[str, int] = {}
    for refund in refunds.values():
        pid = refund["payment_id"]
        refund_totals[pid] = refund_totals.get(pid, 0) + refund["amount_minor"]
    for pid, total in refund_totals.items():
        capture = captures.get(pid)
        if capture and total > capture["amount_minor"]:
            exception_reasons.append(f"REFUND_EXCEEDS_CAPTURE:{pid}")

    captured_total = sum(item["amount_minor"] for item in captures.values())
    refunded_total = sum(item["amount_minor"] for item in refunds.values())
    net_paid = captured_total - refunded_total

    readiness_state = "UNKNOWN"
    readiness_event_id: str | None = None
    readiness_at: datetime | None = None
    if readiness_events:
        latest_time = max(event.occurred_at for event in readiness_events)
        latest = [event for event in readiness_events if event.occurred_at == latest_time]
        latest_kinds = {event.kind for event in latest}
        if len(latest_kinds) > 1:
            exception_reasons.append("READINESS_CONFLICT_AT_SAME_TIME")
        else:
            chosen = sorted(latest, key=lambda event: event.event_id)[-1]
            readiness_state = "READY" if chosen.kind == "FULFILLMENT_READY" else "NOT_READY"
            readiness_event_id = chosen.event_id
            readiness_at = chosen.occurred_at

    release_ids = sorted({event.data["release_id"] for event in release_events})
    release_at: datetime | None = None
    if len(release_ids) > 1:
        exception_reasons.append("MULTIPLE_RELEASE_IDS")
    elif release_events:
        release_at = min(event.occurred_at for event in release_events)

    if refunds:
        exception_reasons.append("REFUND_PRESENT")
    if chargebacks:
        exception_reasons.append("CHARGEBACK_PRESENT")
    if cancellation_events:
        exception_reasons.append("ORDER_CANCELLED")

    if release_at is not None:
        post_release_reversal = any(refund["occurred_at"] > release_at for refund in refunds.values())
        post_release_reversal = post_release_reversal or any(
            event.occurred_at > release_at for event in cancellation_events
        )
        post_release_reversal = post_release_reversal or any(
            event.kind == "FULFILLMENT_NOT_READY" and event.occurred_at > release_at for event in readiness_events
        )
        if chargebacks:
            post_release_reversal = post_release_reversal or any(
                event.kind == "PAYMENT_CHARGEBACK" and event.occurred_at > release_at for event in events
            )
        if post_release_reversal:
            exception_reasons.append("POST_RELEASE_REVERSAL")

    if not exception_reasons:
        if net_paid < required_amount:
            reasons.append("PAYMENT_INSUFFICIENT")
        if readiness_state == "UNKNOWN":
            reasons.append("FULFILLMENT_READINESS_MISSING")
        elif readiness_state != "READY":
            reasons.append("FULFILLMENT_NOT_READY")

    exception_reasons = sorted(set(exception_reasons))
    reasons = sorted(set(reasons))
    if exception_reasons:
        decision = "EXCEPTION"
        release_authorized = False
        final_reasons = exception_reasons + reasons
    elif release_ids:
        decision = "ALREADY_RELEASED"
        release_authorized = False
        final_reasons = reasons or ["RELEASE_ALREADY_RECORDED"]
    elif reasons:
        decision = "HOLD"
        release_authorized = False
        final_reasons = reasons
    else:
        decision = "RELEASE"
        release_authorized = True
        final_reasons = ["FULL_PAYMENT_AND_READINESS_PROVEN"]

    normalized_events = [event.data for event in events]
    source_receipt = {
        source: {
            "complete": state.complete,
            "observed_at": _format_time(state.observed_at),
            "age_seconds": int((snapshot_at - state.observed_at).total_seconds()),
        }
        for source, state in sorted(sources.items())
    }
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "decision_id": decision_id,
        "order_id": order_id,
        "snapshot_at": _format_time(snapshot_at),
        "decision": decision,
        "release_authorized": release_authorized,
        "reasons": final_reasons,
        "money": {
            "currency": currency,
            "required_amount_minor": required_amount,
            "captured_amount_minor": captured_total,
            "refunded_amount_minor": refunded_total,
            "net_paid_amount_minor": net_paid,
            "payment_ids": sorted(captures),
        },
        "readiness": {
            "state": readiness_state,
            "event_id": readiness_event_id,
            "occurred_at": _format_time(readiness_at) if readiness_at else None,
        },
        "release_history": {
            "release_ids": release_ids,
            "first_release_at": _format_time(release_at) if release_at else None,
        },
        "sources": source_receipt,
        "events": {
            "input_count": len(raw_events),
            "normalized_count": len(normalized_events),
            "deduplicated_count": duplicate_count,
            "sha256": _digest(normalized_events),
        },
    }
    receipt["receipt_sha256"] = _digest(receipt)
    return receipt


def _write_atomic(output: Path, receipt: dict[str, Any], input_path: Path | None = None) -> None:
    if output.exists() and output.is_symlink():
        raise GateInputError("output path must not be a symlink")
    output.parent.mkdir(parents=True, exist_ok=True)
    if input_path is not None:
        try:
            if output.exists() and os.path.samefile(input_path, output):
                raise GateInputError("input and output must be different files")
            if not output.exists() and input_path.resolve() == output.resolve():
                raise GateInputError("input and output must be different files")
        except FileNotFoundError:
            pass
    encoded = json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=str(output.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, output)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate a paid-fulfillment release snapshot")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, help="atomically write the receipt instead of stdout")
    args = parser.parse_args(argv)
    try:
        payload = load_json(args.input)
        receipt = evaluate(payload)
        if args.output:
            _write_atomic(args.output, receipt, args.input)
        else:
            print(json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False))
    except GateInputError as exc:
        parser.exit(2, f"paid-fulfillment-release-gate: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
