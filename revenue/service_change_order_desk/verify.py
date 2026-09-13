from __future__ import annotations

from typing import Any, Mapping

from .common import (
    AUTHORITY_FALSE,
    MAX_EVENTS,
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
    _scan_sensitive,
    _text,
    _timestamp,
    sha256_json,
)
from .events import validate_events
from .package import _receipt_digest, _render_markdown, format_money


def _validate_authority(value: Any) -> dict[str, bool]:
    row = _object(value, path="$.package.receipt.authority", required=AUTHORITY_FALSE.keys())
    normalized: dict[str, bool] = {}
    for key in AUTHORITY_FALSE:
        if row[key] is not False:
            raise DeskError("AUTHORITY_CEILING_VIOLATION", key)
        normalized[key] = False
    return normalized


def _validate_hold_receipt(receipt: Any) -> Mapping[str, Any]:
    required = (
        "schema_version", "product", "status", "hold_codes", "generated_at",
        "baseline_input_sha256", "change_input_sha256", "events_input_sha256",
        "expected_baseline_sha256", "expected_baseline_input_sha256",
        "baseline_commitment_verified", "integrity_only", "source_authority_verified",
        "authority", "receipt_sha256",
    )
    row = _object(receipt, path="$.package.receipt", required=required)
    if _integer(row["schema_version"], path="$.package.receipt.schema_version", minimum=1, maximum=1) != SCHEMA_VERSION:
        raise DeskError("UNSUPPORTED_SCHEMA_VERSION", "$.package.receipt")
    if row["product"] != "service_change_order_desk" or row["status"] != "HOLD":
        raise DeskError("INVALID_RECEIPT_IDENTITY")
    hold_codes = _list(row["hold_codes"], path="$.package.receipt.hold_codes", maximum=1, allow_empty=False)
    _text(hold_codes[0], path="$.package.receipt.hold_codes[0]", maximum=96)
    _timestamp(row["generated_at"], path="$.package.receipt.generated_at")
    for key in ("baseline_input_sha256", "change_input_sha256", "events_input_sha256", "expected_baseline_input_sha256"):
        _digest(row[key], path=f"$.package.receipt.{key}")
    if row["expected_baseline_sha256"] is not None:
        _digest(row["expected_baseline_sha256"], path="$.package.receipt.expected_baseline_sha256")
    if row["baseline_commitment_verified"] is not False:
        raise DeskError("HOLD_CANNOT_VERIFY_BASELINE")
    if row["integrity_only"] is not True or row["source_authority_verified"] is not False:
        raise DeskError("TRUST_BOUNDARY_MISMATCH")
    _validate_authority(row["authority"])
    _digest(row["receipt_sha256"], path="$.package.receipt.receipt_sha256")
    return row


