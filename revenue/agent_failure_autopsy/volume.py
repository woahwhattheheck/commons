#!/usr/bin/env python3
"""Truth-bounded post-purchase volume coordinator for Agent Failure Autopsy.

This module never contacts Stripe, buyers, or providers.  It accepts private,
authenticated payment/operations receipts, calls the canonical Autopsy
fulfillment validators for any supplied intake/report pair, and derives a
redacted work queue plus a public aggregate summary.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from revenue.agent_failure_autopsy.fulfillment import (
    OFFER_ID,
    AutopsyValidationError,
    canonical_bytes,
    canonical_sha256,
    validate_intake,
    validate_report,
)

PORTFOLIO_VERSION = "commons-agent-failure-autopsy-volume/v1"
PAYMENT_VERSION = "commons-agent-failure-autopsy-payment-receipt/v1"
FACTS_VERSION = "commons-agent-failure-autopsy-next-offer-facts/v1"
PRIVATE_OUTPUT_VERSION = "commons-agent-failure-autopsy-private-queue/v1"
PUBLIC_OUTPUT_VERSION = "commons-agent-failure-autopsy-public-volume/v1"

_EXPECTED_PRICE_CENTS = 2900
_EXPECTED_CURRENCY = "USD"
_EXPECTED_PROVIDER = "STRIPE"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_PAYMENT_RE = re.compile(r"^pay_[0-9a-f]{16,64}$")
_SEAT_RE = re.compile(r"^(?:seat|peer|operator)_[A-Za-z0-9._:-]{3,120}$")

_PAYMENT_SIGNED_KEYS = {
    "schema_version",
    "offer_id",
    "case_id",
    "provider",
    "provider_payment_ref",
    "payment_state",
    "amount_cents",
    "currency",
    "observed_at",
    "provider_receipt_sha256",
}
_PAYMENT_KEYS = _PAYMENT_SIGNED_KEYS | {"authority_tag"}

_FACTS_SIGNED_KEYS = {
    "schema_version",
    "case_id",
    "basis",
    "observed_at",
    "evidence_sha256",
    "related_failed_run_count",
}
_FACTS_KEYS = _FACTS_SIGNED_KEYS | {"authority_tag"}

_CASE_KEYS = {
    "case_id",
    "payment_receipt",
    "intake",
    "report",
    "coordinator_ref",
    "backup_ref",
    "next_offer_facts",
}

_WORK_STATES = {
    "WAITING_FOR_SANITIZED_INTAKE",
    "HOLD_INTAKE",
    "ANALYSIS_DUE",
    "REFUND_DUE",
    "DELIVERED",
    "REFUNDED_CLOSED",
}
_NEXT_OFFERS = {"NONE", "$199_DIAGNOSTIC", "OWNER_REVIEW"}


class VolumeValidationError(ValueError):
    """Volume input is unauthenticated, inconsistent, duplicate, or out of contract."""


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if type(value) is not dict:
        raise VolumeValidationError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        raise VolumeValidationError(
            f"{label} keys differ: missing={sorted(expected-actual)} extra={sorted(actual-expected)}"
        )
    return value


def _text(value: Any, label: str, *, minimum: int = 1, maximum: int = 256) -> str:
    if type(value) is not str or not minimum <= len(value) <= maximum:
        raise VolumeValidationError(f"{label} must be text with length {minimum}..{maximum}")
    return value


def _id(value: Any, label: str) -> str:
    text = _text(value, label, maximum=128)
    if not _ID_RE.fullmatch(text):
        raise VolumeValidationError(f"{label} is not a safe opaque id")
    return text


def _sha(value: Any, label: str) -> str:
    text = _text(value, label, minimum=64, maximum=64)
    if not _SHA_RE.fullmatch(text):
        raise VolumeValidationError(f"{label} must be lowercase SHA-256")
    return text


def _seat(value: Any, label: str) -> str:
    text = _text(value, label, maximum=128)
    if not _SEAT_RE.fullmatch(text):
        raise VolumeValidationError(f"{label} must be an opaque seat/operator ref")
    return text


def _time(value: Any, label: str) -> datetime:
    text = _text(value, label, maximum=40)
    if not text.endswith("Z"):
        raise VolumeValidationError(f"{label} must be canonical whole-second UTC")
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise VolumeValidationError(f"{label} must be canonical whole-second UTC") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != text:
        raise VolumeValidationError(f"{label} must be canonical whole-second UTC")
    return parsed


def _key(value: Any, label: str) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise VolumeValidationError(f"{label} must be bytes")
    key = bytes(value)
    if not 32 <= len(key) <= 128:
        raise VolumeValidationError(f"{label} must be 32..128 bytes")
    return key


def _canonical_no_newline(value: Any) -> bytes:
    """Canonical JSON for runtime HMAC envelopes.

    The fulfillment module's canonical_bytes adds a trailing newline.  Reuse it
    so receipts have one repository-wide canonicalization rule.
    """
    return canonical_bytes(value)


def _auth_tag(signed: Mapping[str, Any], key: bytes) -> str:
    return hmac.new(key, _canonical_no_newline(signed), hashlib.sha256).hexdigest()


def _trusted_now() -> datetime:
    """Owner-runtime UTC clock; operational scheduling never accepts caller time."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def validate_payment_receipt(raw: Any, *, authority_key: bytes) -> dict[str, Any]:
    obj = _exact_keys(raw, _PAYMENT_KEYS, "payment_receipt")
    key = _key(authority_key, "payment authority key")
    signed = {name: obj[name] for name in sorted(_PAYMENT_SIGNED_KEYS)}

    if obj["schema_version"] != PAYMENT_VERSION:
        raise VolumeValidationError("payment receipt schema_version is invalid")
    if obj["offer_id"] != OFFER_ID:
        raise VolumeValidationError("payment receipt offer_id is invalid")
    case_id = _id(obj["case_id"], "payment_receipt.case_id")
    if obj["provider"] != _EXPECTED_PROVIDER:
        raise VolumeValidationError("payment receipt provider is not canonical Stripe")
    payment_ref = _text(obj["provider_payment_ref"], "provider_payment_ref", maximum=68)
    if not _OPAQUE_PAYMENT_RE.fullmatch(payment_ref):
        raise VolumeValidationError("provider_payment_ref must be a one-way opaque pay_<hex> ref")
    if obj["payment_state"] not in {"PAID_CONFIRMED", "REFUNDED_CONFIRMED"}:
        raise VolumeValidationError("payment_state must be provider-confirmed paid or refunded")
    if type(obj["amount_cents"]) is not int or isinstance(obj["amount_cents"], bool):
        raise VolumeValidationError("amount_cents must be an integer")
    if obj["amount_cents"] != _EXPECTED_PRICE_CENTS:
        raise VolumeValidationError("payment amount does not match the canonical USD 29 offer")
    if obj["currency"] != _EXPECTED_CURRENCY:
        raise VolumeValidationError("payment currency must be USD")
    observed_at = _time(obj["observed_at"], "payment_receipt.observed_at")
    provider_receipt_sha256 = _sha(
        obj["provider_receipt_sha256"], "payment_receipt.provider_receipt_sha256"
    )
    tag = _sha(obj["authority_tag"], "payment_receipt.authority_tag")
    expected = _auth_tag(signed, key)
    if not hmac.compare_digest(tag, expected):
        raise VolumeValidationError("payment receipt authority authentication failed")

    return {
        "case_id": case_id,
        "provider_payment_ref": payment_ref,
        "payment_state": obj["payment_state"],
        "observed_at": observed_at,
        "provider_receipt_sha256": provider_receipt_sha256,
        "receipt_sha256": canonical_sha256(obj),
    }


