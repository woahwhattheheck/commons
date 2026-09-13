from __future__ import annotations

import copy
from typing import Any, Mapping

from .common import (
    AUTHORITY_FALSE,
    HEX64,
    SCHEMA_VERSION,
    DeskError,
    _digest,
    _scan_sensitive,
    _timestamp,
    _validate_json,
    sha256_json,
    sha256_text,
)
from .events import validate_events
from .model import _parse_baseline, _parse_change


def format_money(cents: int, currency: str) -> str:
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise DeskError("EXPECTED_INTEGER", "money")
    sign = "-" if cents < 0 else ""
    whole, fraction = divmod(abs(cents), 100)
    return f"{sign}{currency} {whole}.{fraction:02d}"


def _receipt_digest(receipt: Mapping[str, Any]) -> str:
    return sha256_json({key: value for key, value in receipt.items() if key != "receipt_sha256"})


def _render_markdown(receipt: Mapping[str, Any]) -> str:
    status = receipt["status"]
    lines = [
        f"# Service Change Order — {receipt.get('change_id', 'HOLD')}",
        "",
        f"**Status:** `{status}`",
        f"**Generated:** {receipt['generated_at']}",
    ]
    if status == "HOLD":
        lines.extend(["", "## Hold", "", f"Reason: `{receipt['hold_codes'][0]}`", ""])
        return "\n".join(lines)
    currency = receipt["currency"]
    lines.extend([
        f"**Baseline:** `{receipt['baseline_id']}` v{receipt['baseline_version']}",
        f"**Change version:** {receipt['change_version']}",
        "",
        "## Summary",
        "",
        receipt["summary"],
        "",
        "## Price change",
        "",
        "| Item | Description | Qty | Unit delta | Extended delta |",
        "|---|---|---:|---:|---:|",
    ])
    for item in receipt["line_items"]:
        extended = item["quantity"] * item["unit_delta_cents"]
        lines.append(
            f"| `{item['item_id']}` | {item['description']} | {item['quantity']} | "
            f"{format_money(item['unit_delta_cents'], currency)} | {format_money(extended, currency)} |"
        )
    if not receipt["line_items"]:
        lines.append(f"| — | Schedule-only change | 0 | — | {format_money(0, currency)} |")
    lines.extend([
        "",
        f"Subtotal delta: **{format_money(receipt['subtotal_delta_cents'], currency)}**  ",
        f"Discount delta: **{format_money(receipt['discount_delta_cents'], currency)}**  ",
        f"Tax delta: **{format_money(receipt['tax_delta_cents'], currency)}**  ",
        f"Total delta: **{format_money(receipt['total_delta_cents'], currency)}**  ",
        f"Updated total: **{format_money(receipt['updated_total_cents'], currency)}**",
        "",
        "## Schedule",
        "",
        f"End-date change: **{receipt['schedule_delta_days']:+d} days**  ",
        f"Updated end date: **{receipt['updated_end_date']}**",
        "",
        "## Authority boundary",
        "",
        "This package is deterministic integrity evidence for human review. It does not send, sign, amend a contract, charge, schedule, dispatch, begin fulfillment, deploy, or recognize cash/revenue.",
        "",
        f"Receipt SHA-256: `{receipt['receipt_sha256']}`",
        "",
    ])
    return "\n".join(lines)


def _hold_package(
    *,
    code: str,
    baseline_input_sha256: str,
    change_input_sha256: str,
    events_input_sha256: str,
    expected_baseline_sha256: str,
    generated_at: str,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "product": "service_change_order_desk",
        "status": "HOLD",
        "hold_codes": [code],
        "generated_at": generated_at,
        "baseline_input_sha256": baseline_input_sha256,
        "change_input_sha256": change_input_sha256,
        "events_input_sha256": events_input_sha256,
        "expected_baseline_sha256": expected_baseline_sha256 if isinstance(expected_baseline_sha256, str) and HEX64.fullmatch(expected_baseline_sha256) else None,
        "expected_baseline_input_sha256": sha256_text(repr(expected_baseline_sha256)),
        "baseline_commitment_verified": False,
        "integrity_only": True,
        "source_authority_verified": False,
        "authority": copy.deepcopy(AUTHORITY_FALSE),
    }
    receipt["receipt_sha256"] = _receipt_digest(receipt)
    markdown = _render_markdown(receipt)
    package = {"schema_version": SCHEMA_VERSION, "receipt": receipt, "markdown": markdown}
    package["package_sha256"] = sha256_json(package)
    return package