def _validate_success_receipt(receipt: Any) -> Mapping[str, Any]:
    required = (
        "schema_version", "product", "status", "hold_codes", "generated_at",
        "baseline_input_sha256", "change_input_sha256", "events_input_sha256",
        "expected_baseline_sha256", "expected_baseline_input_sha256",
        "baseline_id", "baseline_version", "baseline_sha256", "baseline_commitment_verified",
        "change_id", "change_version", "supersedes_change_sha256", "change_sha256", "change_created_at",
        "currency", "summary", "scope_delta_digest", "line_items", "subtotal_delta_cents",
        "discount_delta_cents", "tax_delta_cents", "total_delta_cents", "updated_total_cents",
        "schedule_delta_days", "updated_end_date", "milestones", "evidence_refs", "expires_at",
        "events", "event_count", "event_tip_sha256", "events_sha256", "integrity_only",
        "source_authority_verified", "authority", "receipt_sha256",
    )
    row = _object(receipt, path="$.package.receipt", required=required)
    if _integer(row["schema_version"], path="$.package.receipt.schema_version", minimum=1, maximum=1) != SCHEMA_VERSION:
        raise DeskError("UNSUPPORTED_SCHEMA_VERSION", "$.package.receipt")
    if row["product"] != "service_change_order_desk":
        raise DeskError("INVALID_RECEIPT_IDENTITY")
    valid_states = {"DRAFT", "READY_FOR_HUMAN_REVIEW", "APPROVED", "REJECTED", "REVISION_REQUESTED", "CANCELLED"}
    if row["status"] not in valid_states:
        raise DeskError("INVALID_RECEIPT_STATUS")
    if _list(row["hold_codes"], path="$.package.receipt.hold_codes", maximum=0, allow_empty=True):
        raise DeskError("SUCCESS_RECEIPT_HAS_HOLD_CODE")
    generated = _timestamp(row["generated_at"], path="$.package.receipt.generated_at")
    for key in (
        "baseline_input_sha256", "change_input_sha256", "events_input_sha256",
        "expected_baseline_sha256", "expected_baseline_input_sha256", "baseline_sha256",
        "change_sha256", "scope_delta_digest", "events_sha256", "receipt_sha256",
    ):
        _digest(row[key], path=f"$.package.receipt.{key}")
    if row["expected_baseline_sha256"] != row["baseline_sha256"] or row["baseline_commitment_verified"] is not True:
        raise DeskError("BASELINE_COMMITMENT_MISMATCH")
    _identifier(row["baseline_id"], path="$.package.receipt.baseline_id")
    _integer(row["baseline_version"], path="$.package.receipt.baseline_version", minimum=1, maximum=1_000_000)
    _identifier(row["change_id"], path="$.package.receipt.change_id")
    change_version = _integer(row["change_version"], path="$.package.receipt.change_version", minimum=1, maximum=1_000_000)
    if change_version == 1:
        if row["supersedes_change_sha256"] is not None:
            raise DeskError("UNEXPECTED_SUPERSESSION_COMMITMENT")
    else:
        _digest(row["supersedes_change_sha256"], path="$.package.receipt.supersedes_change_sha256")
    change_created = _timestamp(row["change_created_at"], path="$.package.receipt.change_created_at")
    expires = _timestamp(row["expires_at"], path="$.package.receipt.expires_at")
    if change_created > generated or generated > expires:
        raise DeskError("INVALID_RECEIPT_TIME")
    currency = _currency(row["currency"], path="$.package.receipt.currency")
    _text(row["summary"], path="$.package.receipt.summary", maximum=500)
    line_items = _list(row["line_items"], path="$.package.receipt.line_items", maximum=MAX_ITEMS, allow_empty=True)
    parsed_items: list[dict[str, Any]] = []
    for index, raw in enumerate(line_items):
        path = f"$.package.receipt.line_items[{index}]"
        item = _object(raw, path=path, required=("item_id", "description", "quantity", "unit_delta_cents"))
        parsed_items.append({
            "item_id": _identifier(item["item_id"], path=f"{path}.item_id"),
            "description": _text(item["description"], path=f"{path}.description", maximum=240),
            "quantity": _integer(item["quantity"], path=f"{path}.quantity", minimum=1, maximum=1_000_000),
            "unit_delta_cents": _integer(item["unit_delta_cents"], path=f"{path}.unit_delta_cents", minimum=-MAX_SAFE_CENTS, maximum=MAX_SAFE_CENTS),
        })
    _check_unique([item["item_id"] for item in parsed_items], code="DUPLICATE_ITEM_ID", path="$.package.receipt.line_items")
    computed_subtotal = sum(item["quantity"] * item["unit_delta_cents"] for item in parsed_items)
    subtotal = _integer(row["subtotal_delta_cents"], path="$.package.receipt.subtotal_delta_cents", minimum=-MAX_SAFE_CENTS, maximum=MAX_SAFE_CENTS)
    discount = _integer(row["discount_delta_cents"], path="$.package.receipt.discount_delta_cents", minimum=-MAX_SAFE_CENTS, maximum=MAX_SAFE_CENTS)
    tax = _integer(row["tax_delta_cents"], path="$.package.receipt.tax_delta_cents", minimum=-MAX_SAFE_CENTS, maximum=MAX_SAFE_CENTS)
    total = _integer(row["total_delta_cents"], path="$.package.receipt.total_delta_cents", minimum=-MAX_SAFE_CENTS, maximum=MAX_SAFE_CENTS)
    _integer(row["updated_total_cents"], path="$.package.receipt.updated_total_cents", minimum=0, maximum=MAX_SAFE_CENTS)
    if computed_subtotal != subtotal or subtotal - discount + tax != total:
        raise DeskError("RECEIPT_MONEY_MISMATCH")
    _integer(row["schedule_delta_days"], path="$.package.receipt.schedule_delta_days", minimum=-365, maximum=365)
    _date(row["updated_end_date"], path="$.package.receipt.updated_end_date")
    milestones = _list(row["milestones"], path="$.package.receipt.milestones", maximum=MAX_ITEMS, allow_empty=True)
    milestone_ids: list[str] = []
    milestone_total = 0
    for index, raw in enumerate(milestones):
        path = f"$.package.receipt.milestones[{index}]"
        milestone = _object(raw, path=path, required=("milestone_id", "due_date", "amount_delta_cents"))
        milestone_ids.append(_identifier(milestone["milestone_id"], path=f"{path}.milestone_id"))
        _date(milestone["due_date"], path=f"{path}.due_date")
        milestone_total += _integer(milestone["amount_delta_cents"], path=f"{path}.amount_delta_cents", minimum=-MAX_SAFE_CENTS, maximum=MAX_SAFE_CENTS)
    _check_unique(milestone_ids, code="DUPLICATE_MILESTONE_ID", path="$.package.receipt.milestones")
    if milestone_total != total:
        raise DeskError("RECEIPT_MILESTONE_TOTAL_MISMATCH")
    evidence = _parse_evidence(row["evidence_refs"], path="$.package.receipt.evidence_refs")
    if not any(item["kind"] == "scope" for item in evidence):
        raise DeskError("SCOPE_EVIDENCE_REQUIRED")
    events = _list(row["events"], path="$.package.receipt.events", maximum=MAX_EVENTS, allow_empty=True)
    if _integer(row["event_count"], path="$.package.receipt.event_count", minimum=0, maximum=MAX_EVENTS) != len(events):
        raise DeskError("EVENT_COUNT_MISMATCH")
    if sha256_json(events) != row["events_sha256"]:
        raise DeskError("EVENTS_DIGEST_MISMATCH")
    event_change = {
        "created_at": change_created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "change_version": change_version,
        "evidence_refs": evidence,
    }
    parsed_events, state, event_tip = validate_events(events, event_change, generated)
    if parsed_events != events or state != row["status"] or event_tip != row["event_tip_sha256"]:
        raise DeskError("EVENT_CHAIN_RECEIPT_MISMATCH")
    if row["integrity_only"] is not True or row["source_authority_verified"] is not False:
        raise DeskError("TRUST_BOUNDARY_MISMATCH")
    _validate_authority(row["authority"])
    # Exercise exact formatting without relying on binary floating point.
    format_money(total, currency)
    return row