def validate_next_offer_facts(raw: Any, *, authority_key: bytes) -> dict[str, Any]:
    obj = _exact_keys(raw, _FACTS_KEYS, "next_offer_facts")
    key = _key(authority_key, "facts authority key")
    signed = {name: obj[name] for name in sorted(_FACTS_SIGNED_KEYS)}

    if obj["schema_version"] != FACTS_VERSION:
        raise VolumeValidationError("next_offer_facts schema_version is invalid")
    case_id = _id(obj["case_id"], "next_offer_facts.case_id")
    basis = obj["basis"]
    if basis not in {
        "NO_FOLLOW_ON_EVIDENCE",
        "SECOND_FAILED_RUN_OBSERVED",
        "IMPLEMENTATION_REQUEST_OBSERVED",
        "AMBIGUOUS_FOLLOW_ON",
    }:
        raise VolumeValidationError("next_offer_facts basis is invalid")
    observed_at = _time(obj["observed_at"], "next_offer_facts.observed_at")
    evidence_sha256 = _sha(obj["evidence_sha256"], "next_offer_facts.evidence_sha256")
    count = obj["related_failed_run_count"]
    if type(count) is not int or isinstance(count, bool) or not 0 <= count <= 1000:
        raise VolumeValidationError("related_failed_run_count must be integer 0..1000")
    if basis == "SECOND_FAILED_RUN_OBSERVED" and count < 2:
        raise VolumeValidationError("second-run basis requires at least two observed failed runs")
    if basis == "IMPLEMENTATION_REQUEST_OBSERVED" and count < 1:
        raise VolumeValidationError("implementation-request basis requires at least one failed run")
    tag = _sha(obj["authority_tag"], "next_offer_facts.authority_tag")
    expected = _auth_tag(signed, key)
    if not hmac.compare_digest(tag, expected):
        raise VolumeValidationError("next-offer facts authority authentication failed")
    return {
        "case_id": case_id,
        "basis": basis,
        "observed_at": observed_at,
        "evidence_sha256": evidence_sha256,
        "related_failed_run_count": count,
        "receipt_sha256": canonical_sha256(obj),
    }