def build_package(
    baseline: Any,
    change: Any,
    events: Any,
    *,
    expected_baseline_sha256: str,
    evaluation_time: str,
) -> dict[str, Any]:
    evaluation = _timestamp(evaluation_time, path="$.evaluation_time")
    generated_at = evaluation.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        baseline_input_sha256 = sha256_json(baseline)
    except DeskError:
        baseline_input_sha256 = sha256_text(repr(baseline))
    try:
        change_input_sha256 = sha256_json(change)
    except DeskError:
        change_input_sha256 = sha256_text(repr(change))
    try:
        events_input_sha256 = sha256_json(events)
    except DeskError:
        events_input_sha256 = sha256_text(repr(events))
    try:
        expected = _digest(expected_baseline_sha256, path="$.expected_baseline_sha256")
        _validate_json(baseline, "$.baseline")
        _validate_json(change, "$.change")
        _validate_json(events, "$.events")
        _scan_sensitive(baseline, "$.baseline")
        _scan_sensitive(change, "$.change")
        _scan_sensitive(events, "$.events")
        parsed_baseline = _parse_baseline(baseline)
        canonical_baseline_sha = sha256_json(parsed_baseline)
        if canonical_baseline_sha != expected:
            raise DeskError("BASELINE_COMMITMENT_MISMATCH")
        parsed_change = _parse_change(change, parsed_baseline, expected, evaluation)
        parsed_events, state, event_tip = validate_events(events, parsed_change, evaluation)
        receipt: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "product": "service_change_order_desk",
            "status": state,
            "hold_codes": [],
            "generated_at": generated_at,
            "baseline_input_sha256": baseline_input_sha256,
            "change_input_sha256": change_input_sha256,
            "events_input_sha256": events_input_sha256,
            "expected_baseline_sha256": expected,
            "expected_baseline_input_sha256": sha256_text(repr(expected_baseline_sha256)),
            "baseline_id": parsed_baseline["baseline_id"],
            "baseline_version": parsed_baseline["baseline_version"],
            "baseline_sha256": expected,
            "baseline_commitment_verified": True,
            "change_id": parsed_change["change_id"],
            "change_version": parsed_change["change_version"],
            "supersedes_change_sha256": parsed_change["supersedes_change_sha256"],
            "change_sha256": sha256_json(parsed_change),
            "change_created_at": parsed_change["created_at"],
            "currency": parsed_change["currency"],
            "summary": parsed_change["summary"],
            "scope_delta_digest": parsed_change["scope_delta_digest"],
            "line_items": parsed_change["line_items"],
            "subtotal_delta_cents": parsed_change["subtotal_delta_cents"],
            "discount_delta_cents": parsed_change["discount_delta_cents"],
            "tax_delta_cents": parsed_change["tax_delta_cents"],
            "total_delta_cents": parsed_change["total_delta_cents"],
            "updated_total_cents": parsed_change["updated_total_cents"],
            "schedule_delta_days": parsed_change["schedule_delta_days"],
            "updated_end_date": parsed_change["updated_end_date"],
            "milestones": parsed_change["milestones"],
            "evidence_refs": parsed_change["evidence_refs"],
            "expires_at": parsed_change["expires_at"],
            "events": parsed_events,
            "event_count": len(parsed_events),
            "event_tip_sha256": event_tip,
            "events_sha256": sha256_json(parsed_events),
            "integrity_only": True,
            "source_authority_verified": False,
            "authority": copy.deepcopy(AUTHORITY_FALSE),
        }
        receipt["receipt_sha256"] = _receipt_digest(receipt)
        markdown = _render_markdown(receipt)
        package = {"schema_version": SCHEMA_VERSION, "receipt": receipt, "markdown": markdown}
        package["package_sha256"] = sha256_json(package)
        return package
    except DeskError as exc:
        return _hold_package(
            code=exc.code,
            baseline_input_sha256=baseline_input_sha256,
            change_input_sha256=change_input_sha256,
            events_input_sha256=events_input_sha256,
            expected_baseline_sha256=expected_baseline_sha256 if isinstance(expected_baseline_sha256, str) else sha256_text(repr(expected_baseline_sha256)),
            generated_at=generated_at,
        )