def verify_package(package: Any) -> dict[str, Any]:
    row = _object(package, path="$.package", required=("schema_version", "receipt", "markdown", "package_sha256"))
    if _integer(row["schema_version"], path="$.package.schema_version", minimum=1, maximum=1) != SCHEMA_VERSION:
        raise DeskError("UNSUPPORTED_SCHEMA_VERSION", "$.package")
    if not isinstance(row["receipt"], dict):
        raise DeskError("EXPECTED_OBJECT", "$.package.receipt")
    receipt = _validate_hold_receipt(row["receipt"]) if row["receipt"].get("status") == "HOLD" else _validate_success_receipt(row["receipt"])
    _scan_sensitive(receipt, "$.package.receipt")
    supplied_receipt_digest = _digest(receipt.get("receipt_sha256"), path="$.package.receipt.receipt_sha256")
    if supplied_receipt_digest != _receipt_digest(receipt):
        raise DeskError("RECEIPT_DIGEST_MISMATCH")
    markdown = _text(row["markdown"], path="$.package.markdown", maximum=200_000, allow_empty=False)
    if markdown != _render_markdown(receipt):
        raise DeskError("MARKDOWN_MISMATCH")
    supplied_package_digest = _digest(row["package_sha256"], path="$.package.package_sha256")
    unsigned = {"schema_version": SCHEMA_VERSION, "receipt": receipt, "markdown": markdown}
    if supplied_package_digest != sha256_json(unsigned):
        raise DeskError("PACKAGE_DIGEST_MISMATCH")
    return {
        "verified": True,
        "integrity_only": True,
        "source_authority_verified": False,
        "status": receipt["status"],
        "receipt_sha256": supplied_receipt_digest,
        "package_sha256": supplied_package_digest,
    }