def _next_offer_for(*, work_state: str, facts: dict[str, Any] | None) -> str:
    if work_state != "DELIVERED":
        return "NONE"
    if facts is None:
        return "OWNER_REVIEW"
    basis = facts["basis"]
    if basis == "NO_FOLLOW_ON_EVIDENCE":
        return "NONE"
    if basis == "SECOND_FAILED_RUN_OBSERVED":
        return "$199_DIAGNOSTIC"
    if basis == "IMPLEMENTATION_REQUEST_OBSERVED":
        # Implementation interest is real follow-on evidence, but Commons has no
        # canonical $2,500 Autopsy-adjacent SKU in the current source tree.
        return "OWNER_REVIEW"
    return "OWNER_REVIEW"


def _status_priority(state: str) -> int:
    return {
        "REFUND_DUE": 0,
        "ANALYSIS_DUE": 1,
        "HOLD_INTAKE": 2,
        "WAITING_FOR_SANITIZED_INTAKE": 3,
        "DELIVERED": 4,
        "REFUNDED_CLOSED": 5,
    }[state]


def _private_case_row(
    raw: Mapping[str, Any],
    *,
    as_of: datetime,
    payment_authority_key: bytes,
    facts_authority_key: bytes,
) -> dict[str, Any]:
    obj = _exact_keys(raw, _CASE_KEYS, "case")
    case_id = _id(obj["case_id"], "case.case_id")
    payment = validate_payment_receipt(
        obj["payment_receipt"], authority_key=payment_authority_key
    )
    if payment["case_id"] != case_id:
        raise VolumeValidationError("case_id does not match authenticated payment receipt")

    coordinator = _seat(obj["coordinator_ref"], "case.coordinator_ref")
    backup = _seat(obj["backup_ref"], "case.backup_ref")
    if coordinator == backup:
        raise VolumeValidationError("coordinator and backup must be distinct")

    facts = None
    if obj["next_offer_facts"] is not None:
        facts = validate_next_offer_facts(
            obj["next_offer_facts"], authority_key=facts_authority_key
        )
        if facts["case_id"] != case_id:
            raise VolumeValidationError("next-offer facts belong to another case")
        if facts["observed_at"] > as_of:
            raise VolumeValidationError("next-offer facts cannot be observed in the future")

    if payment["observed_at"] > as_of:
        raise VolumeValidationError("payment receipt cannot be observed in the future")

    intake = obj["intake"]
    report = obj["report"]
    if intake is not None and type(intake) is not dict:
        raise VolumeValidationError("case.intake must be object or null")
    if report is not None and type(report) is not dict:
        raise VolumeValidationError("case.report must be object or null")
    if report is not None and intake is None:
        raise VolumeValidationError("a report cannot exist without its intake")

    validated_report: dict[str, Any] | None = None

    # A provider-confirmed refund is terminal for scheduling. Optional retained
    # intake/report bytes may exist privately, but they cannot reopen work.
    if payment["payment_state"] == "REFUNDED_CONFIRMED":
        work_state = "REFUNDED_CLOSED"
        due_at = None
        fulfillment_receipt = None
        intake_receipt = canonical_sha256(intake) if intake is not None else None
        report_receipt = canonical_sha256(report) if report is not None else None
    elif intake is None:
        work_state = "WAITING_FOR_SANITIZED_INTAKE"
        due_at = None
        fulfillment_receipt = None
        intake_receipt = None
        report_receipt = None
    else:
        try:
            intake_context = validate_intake(intake)
        except AutopsyValidationError as exc:
            raise VolumeValidationError(f"canonical intake validation failed: {exc}") from exc
        if intake_context["case_id"] != case_id:
            raise VolumeValidationError("canonical intake belongs to another case")
        intake_receipt = canonical_sha256(intake)
        due = intake_context.get("due_at")
        due_at = due if isinstance(due, datetime) else None

        if intake_context.get("state") != "USABLE":
            if report is not None:
                try:
                    validated_report = validate_report(report, intake, intake_context)
                except AutopsyValidationError as exc:
                    raise VolumeValidationError(
                        f"canonical report validation failed: {exc}"
                    ) from exc
                if report.get("disposition") != "REFUND_REQUIRED":
                    raise VolumeValidationError(
                        "non-usable intake may only carry a canonical refund report"
                    )
                work_state = "REFUND_DUE"
                report_receipt = canonical_sha256(report)
                fulfillment_receipt = canonical_sha256(
                    {"intake_sha256": intake_receipt, "report_sha256": report_receipt}
                )
            else:
                work_state = "HOLD_INTAKE"
                report_receipt = None
                fulfillment_receipt = None
        elif report is None:
            if due_at is None:
                raise VolumeValidationError("usable canonical intake lacks delivery deadline")
            work_state = "REFUND_DUE" if as_of > due_at else "ANALYSIS_DUE"
            report_receipt = None
            fulfillment_receipt = None
        else:
            try:
                validated_report = validate_report(report, intake, intake_context)
            except AutopsyValidationError as exc:
                raise VolumeValidationError(
                    f"canonical report validation failed: {exc}"
                ) from exc
            report_receipt = canonical_sha256(report)
            fulfillment_receipt = canonical_sha256(
                {"intake_sha256": intake_receipt, "report_sha256": report_receipt}
            )
            disposition = report.get("disposition")
            if disposition == "DIAGNOSIS_DELIVERED":
                work_state = "DELIVERED"
            elif disposition == "REFUND_REQUIRED":
                work_state = "REFUND_DUE"
            else:
                raise VolumeValidationError("canonical report has unknown disposition")

    next_offer = _next_offer_for(work_state=work_state, facts=facts)
    if next_offer not in _NEXT_OFFERS:
        raise AssertionError("internal next-offer state")

    hours_to_due = None
    sla_state = "CLOCK_NOT_RUNNING"
    if due_at is not None and work_state in {"ANALYSIS_DUE", "REFUND_DUE"}:
        hours_to_due = (due_at - as_of).total_seconds() / 3600.0
        if work_state == "REFUND_DUE":
            sla_state = "REFUND_REQUIRED"
        elif hours_to_due <= 4:
            sla_state = "DUE_SOON"
        else:
            sla_state = "ON_CLOCK"
    elif work_state == "DELIVERED":
        sla_state = "CLOSED_DELIVERED"
    elif work_state == "REFUNDED_CLOSED":
        sla_state = "CLOSED_REFUNDED"
    elif work_state == "HOLD_INTAKE":
        sla_state = "CLOCK_STOPPED_INTAKE"
    elif work_state == "WAITING_FOR_SANITIZED_INTAKE":
        sla_state = "CLOCK_NOT_STARTED"

    return {
        "case_id": case_id,
        "work_state": work_state,
        "sla_state": sla_state,
        "due_at": (
            due_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if due_at
            else None
        ),
        "hours_to_due": round(hours_to_due, 3) if hours_to_due is not None else None,
        "coordinator_ref": coordinator,
        "backup_ref": backup,
        "payment_state": payment["payment_state"],
        "payment_receipt_sha256": payment["receipt_sha256"],
        "provider_evidence_sha256": payment["provider_receipt_sha256"],
        "intake_sha256": intake_receipt,
        "report_sha256": report_receipt,
        "fulfillment_receipt_sha256": fulfillment_receipt,
        "next_offer": next_offer,
        "next_offer_facts_sha256": facts["receipt_sha256"] if facts else None,
        "fulfillment_economics": {
            "measurement_purpose": (
                validated_report["time_measurement_purpose"]
                if validated_report is not None
                else None
            ),
            "automated_draft_minutes": (
                validated_report["automated_draft_minutes"]
                if validated_report is not None
                else None
            ),
            "reviewer_minutes": (
                validated_report["reviewer_minutes"]
                if validated_report is not None
                else None
            ),
            "quality_truncation_authorized": False,
        },
        "external_action_authorized": False,
        "automatic_outreach_authorized": False,
        "automatic_charge_or_refund_authorized": False,
        "cash_or_revenue_recognized": False,
    }


