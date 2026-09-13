from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping

from .common import (
    MAX_ITEMS,
    MAX_SAFE_CENTS,
    SCHEMA_VERSION,
    DeskError,
    _check_unique,
    _currency,
    _date,
    _digest,
    _identifier,
    _integer,
    _list,
    _object,
    _parse_evidence,
    _text,
    _timestamp,
)


def _parse_baseline(value: Any) -> dict[str, Any]:
    row = _object(
        value,
        path="$.baseline",
        required=(
            "schema_version", "baseline_id", "baseline_version", "currency", "accepted_at",
            "scope_digest", "line_items", "discount_cents", "tax_cents", "subtotal_cents",
            "total_cents", "schedule", "evidence_refs",
        ),
    )
    if _integer(row["schema_version"], path="$.baseline.schema_version", minimum=1, maximum=1) != SCHEMA_VERSION:
        raise DeskError("UNSUPPORTED_SCHEMA_VERSION", "$.baseline")
    items_raw = _list(row["line_items"], path="$.baseline.line_items", maximum=MAX_ITEMS, allow_empty=False)
    items: list[dict[str, Any]] = []
    for index, raw in enumerate(items_raw):
        path = f"$.baseline.line_items[{index}]"
        item = _object(raw, path=path, required=("item_id", "description", "quantity", "unit_price_cents"))
        items.append({
            "item_id": _identifier(item["item_id"], path=f"{path}.item_id"),
            "description": _text(item["description"], path=f"{path}.description", maximum=240),
            "quantity": _integer(item["quantity"], path=f"{path}.quantity", minimum=1, maximum=1_000_000),
            "unit_price_cents": _integer(item["unit_price_cents"], path=f"{path}.unit_price_cents", minimum=0, maximum=MAX_SAFE_CENTS),
        })
    _check_unique([item["item_id"] for item in items], code="DUPLICATE_ITEM_ID", path="$.baseline.line_items")
    computed_subtotal = sum(item["quantity"] * item["unit_price_cents"] for item in items)
    if computed_subtotal > MAX_SAFE_CENTS:
        raise DeskError("MONEY_OVERFLOW", "$.baseline.subtotal_cents")
    subtotal = _integer(row["subtotal_cents"], path="$.baseline.subtotal_cents", minimum=0, maximum=MAX_SAFE_CENTS)
    discount = _integer(row["discount_cents"], path="$.baseline.discount_cents", minimum=0, maximum=MAX_SAFE_CENTS)
    tax = _integer(row["tax_cents"], path="$.baseline.tax_cents", minimum=0, maximum=MAX_SAFE_CENTS)
    total = _integer(row["total_cents"], path="$.baseline.total_cents", minimum=0, maximum=MAX_SAFE_CENTS)
    if subtotal != computed_subtotal:
        raise DeskError("BASELINE_SUBTOTAL_MISMATCH")
    if discount > subtotal or subtotal - discount + tax != total:
        raise DeskError("BASELINE_TOTAL_MISMATCH")

    schedule = _object(row["schedule"], path="$.baseline.schedule", required=("start_date", "end_date", "milestones"))
    start = _date(schedule["start_date"], path="$.baseline.schedule.start_date")
    end = _date(schedule["end_date"], path="$.baseline.schedule.end_date")
    if end < start:
        raise DeskError("INVALID_BASELINE_SCHEDULE")
    milestones_raw = _list(schedule["milestones"], path="$.baseline.schedule.milestones", maximum=MAX_ITEMS, allow_empty=False)
    milestones: list[dict[str, Any]] = []
    for index, raw in enumerate(milestones_raw):
        path = f"$.baseline.schedule.milestones[{index}]"
        milestone = _object(raw, path=path, required=("milestone_id", "due_date", "amount_cents"))
        due = _date(milestone["due_date"], path=f"{path}.due_date")
        if due < start or due > end:
            raise DeskError("BASELINE_MILESTONE_OUTSIDE_SCHEDULE", path)
        milestones.append({
            "milestone_id": _identifier(milestone["milestone_id"], path=f"{path}.milestone_id"),
            "due_date": due.isoformat(),
            "amount_cents": _integer(milestone["amount_cents"], path=f"{path}.amount_cents", minimum=0, maximum=MAX_SAFE_CENTS),
        })
    _check_unique([item["milestone_id"] for item in milestones], code="DUPLICATE_MILESTONE_ID", path="$.baseline.schedule.milestones")
    if sum(item["amount_cents"] for item in milestones) != total:
        raise DeskError("BASELINE_MILESTONE_TOTAL_MISMATCH")
    evidence = _parse_evidence(row["evidence_refs"], path="$.baseline.evidence_refs")
    if not any(item["kind"] == "acceptance" for item in evidence):
        raise DeskError("BASELINE_ACCEPTANCE_EVIDENCE_REQUIRED")
    return {
        "schema_version": SCHEMA_VERSION,
        "baseline_id": _identifier(row["baseline_id"], path="$.baseline.baseline_id"),
        "baseline_version": _integer(row["baseline_version"], path="$.baseline.baseline_version", minimum=1, maximum=1_000_000),
        "currency": _currency(row["currency"], path="$.baseline.currency"),
        "accepted_at": _timestamp(row["accepted_at"], path="$.baseline.accepted_at").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope_digest": _digest(row["scope_digest"], path="$.baseline.scope_digest"),
        "line_items": items,
        "discount_cents": discount,
        "tax_cents": tax,
        "subtotal_cents": subtotal,
        "total_cents": total,
        "schedule": {"start_date": start.isoformat(), "end_date": end.isoformat(), "milestones": milestones},
        "evidence_refs": evidence,
    }


