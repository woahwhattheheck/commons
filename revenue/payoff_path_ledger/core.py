from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

SCHEMA_INPUT = "commons-payoff-path-input/v1"
SCHEMA_RECEIPT = "commons-payoff-path-receipt/v1"
COMPILER_ID = "commons.payoff-path-ledger/v1"
MAX_SAFE_INT = 10**15
MAX_TEXT = 4096
MAX_ROWS = 256
MAX_EVIDENCE_AGE = timedelta(days=90)

PAYOFF_CLASSES = frozenset(
    {
        "BUG_BOUNTY",
        "COMPETITION_PRIZE",
        "PAID_DISCOVERY",
        "PARTNER_WORKSHARE",
        "PRODUCT_CONVERSION",
        "PAID_WORK",
        "STRATEGIC_UNPAID",
    }
)
CASH_TERM_CLASSES = frozenset(
    {"BUG_BOUNTY", "COMPETITION_PRIZE", "PAID_DISCOVERY", "PARTNER_WORKSHARE", "PAID_WORK"}
)
EVIDENCE_CLASSES = PAYOFF_CLASSES | frozenset({"GENERIC_CONTEXT"})
OUTCOME_KINDS = frozenset({"ACTIVE_DUPLICATE", "SETTLED"})
SCOPE_STATUSES = frozenset({"COMPLETE", "PARTIAL"})
AMOUNT_MODES = frozenset({"EXACT", "AMOUNT_UNKNOWN"})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,255}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

_AUTHORITY = {
    "contact_authorized": False,
    "muse_election_authorized": False,
    "terms_acceptance_authorized": False,
    "contract_or_signature_authorized": False,
    "submission_authorized": False,
    "invoice_or_receivable_authorized": False,
    "payment_or_funds_movement_authorized": False,
    "cash_receipt_proven": False,
    "revenue_recognized": False,
    "tax_or_accounting_conclusion": False,
    "provider_or_account_mutation_authorized": False,
}


class GateError(ValueError):
    pass


def _reject_float(_: str) -> Any:
    raise GateError("floating-point JSON is not allowed")


def _reject_constant(_: str) -> Any:
    raise GateError("non-finite JSON is not allowed")


def _parse_int(token: str) -> int:
    if len(token.lstrip("-")) > 16:
        raise GateError("integer outside safe domain")
    value = int(token)
    if abs(value) > MAX_SAFE_INT:
        raise GateError("integer outside safe domain")
    return value


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise GateError("duplicate JSON key")
        out[key] = value
    return out