def compile_volume(
    case_records: Sequence[Mapping[str, Any]],
    *,
    payment_authority_key: bytes,
    facts_authority_key: bytes,
    max_active_cases: int,
) -> dict[str, Any]:
    if isinstance(case_records, (str, bytes, bytearray)) or not isinstance(case_records, Sequence):
        raise VolumeValidationError("case_records must be a sequence")
    if len(case_records) > 10_000:
        raise VolumeValidationError("too many cases")
    if type(max_active_cases) is not int or isinstance(max_active_cases, bool) or not 1 <= max_active_cases <= 1000:
        raise VolumeValidationError("max_active_cases must be integer 1..1000")
    current = _trusted_now()
    as_of = current.strftime("%Y-%m-%dT%H:%M:%SZ")
    _key(payment_authority_key, "payment authority key")
    _key(facts_authority_key, "facts authority key")

    rows: list[dict[str, Any]] = []
    seen_cases: set[str] = set()
    seen_payments: set[str] = set()
    for index, raw in enumerate(case_records):
        row = _private_case_row(
            raw,
            as_of=current,
            payment_authority_key=payment_authority_key,
            facts_authority_key=facts_authority_key,
        )
        if row["case_id"] in seen_cases:
            raise VolumeValidationError(f"duplicate case_id at case_records[{index}]")
        seen_cases.add(row["case_id"])
        payment_ref = raw["payment_receipt"]["provider_payment_ref"]
        if payment_ref in seen_payments:
            raise VolumeValidationError(
                f"provider payment ref reused across cases at case_records[{index}]"
            )
        seen_payments.add(payment_ref)
        rows.append(row)

    rows.sort(
        key=lambda row: (
            _status_priority(row["work_state"]),
            row["due_at"] or "9999-12-31T23:59:59Z",
            row["case_id"],
        )
    )

    analysis_due = sum(row["work_state"] == "ANALYSIS_DUE" for row in rows)
    refund_due = sum(row["work_state"] == "REFUND_DUE" for row in rows)
    capacity = {
        "max_active_cases": max_active_cases,
        "analysis_due_cases": analysis_due,
        "analysis_slots_available": max(0, max_active_cases - analysis_due),
        "over_capacity": analysis_due > max_active_cases,
        "backlog_cases": max(0, analysis_due - max_active_cases),
        "refund_due_cases": refund_due,
    }
    state_counts = {state: sum(row["work_state"] == state for row in rows) for state in sorted(_WORK_STATES)}
    next_offer_counts = {state: sum(row["next_offer"] == state for row in rows) for state in sorted(_NEXT_OFFERS)}
    measured_rows = [
        row["fulfillment_economics"]
        for row in rows
        if row["fulfillment_economics"]["measurement_purpose"] == "DESCRIPTIVE_ECONOMICS_ONLY"
    ]
    economics = {
        "measured_case_count": len(measured_rows),
        "automated_draft_minutes": sum(
            item["automated_draft_minutes"] or 0 for item in measured_rows
        ),
        "reviewer_minutes": sum(
            item["reviewer_minutes"] or 0 for item in measured_rows
        ),
        "measurement_purpose": "DESCRIPTIVE_ECONOMICS_ONLY",
        "quality_truncation_authorized": False,
    }

    public_summary = {
        "schema_version": PUBLIC_OUTPUT_VERSION,
        "offer_id": OFFER_ID,
        "as_of": as_of,
        "case_count": len(rows),
        "cases_by_state": state_counts,
        "next_offer_eligibility_counts": next_offer_counts,
        "capacity": capacity,
        "buyer_identifiers_included": False,
        "provider_payment_refs_included": False,
        "payment_amount_totals_included": False,
        "automatic_outreach_authorized": False,
        "automatic_charge_or_refund_authorized": False,
        "cash_or_revenue_recognized": False,
    }
    public_summary["summary_sha256"] = canonical_sha256(public_summary)

    private_body = {
        "schema_version": PRIVATE_OUTPUT_VERSION,
        "offer_id": OFFER_ID,
        "as_of": as_of,
        "queue": rows,
        "capacity": capacity,
        "cases_by_state": state_counts,
        "next_offer_eligibility_counts": next_offer_counts,
        "fulfillment_economics": economics,
        "public_summary_sha256": public_summary["summary_sha256"],
        "external_action_authorized": False,
        "automatic_outreach_authorized": False,
        "automatic_charge_or_refund_authorized": False,
        "cash_or_revenue_recognized": False,
    }
    private_body["queue_sha256"] = canonical_sha256(private_body)

    return {
        "schema_version": PORTFOLIO_VERSION,
        "private": private_body,
        "public": public_summary,
    }