def _parse_change(value: Any, baseline: Mapping[str, Any], expected_baseline_sha256: str, evaluation: datetime) -> dict[str, Any]:
    row = _object(
        value,
        path="$.change",
        required=(
            "schema_version", "change_id", "change_version", "supersedes_change_sha256", "baseline_id", "baseline_version",
            "baseline_sha256", "currency", "created_at", "expires_at", "summary", "scope_delta_digest",
            "line_items", "discount_delta_cents", "tax_delta_cents", "subtotal_delta_cents",
            "total_delta_cents", "schedule_delta_days", "updated_end_date", "milestones", "evidence_refs",
        ),
    )
    if _integer(row["schema_version"], path="$.change.schema_version", minimum=1, maximum=1) != SCHEMA_VERSION:
        raise DeskError("UNSUPPORTED_SCHEMA_VERSION", "$.change")
    change_version = _integer(row["change_version"], path="$.change.change_version", minimum=1, maximum=1_000_000)
    supersedes = row["supersedes_change_sha256"]
    if change_version == 1:
        if supersedes is not None:
            raise DeskError("UNEXPECTED_SUPERSESSION_COMMITMENT")
    else:
        if supersedes is None:
            raise DeskError("SUPERSESSION_COMMITMENT_REQUIRED")
        supersedes = _digest(supersedes, path="$.change.supersedes_change_sha256")
    baseline_hash = _digest(row["baseline_sha256"], path="$.change.baseline_sha256")
    if baseline_hash != expected_baseline_sha256:
        raise DeskError("BASELINE_COMMITMENT_MISMATCH")
    baseline_id = _identifier(row["baseline_id"], path="$.change.baseline_id")
    baseline_version = _integer(row["baseline_version"], path="$.change.baseline_version", minimum=1, maximum=1_000_000)
    if baseline_id != baseline["baseline_id"] or baseline_version != baseline["baseline_version"]:
        raise DeskError("BASELINE_IDENTITY_MISMATCH")
    currency = _currency(row["currency"], path="$.change.currency")
    if currency != baseline["currency"]:
        raise DeskError("CURRENCY_MISMATCH")
    created = _timestamp(row["created_at"], path="$.change.created_at")
    expires = _timestamp(row["expires_at"], path="$.change.expires_at")
    accepted = _timestamp(baseline["accepted_at"], path="$.baseline.accepted_at")
    if created < accepted or created > evaluation:
        raise DeskError("INVALID_CHANGE_CREATION_TIME")
    if expires <= created or expires - created > timedelta(days=366):
        raise DeskError("INVALID_CHANGE_EXPIRY")
    if evaluation > expires:
        raise DeskError("CHANGE_EXPIRED")

    items_raw = _list(row["line_items"], path="$.change.line_items", maximum=MAX_ITEMS, allow_empty=True)
    items: list[dict[str, Any]] = []
    for index, raw in enumerate(items_raw):
        path = f"$.change.line_items[{index}]"
        item = _object(raw, path=path, required=("item_id", "description", "quantity", "unit_delta_cents"))
        items.append({
            "item_id": _identifier(item["item_id"], path=f"{path}.item_id"),
            "description": _text(item["description"], path=f"{path}.description", maximum=240),
            "quantity": _integer(item["quantity"], path=f"{path}.quantity", minimum=1, maximum=1_000_000),
            "unit_delta_cents": _integer(item["unit_delta_cents"], path=f"{path}.unit_delta_cents", minimum=-MAX_SAFE_CENTS, maximum=MAX_SAFE_CENTS),
        })
    _check_unique([item["item_id"] for item in items], code="DUPLICATE_ITEM_ID", path="$.change.line_items")
    computed_subtotal = sum(item["quantity"] * item["unit_delta_cents"] for item in items)
    if abs(computed_subtotal) > MAX_SAFE_CENTS:
        raise DeskError("MONEY_OVERFLOW", "$.change.subtotal_delta_cents")
    subtotal = _integer(row["subtotal_delta_cents"], path="$.change.subtotal_delta_cents", minimum=-MAX_SAFE_CENTS, maximum=MAX_SAFE_CENTS)
    discount = _integer(row["discount_delta_cents"], path="$.change.discount_delta_cents", minimum=-MAX_SAFE_CENTS, maximum=MAX_SAFE_CENTS)
    tax = _integer(row["tax_delta_cents"], path="$.change.tax_delta_cents", minimum=-MAX_SAFE_CENTS, maximum=MAX_SAFE_CENTS)
    total = _integer(row["total_delta_cents"], path="$.change.total_delta_cents", minimum=-MAX_SAFE_CENTS, maximum=MAX_SAFE_CENTS)
    if subtotal != computed_subtotal:
        raise DeskError("CHANGE_SUBTOTAL_MISMATCH")
    if subtotal - discount + tax != total:
        raise DeskError("CHANGE_TOTAL_MISMATCH")
    updated_total = baseline["total_cents"] + total
    if updated_total < 0 or updated_total > MAX_SAFE_CENTS:
        raise DeskError("UPDATED_TOTAL_OUT_OF_RANGE")

    delta_days = _integer(row["schedule_delta_days"], path="$.change.schedule_delta_days", minimum=-365, maximum=365)
    baseline_end = _date(baseline["schedule"]["end_date"], path="$.baseline.schedule.end_date")
    updated_end = _date(row["updated_end_date"], path="$.change.updated_end_date")
    if updated_end != baseline_end + timedelta(days=delta_days):
        raise DeskError("UPDATED_END_DATE_MISMATCH")
    if updated_end < _date(baseline["schedule"]["start_date"], path="$.baseline.schedule.start_date"):
        raise DeskError("UPDATED_SCHEDULE_BEFORE_START")

    milestones_raw = _list(row["milestones"], path="$.change.milestones", maximum=MAX_ITEMS, allow_empty=True)
    milestones: list[dict[str, Any]] = []
    for index, raw in enumerate(milestones_raw):
        path = f"$.change.milestones[{index}]"
        milestone = _object(raw, path=path, required=("milestone_id", "due_date", "amount_delta_cents"))
        due = _date(milestone["due_date"], path=f"{path}.due_date")
        if due < _date(baseline["schedule"]["start_date"], path="$.baseline.schedule.start_date") or due > updated_end:
            raise DeskError("CHANGE_MILESTONE_OUTSIDE_SCHEDULE", path)
        milestone_id = _identifier(milestone["milestone_id"], path=f"{path}.milestone_id")
        amount_delta = _integer(milestone["amount_delta_cents"], path=f"{path}.amount_delta_cents", minimum=-MAX_SAFE_CENTS, maximum=MAX_SAFE_CENTS)
        baseline_amounts = {item["milestone_id"]: item["amount_cents"] for item in baseline["schedule"]["milestones"]}
        if baseline_amounts.get(milestone_id, 0) + amount_delta < 0:
            raise DeskError("UPDATED_MILESTONE_AMOUNT_NEGATIVE", path)
        milestones.append({
            "milestone_id": milestone_id,
            "due_date": due.isoformat(),
            "amount_delta_cents": amount_delta,
        })
    _check_unique([item["milestone_id"] for item in milestones], code="DUPLICATE_MILESTONE_ID", path="$.change.milestones")
    if sum(item["amount_delta_cents"] for item in milestones) != total:
        raise DeskError("CHANGE_MILESTONE_TOTAL_MISMATCH")
    evidence = _parse_evidence(row["evidence_refs"], path="$.change.evidence_refs")
    if not any(item["kind"] == "scope" for item in evidence):
        raise DeskError("SCOPE_EVIDENCE_REQUIRED")
    return {
        "schema_version": SCHEMA_VERSION,
        "change_id": _identifier(row["change_id"], path="$.change.change_id"),
        "change_version": change_version,
        "supersedes_change_sha256": supersedes,
        "baseline_id": baseline_id,
        "baseline_version": baseline_version,
        "baseline_sha256": baseline_hash,
        "currency": currency,
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": _text(row["summary"], path="$.change.summary", maximum=500),
        "scope_delta_digest": _digest(row["scope_delta_digest"], path="$.change.scope_delta_digest"),
        "line_items": items,
        "discount_delta_cents": discount,
        "tax_delta_cents": tax,
        "subtotal_delta_cents": subtotal,
        "total_delta_cents": total,
        "updated_total_cents": updated_total,
        "schedule_delta_days": delta_days,
        "updated_end_date": updated_end.isoformat(),
        "milestones": milestones,
        "evidence_refs": evidence,
    }