def loads_strict_json(raw: bytes | str) -> Any:
    try:
        if isinstance(raw, bytes):
            text = raw.decode("utf-8", "strict")
        elif type(raw) is str:
            raw.encode("utf-8", "strict")
            text = raw
        else:
            raise GateError("JSON input must be bytes or exact str")
    except UnicodeError as exc:
        raise GateError("invalid UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_float=_reject_float,
            parse_int=_parse_int,
            parse_constant=_reject_constant,
        )
    except GateError:
        raise
    except (json.JSONDecodeError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise GateError("invalid JSON") from exc
    return _freeze_json(value)


def _freeze_json(value: Any, path: str = "$") -> Any:
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if abs(value) > MAX_SAFE_INT:
            raise GateError("integer outside safe domain")
        return value
    if type(value) is str:
        if len(value) > MAX_TEXT:
            raise GateError("text too long")
        try:
            value.encode("utf-8", "strict")
        except UnicodeError as exc:
            raise GateError("invalid UTF-8 text") from exc
        return value
    if type(value) is list:
        if len(value) > MAX_ROWS:
            raise GateError("collection too large")
        return [_freeze_json(v, f"{path}[]") for v in value]
    if type(value) is dict:
        if len(value) > MAX_ROWS:
            raise GateError("mapping too large")
        out: dict[str, Any] = {}
        for key, child in value.items():
            if type(key) is not str:
                raise GateError("object key must be exact str")
            _freeze_json(key, path)
            out[key] = _freeze_json(child, f"{path}.{key}")
        return out
    raise GateError(f"non-JSON value at {path}")


def _canonical_bytes(value: Any) -> bytes:
    frozen = _freeze_json(value)
    try:
        return json.dumps(frozen, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8", "strict")
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise GateError("cannot canonicalize JSON") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _exact_keys(obj: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(obj) is not dict:
        raise GateError(f"{label} must be object")
    if set(obj) != keys:
        raise GateError(f"{label} keys mismatch")
    return obj


def _text(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str:
        raise GateError(f"{label} must be exact str")
    if not allow_empty and not value:
        raise GateError(f"{label} must be nonempty")
    if len(value) > MAX_TEXT:
        raise GateError(f"{label} too long")
    try:
        value.encode("utf-8", "strict")
    except UnicodeError as exc:
        raise GateError(f"{label} invalid UTF-8") from exc
    return value


def _identifier(value: Any, label: str) -> str:
    value = _text(value, label)
    if not _ID.fullmatch(value):
        raise GateError(f"{label} invalid")
    return value


def _digest(value: Any, label: str) -> str:
    value = _text(value, label)
    if not _HEX64.fullmatch(value):
        raise GateError(f"{label} must be lowercase sha256")
    return value


def _timestamp(value: Any, label: str) -> datetime:
    value = _text(value, label)
    if not _TS.fullmatch(value):
        raise GateError(f"{label} must be whole-second UTC")
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise GateError(f"{label} invalid timestamp") from exc
    if dt.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise GateError(f"{label} noncanonical timestamp")
    return dt


def _format_ts(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise GateError("evaluation time must be timezone-aware")
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0 or value > MAX_SAFE_INT:
        raise GateError(f"{label} must be positive safe integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0 or value > MAX_SAFE_INT:
        raise GateError(f"{label} must be nonnegative safe integer")
    return value


def _validate_term(row: Any) -> dict[str, Any]:
    row = _exact_keys(
        row,
        {
            "evidence_id",
            "subject_work_id",
            "subject_generation_sha256",
            "evidence_class",
            "source_id",
            "source_sha256",
            "observed_at_utc",
            "valid_until_utc",
            "amount_mode",
            "amount_minor",
            "currency",
        },
        "term evidence",
    )
    _identifier(row["evidence_id"], "evidence_id")
    _identifier(row["subject_work_id"], "term subject_work_id")
    _digest(row["subject_generation_sha256"], "term subject generation")
    if row["evidence_class"] not in EVIDENCE_CLASSES:
        raise GateError("invalid evidence_class")
    _identifier(row["source_id"], "source_id")
    _digest(row["source_sha256"], "source sha256")
    _timestamp(row["observed_at_utc"], "observed_at_utc")
    if row["valid_until_utc"] is not None:
        _timestamp(row["valid_until_utc"], "valid_until_utc")
    if row["amount_mode"] not in AMOUNT_MODES:
        raise GateError("invalid amount_mode")
    if row["amount_mode"] == "EXACT":
        _positive_int(row["amount_minor"], "amount_minor")
        if type(row["currency"]) is not str or not _CURRENCY.fullmatch(row["currency"]):
            raise GateError("currency must be three uppercase letters")
    else:
        if row["amount_minor"] is not None or row["currency"] is not None:
            raise GateError("AMOUNT_UNKNOWN must not carry amount/currency")
    return row


def _validate_outcome(row: Any) -> dict[str, Any]:
    row = _exact_keys(
        row,
        {
            "event_id",
            "subject_work_id",
            "subject_generation_sha256",
            "kind",
            "source_id",
            "source_sha256",
            "observed_at_utc",
        },
        "outcome evidence",
    )
    _identifier(row["event_id"], "event_id")
    _identifier(row["subject_work_id"], "outcome subject_work_id")
    _digest(row["subject_generation_sha256"], "outcome subject generation")
    if row["kind"] not in OUTCOME_KINDS:
        raise GateError("invalid outcome kind")
    _identifier(row["source_id"], "outcome source_id")
    _digest(row["source_sha256"], "outcome source sha256")
    _timestamp(row["observed_at_utc"], "outcome observed_at_utc")
    return row


def _validate_plan(plan: Any) -> dict[str, Any] | None:
    if plan is None:
        return None
    plan = _exact_keys(plan, {"milestone", "effort_ceiling_hours", "review_by_utc"}, "conversion_plan")
    _text(plan["milestone"], "conversion milestone")
    _positive_int(plan["effort_ceiling_hours"], "effort ceiling")
    _timestamp(plan["review_by_utc"], "review_by_utc")
    return plan


def _validate_packet(packet: Any) -> dict[str, Any]:
    packet = _freeze_json(packet)
    packet = _exact_keys(
        packet,
        {
            "schema",
            "subject_work_id",
            "subject_generation_sha256",
            "payoff_class",
            "evidence_scope_status",
            "term_evidence",
            "outcome_evidence",
            "conversion_plan",
        },
        "packet",
    )
    if packet["schema"] != SCHEMA_INPUT:
        raise GateError("wrong input schema")
    _identifier(packet["subject_work_id"], "subject_work_id")
    _digest(packet["subject_generation_sha256"], "subject generation")
    if packet["payoff_class"] not in PAYOFF_CLASSES:
        raise GateError("invalid payoff_class")
    if packet["evidence_scope_status"] not in SCOPE_STATUSES:
        raise GateError("invalid evidence_scope_status")
    if type(packet["term_evidence"]) is not list or len(packet["term_evidence"]) > MAX_ROWS:
        raise GateError("term_evidence must be bounded list")
    if type(packet["outcome_evidence"]) is not list or len(packet["outcome_evidence"]) > MAX_ROWS:
        raise GateError("outcome_evidence must be bounded list")
    ids: set[str] = set()
    for row in packet["term_evidence"]:
        _validate_term(row)
        if row["evidence_id"] in ids:
            raise GateError("duplicate evidence identity")
        ids.add(row["evidence_id"])
    for row in packet["outcome_evidence"]:
        _validate_outcome(row)
        if row["event_id"] in ids:
            raise GateError("duplicate evidence identity")
        ids.add(row["event_id"])
    _validate_plan(packet["conversion_plan"])
    return packet


def _receipt_projection(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": receipt["schema"],
        "compiler_id": receipt["compiler_id"],
        "subject_work_id": receipt["subject_work_id"],
        "subject_generation_sha256": receipt["subject_generation_sha256"],
        "payoff_class": receipt["payoff_class"],
        "state": receipt["state"],
        "reasons": receipt["reasons"],
        "input_digest_sha256": receipt["input_digest_sha256"],
        "term_fingerprint_sha256": receipt["term_fingerprint_sha256"],
        "conversion_plan_fingerprint_sha256": receipt["conversion_plan_fingerprint_sha256"],
        "authority": receipt["authority"],
    }


def _compile_at(packet: Any, now: datetime) -> dict[str, Any]:
    packet = _validate_packet(packet)
    now = now.astimezone(timezone.utc).replace(microsecond=0)
    subject = packet["subject_work_id"]
    generation = packet["subject_generation_sha256"]
    payoff_class = packet["payoff_class"]
    reasons: list[str] = []

    conflict = False
    stale = False
    expired = False
    future = False

    exact_terms: list[dict[str, Any]] = []
    matching_terms: list[dict[str, Any]] = []
    generic_terms: list[dict[str, Any]] = []

    for row in packet["term_evidence"]:
        if row["subject_work_id"] != subject or row["subject_generation_sha256"] != generation:
            conflict = True
            continue
        observed = _timestamp(row["observed_at_utc"], "observed_at_utc")
        if observed > now:
            future = True
        if now - observed > MAX_EVIDENCE_AGE:
            stale = True
        if row["valid_until_utc"] is not None:
            valid_until = _timestamp(row["valid_until_utc"], "valid_until_utc")
            if valid_until < observed:
                conflict = True
            if now >= valid_until:
                expired = True
        if row["evidence_class"] == payoff_class:
            matching_terms.append(row)
            if row["amount_mode"] == "EXACT":
                exact_terms.append(row)
        elif row["evidence_class"] == "GENERIC_CONTEXT":
            generic_terms.append(row)
        else:
            conflict = True

    outcomes: set[str] = set()
    for row in packet["outcome_evidence"]:
        if row["subject_work_id"] != subject or row["subject_generation_sha256"] != generation:
            conflict = True
            continue
        observed = _timestamp(row["observed_at_utc"], "outcome observed_at_utc")
        if observed > now:
            future = True
        if now - observed > MAX_EVIDENCE_AGE:
            stale = True
        outcomes.add(row["kind"])

    economics = {(r["amount_minor"], r["currency"]) for r in exact_terms}
    if len(economics) > 1:
        conflict = True
    if exact_terms and any(r["amount_mode"] == "AMOUNT_UNKNOWN" for r in matching_terms):
        conflict = True

    plan = packet["conversion_plan"]
    if plan is not None:
        review_by = _timestamp(plan["review_by_utc"], "review_by_utc")
        if now >= review_by:
            expired = True

    if conflict or future:
        state = "HOLD_EVIDENCE_CONFLICT"
        if conflict:
            reasons.append("EVIDENCE_CONFLICT")
        if future:
            reasons.append("FUTURE_EVIDENCE")
    elif "SETTLED" in outcomes:
        state = "HOLD_ALREADY_SETTLED"
        reasons.append("EXACT_WORK_GENERATION_SETTLED")
    elif "ACTIVE_DUPLICATE" in outcomes:
        state = "HOLD_ACTIVE_DUPLICATE"
        reasons.append("ACTIVE_DUPLICATE_OR_CUSTODY_CONFLICT")
    elif packet["evidence_scope_status"] != "COMPLETE":
        state = "HOLD_INCOMPLETE_EVIDENCE"
        reasons.append("EVIDENCE_SCOPE_PARTIAL")
    elif expired:
        state = "HOLD_EXPIRED"
        reasons.append("PAYOFF_PATH_EXPIRED")
    elif stale:
        state = "HOLD_STALE"
        reasons.append("PAYOFF_EVIDENCE_STALE")
    elif payoff_class in CASH_TERM_CLASSES:
        if not matching_terms:
            state = "HOLD_NO_PAYOFF_PATH"
            reasons.append("NO_CLASS_BOUND_COMPENSATION_TERM")
        elif any(r["amount_mode"] == "AMOUNT_UNKNOWN" for r in matching_terms):
            state = "HOLD_UNKNOWN_COMPENSATION"
            reasons.append("COMPENSATION_AMOUNT_UNKNOWN")
        elif not exact_terms:
            state = "HOLD_NO_PAYOFF_PATH"
            reasons.append("NO_EXACT_COMPENSATION_TERM")
        elif payoff_class == "PAID_WORK":
            state = "PAID_WORK"
            reasons.append("CURRENT_CLASS_BOUND_PAID_WORK_TERM")
        else:
            state = "PAYOFF_BOUND"
            reasons.append("CURRENT_CLASS_BOUND_COMPENSATION_TERM")
    elif payoff_class == "PRODUCT_CONVERSION":
        if matching_terms:
            if any(r["amount_mode"] == "AMOUNT_UNKNOWN" for r in matching_terms):
                state = "HOLD_UNKNOWN_COMPENSATION"
                reasons.append("COMPENSATION_AMOUNT_UNKNOWN")
            elif exact_terms:
                state = "PAYOFF_BOUND"
                reasons.append("CURRENT_PRODUCT_CONVERSION_CASH_TERM")
            else:
                state = "HOLD_NO_PAYOFF_PATH"
                reasons.append("NO_EXACT_PRODUCT_CONVERSION_TERM")
        elif plan is not None:
            state = "PAYOFF_BOUND"
            reasons.append("BOUNDED_PRODUCT_CONVERSION_MILESTONE")
        else:
            state = "HOLD_UNBOUNDED_STRATEGIC"
            reasons.append("PRODUCT_CONVERSION_REQUIRES_CASH_TERM_OR_BOUNDED_PLAN")
    elif payoff_class == "STRATEGIC_UNPAID":
        if plan is None:
            state = "HOLD_UNBOUNDED_STRATEGIC"
            reasons.append("STRATEGIC_UNPAID_REQUIRES_BOUNDED_PLAN")
        else:
            state = "STRATEGIC_UNPAID_BOUNDED"
            reasons.append("BOUNDED_STRATEGIC_CONVERSION_PLAN")
    else:
        state = "HOLD_INCOMPLETE_EVIDENCE"
        reasons.append("UNHANDLED_PAYOFF_CLASS")

    receipt: dict[str, Any] = {
        "schema": SCHEMA_RECEIPT,
        "compiler_id": COMPILER_ID,
        "subject_work_id": subject,
        "subject_generation_sha256": generation,
        "payoff_class": payoff_class,
        "evaluated_at_utc": _format_ts(now),
        "state": state,
        "reasons": reasons,
        "input_digest_sha256": _sha(packet),
        "term_fingerprint_sha256": _sha(packet["term_evidence"]),
        "conversion_plan_fingerprint_sha256": None if plan is None else _sha(plan),
        "authority": dict(_AUTHORITY),
    }
    receipt["receipt_digest_sha256"] = _sha(receipt)
    return receipt


_NOW: Callable[[], datetime] = lambda: datetime.now(timezone.utc)


def compile_current(packet: Any) -> dict[str, Any]:
    frozen = _freeze_json(packet)
    return _compile_at(frozen, _NOW())


def _validate_receipt_shape(receipt: Any) -> dict[str, Any]:
    receipt = _freeze_json(receipt)
    receipt = _exact_keys(
        receipt,
        {
            "schema",
            "compiler_id",
            "subject_work_id",
            "subject_generation_sha256",
            "payoff_class",
            "evaluated_at_utc",
            "state",
            "reasons",
            "input_digest_sha256",
            "term_fingerprint_sha256",
            "conversion_plan_fingerprint_sha256",
            "authority",
            "receipt_digest_sha256",
        },
        "receipt",
    )
    if receipt["schema"] != SCHEMA_RECEIPT or receipt["compiler_id"] != COMPILER_ID:
        raise GateError("wrong receipt schema/compiler")
    _identifier(receipt["subject_work_id"], "receipt subject_work_id")
    _digest(receipt["subject_generation_sha256"], "receipt subject generation")
    if receipt["payoff_class"] not in PAYOFF_CLASSES:
        raise GateError("receipt payoff_class invalid")
    _timestamp(receipt["evaluated_at_utc"], "receipt evaluated_at_utc")
    _text(receipt["state"], "receipt state")
    if type(receipt["reasons"]) is not list or not all(type(x) is str and x for x in receipt["reasons"]):
        raise GateError("receipt reasons invalid")
    _digest(receipt["input_digest_sha256"], "input digest")
    _digest(receipt["term_fingerprint_sha256"], "term fingerprint")
    if receipt["conversion_plan_fingerprint_sha256"] is not None:
        _digest(receipt["conversion_plan_fingerprint_sha256"], "plan fingerprint")
    if receipt["authority"] != _AUTHORITY:
        raise GateError("authority ceiling mismatch")
    _digest(receipt["receipt_digest_sha256"], "receipt digest")
    without = dict(receipt)
    digest = without.pop("receipt_digest_sha256")
    if _sha(without) != digest:
        raise GateError("receipt digest mismatch")
    return receipt


def verify_integrity(packet: Any, receipt: Any) -> bool:
    frozen_packet = _freeze_json(packet)
    frozen_receipt = _validate_receipt_shape(receipt)
    evaluated = _timestamp(frozen_receipt["evaluated_at_utc"], "receipt evaluated_at_utc")
    expected = _compile_at(frozen_packet, evaluated)
    return _canonical_bytes(expected) == _canonical_bytes(frozen_receipt)


def _verify_current_at(packet: Any, receipt: Any, now: datetime) -> bool:
    frozen_packet = _freeze_json(packet)
    frozen_receipt = _validate_receipt_shape(receipt)
    if not verify_integrity(frozen_packet, frozen_receipt):
        return False
    evaluated = _timestamp(frozen_receipt["evaluated_at_utc"], "receipt evaluated_at_utc")
    now = now.astimezone(timezone.utc).replace(microsecond=0)
    if evaluated > now:
        return False
    current = _compile_at(frozen_packet, now)
    return _canonical_bytes(_receipt_projection(current)) == _canonical_bytes(_receipt_projection(frozen_receipt))


def verify_current(packet: Any, receipt: Any) -> bool:
    frozen_packet = _freeze_json(packet)
    frozen_receipt = _freeze_json(receipt)
    return _verify_current_at(frozen_packet, frozen_receipt, _NOW())