def verify_compiled_volume(result: Any) -> bool:
    """Verify deterministic internal receipt binding on a compiled result.

    This is an integrity verifier, not provider/payment authority. Provider
    authority is established only while compiling from authenticated private
    receipts under the owner-runtime key.
    """
    obj = _exact_keys(result, {"schema_version", "private", "public"}, "compiled result")
    if obj["schema_version"] != PORTFOLIO_VERSION:
        raise VolumeValidationError("compiled result schema_version is invalid")
    public = _exact_keys(
        obj["public"],
        {
            "schema_version",
            "offer_id",
            "as_of",
            "case_count",
            "cases_by_state",
            "next_offer_eligibility_counts",
            "capacity",
            "buyer_identifiers_included",
            "provider_payment_refs_included",
            "payment_amount_totals_included",
            "automatic_outreach_authorized",
            "automatic_charge_or_refund_authorized",
            "cash_or_revenue_recognized",
            "summary_sha256",
        },
        "compiled public result",
    )
    public_without = dict(public)
    claimed_public = _sha(public_without.pop("summary_sha256"), "public.summary_sha256")
    if canonical_sha256(public_without) != claimed_public:
        raise VolumeValidationError("public summary receipt mismatch")

    private = _exact_keys(
        obj["private"],
        {
            "schema_version",
            "offer_id",
            "as_of",
            "queue",
            "capacity",
            "cases_by_state",
            "next_offer_eligibility_counts",
            "fulfillment_economics",
            "public_summary_sha256",
            "external_action_authorized",
            "automatic_outreach_authorized",
            "automatic_charge_or_refund_authorized",
            "cash_or_revenue_recognized",
            "queue_sha256",
        },
        "compiled private result",
    )
    if private["public_summary_sha256"] != claimed_public:
        raise VolumeValidationError("private/public summary receipt mismatch")
    private_without = dict(private)
    claimed_private = _sha(private_without.pop("queue_sha256"), "private.queue_sha256")
    if canonical_sha256(private_without) != claimed_private:
        raise VolumeValidationError("private queue receipt mismatch")
    for field in (
        "external_action_authorized",
        "automatic_outreach_authorized",
        "automatic_charge_or_refund_authorized",
        "cash_or_revenue_recognized",
    ):
        if private[field] is not False:
            raise VolumeValidationError(f"compiled private authority field drift: {field}")
    for field in (
        "automatic_outreach_authorized",
        "automatic_charge_or_refund_authorized",
        "cash_or_revenue_recognized",
    ):
        if public[field] is not False:
            raise VolumeValidationError(f"compiled public authority field drift: {field}")
    return True


def _read_key_from_env(name: str) -> bytes:
    raw = os.environ.get(name)
    if raw is None:
        raise VolumeValidationError(f"missing required environment variable: {name}")
    try:
        key = bytes.fromhex(raw)
    except ValueError as exc:
        raise VolumeValidationError(f"{name} must contain hex-encoded key bytes") from exc
    return _key(key, name)


def _write_new_json(path: Path, value: Any) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(canonical_bytes(value))
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases_json", type=Path, help="private JSON array of case records")
    parser.add_argument("--max-active-cases", required=True, type=int)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    parser.add_argument(
        "--payment-key-env",
        default="AUTOPSY_PAYMENT_AUTH_KEY_HEX",
        help="environment variable containing hex payment-authority key",
    )
    parser.add_argument(
        "--facts-key-env",
        default="AUTOPSY_FACTS_AUTH_KEY_HEX",
        help="environment variable containing hex next-offer-facts key",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        raw = json.loads(args.cases_json.read_text(encoding="utf-8"))
        payment_key = _read_key_from_env(args.payment_key_env)
        facts_key = _read_key_from_env(args.facts_key_env)
        result = compile_volume(
            raw,
            payment_authority_key=payment_key,
            facts_authority_key=facts_key,
            max_active_cases=args.max_active_cases,
        )
        _write_new_json(args.private_output, result["private"])
        _write_new_json(args.public_output, result["public"])
    except (OSError, ValueError, VolumeValidationError, AutopsyValidationError) as exc:
        print(f"volume-error: {exc}", file=os.sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
