#!/usr/bin/env python3
"""Deterministic, side-effect-free revenue closure queue compiler.

This module consumes explicit commercial evidence and emits the next bounded
commercial action without contacting customers, creating checkout rails,
moving money, or claiming revenue.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")

QUALIFICATIONS = {"ACTIONABLE", "HOLD", "REJECT"}
CONTACT_STATES = {
    "NEVER_CONTACTED",
    "SENT_NO_RESPONSE",
    "REPLIED",
    "BOUNCED",
    "DO_NOT_CONTACT",
}
OFFER_STATES = {"NONE", "DRAFT", "SENT", "ACCEPTED", "REJECTED", "EXPIRED"}
COLLECTION_STATES = {"NONE", "READY", "ACTIVE"}
PAYMENT_STATES = {"NONE", "PENDING", "AUTHORIZED", "SETTLED", "FAILED", "REFUNDED"}
DELIVERY_STATES = {"NOT_READY", "READY", "DELIVERED", "ACCEPTED", "REJECTED"}
SETTLEMENT_STATES = {"NOT_EARNED", "EARNED", "SETTLED", "REVERSED"}
PAYMENT_TIMINGS = {"BEFORE_DELIVERY", "AFTER_DELIVERY"}

ACTION_PRIORITIES = {
    "HOLD_STALE_EVIDENCE": 0,
    "HOLD_QUALIFICATION": 5,
    "STOP_REJECTED": 0,
    "STOP_DNR": 0,
    "STOP_DEADLINE_PASSED": 0,
    "CLOSED_LOST": 0,
    "CLOSED_REVERSED": 0,
    "CLOSED_WON": 0,
    "WAIT_FOLLOWUP": 20,
    "AWAIT_QUOTE_DECISION": 30,
    "AWAIT_PAYMENT": 45,
    "AWAIT_DELIVERY_ACCEPTANCE": 45,
    "INITIAL_CONTACT_READY": 60,
    "CONTACT_ROUTE_REPAIR": 65,
    "FOLLOW_UP_READY": 70,
    "REQUOTE_READY": 75,
    "QUOTE_READY": 80,
    "PREPARE_DELIVERY": 82,
    "FULFILLMENT_READY": 88,
    "ACTIVATE_COLLECTION_RAIL": 90,
    "COLLECTION_RAIL_REQUIRED": 92,
    "PAYMENT_RECOVERY": 95,
    "REQUEST_PAYMENT": 96,
    "EARNINGS_EVIDENCE_REQUIRED": 97,
    "SETTLEMENT_PENDING": 100,
}

NON_EXECUTABLE_ACTIONS = {
    "HOLD_STALE_EVIDENCE",
    "HOLD_QUALIFICATION",
    "STOP_REJECTED",
    "STOP_DNR",
    "STOP_DEADLINE_PASSED",
    "CLOSED_LOST",
    "CLOSED_REVERSED",
    "CLOSED_WON",
    "WAIT_FOLLOWUP",
    "AWAIT_QUOTE_DECISION",
    "AWAIT_PAYMENT",
    "AWAIT_DELIVERY_ACCEPTANCE",
}


class ContractError(ValueError):
    """Raised when the supplied evidence is malformed or contradictory."""


def _reject_constant(value: str) -> None:
    raise ContractError(f"non-finite JSON number is forbidden: {value}")


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_strict(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except ContractError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise ContractError(f"invalid JSON: {exc}") from exc


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ContractError(f"{field} must be a UTC timestamp string")
    if not value.endswith("Z"):
        raise ContractError(f"{field} must end in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError(f"{field} is not a valid timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise ContractError(f"{field} must be UTC")
    if parsed.microsecond:
        raise ContractError(f"{field} must not include fractional seconds")
    return parsed


def render_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def require_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{field} must be an array")
    return value


def require_exact_keys(
    value: dict[str, Any], field: str, required: set[str], optional: set[str] = frozenset()
) -> None:
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        raise ContractError(f"{field} missing keys: {', '.join(sorted(missing))}")
    if extra:
        raise ContractError(f"{field} has unsupported keys: {', '.join(sorted(extra))}")


def require_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ContractError(f"{field} must be a boolean")
    return value


def require_int(value: Any, field: str, minimum: int = 0, maximum: int | None = None) -> int:
    if type(value) is not int:
        raise ContractError(f"{field} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        high = f"..{maximum}" if maximum is not None else "+"
        raise ContractError(f"{field} must be in range {minimum}{high}")
    return value


def require_enum(value: Any, field: str, allowed: set[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ContractError(f"{field} must be one of {', '.join(sorted(allowed))}")
    return value


def require_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ContractError(f"{field} must be a safe non-empty identifier")
    return value


def require_currency(value: Any, field: str) -> str:
    if not isinstance(value, str) or not CURRENCY_RE.fullmatch(value):
        raise ContractError(f"{field} must be a 3-letter uppercase currency")
    return value


def _optional_timestamp(row: dict[str, Any], key: str, field: str) -> datetime | None:
    if key not in row or row[key] is None:
        return None
    return parse_utc(row[key], f"{field}.{key}")


def validate_input(payload: Any, as_of: datetime) -> tuple[dict[str, Any], datetime, bool]:
    root = require_dict(payload, "root")
    require_exact_keys(
        root,
        "root",
        {"schema_version", "evidence_generated_at", "max_age_seconds", "opportunities"},
    )
    if require_int(root["schema_version"], "schema_version", 1, 1) != SCHEMA_VERSION:
        raise ContractError("unsupported schema_version")
    generated_at = parse_utc(root["evidence_generated_at"], "evidence_generated_at")
    if generated_at > as_of:
        raise ContractError("evidence_generated_at cannot be in the future")
    max_age = require_int(root["max_age_seconds"], "max_age_seconds", 60, 31 * 86400)
    fresh = (as_of - generated_at).total_seconds() <= max_age

    opportunities = require_list(root["opportunities"], "opportunities")
    if len(opportunities) > 10_000:
        raise ContractError("opportunities exceeds 10000 rows")
    seen: set[str] = set()
    for index, item in enumerate(opportunities):
        validate_opportunity(item, index)
        opp_id = item["opportunity_id"]
        if opp_id in seen:
            raise ContractError(f"duplicate opportunity_id: {opp_id}")
        seen.add(opp_id)
    return root, generated_at, fresh


def validate_opportunity(value: Any, index: int) -> None:
    field = f"opportunities[{index}]"
    row = require_dict(value, field)
    require_exact_keys(
        row,
        field,
        {
            "opportunity_id",
            "expected_value_cents",
            "currency",
            "qualification",
            "contact",
            "commercial",
            "policy",
        },
        {"deadline_at"},
    )
    require_id(row["opportunity_id"], f"{field}.opportunity_id")
    require_int(row["expected_value_cents"], f"{field}.expected_value_cents", 0, 10**15)
    require_currency(row["currency"], f"{field}.currency")
    require_enum(row["qualification"], f"{field}.qualification", QUALIFICATIONS)
    if "deadline_at" in row and row["deadline_at"] is not None:
        parse_utc(row["deadline_at"], f"{field}.deadline_at")

    contact = require_dict(row["contact"], f"{field}.contact")
    require_exact_keys(
        contact,
        f"{field}.contact",
        {"state", "do_not_resend"},
        {"last_contact_at", "followup_not_before"},
    )
    state = require_enum(contact["state"], f"{field}.contact.state", CONTACT_STATES)
    require_bool(contact["do_not_resend"], f"{field}.contact.do_not_resend")
    last_contact = _optional_timestamp(contact, "last_contact_at", f"{field}.contact")
    followup_not_before = _optional_timestamp(contact, "followup_not_before", f"{field}.contact")
    if state in {"SENT_NO_RESPONSE", "REPLIED", "BOUNCED"} and last_contact is None:
        raise ContractError(f"{field}.contact.last_contact_at is required for {state}")
    if state == "NEVER_CONTACTED" and last_contact is not None:
        raise ContractError(f"{field}.contact.last_contact_at contradicts NEVER_CONTACTED")
    if followup_not_before is not None and last_contact is not None and followup_not_before < last_contact:
        raise ContractError(f"{field}.contact.followup_not_before cannot precede last_contact_at")

    commercial = require_dict(row["commercial"], f"{field}.commercial")
    require_exact_keys(
        commercial,
        f"{field}.commercial",
        {"offer", "collection", "payment", "delivery", "settlement"},
    )
    offer = require_enum(commercial["offer"], f"{field}.commercial.offer", OFFER_STATES)
    collection = require_enum(
        commercial["collection"], f"{field}.commercial.collection", COLLECTION_STATES
    )
    payment = require_enum(commercial["payment"], f"{field}.commercial.payment", PAYMENT_STATES)
    delivery = require_enum(
        commercial["delivery"], f"{field}.commercial.delivery", DELIVERY_STATES
    )
    settlement = require_enum(
        commercial["settlement"], f"{field}.commercial.settlement", SETTLEMENT_STATES
    )

    policy = require_dict(row["policy"], f"{field}.policy")
    require_exact_keys(
        policy,
        f"{field}.policy",
        {"followup_cooldown_seconds", "payment_timing", "requires_delivery_acceptance"},
    )
    require_int(
        policy["followup_cooldown_seconds"],
        f"{field}.policy.followup_cooldown_seconds",
        0,
        31 * 86400,
    )
    require_enum(policy["payment_timing"], f"{field}.policy.payment_timing", PAYMENT_TIMINGS)
    require_bool(
        policy["requires_delivery_acceptance"],
        f"{field}.policy.requires_delivery_acceptance",
    )

    _validate_commercial_consistency(field, offer, collection, payment, delivery, settlement)


def _validate_commercial_consistency(
    field: str,
    offer: str,
    collection: str,
    payment: str,
    delivery: str,
    settlement: str,
) -> None:
    if payment in {"PENDING", "AUTHORIZED", "SETTLED", "FAILED", "REFUNDED"} and offer != "ACCEPTED":
        raise ContractError(f"{field}: payment evidence requires ACCEPTED offer")
    if payment in {"PENDING", "AUTHORIZED", "SETTLED", "FAILED", "REFUNDED"} and collection != "ACTIVE":
        raise ContractError(f"{field}: payment evidence requires ACTIVE collection")
    if delivery in {"DELIVERED", "ACCEPTED", "REJECTED"} and offer != "ACCEPTED":
        raise ContractError(f"{field}: delivered work requires ACCEPTED offer")
    if delivery == "ACCEPTED" and settlement == "NOT_EARNED":
        raise ContractError(f"{field}: accepted delivery cannot remain NOT_EARNED")
    if settlement in {"EARNED", "SETTLED"} and delivery not in {"DELIVERED", "ACCEPTED"}:
        raise ContractError(f"{field}: earned/settled state requires delivered work")
    if settlement == "SETTLED" and payment != "SETTLED":
        raise ContractError(f"{field}: SETTLED revenue requires SETTLED payment")
    if settlement == "REVERSED" and payment not in {"REFUNDED", "SETTLED"}:
        raise ContractError(f"{field}: REVERSED settlement requires settled/refunded payment")


def _decision(
    action: str,
    reason: str,
    *,
    not_before: datetime | None = None,
    blocking: list[str] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "action": action,
        "priority": ACTION_PRIORITIES[action],
        "action_ready": action not in NON_EXECUTABLE_ACTIONS,
        "reason": reason,
        "blocking_reasons": blocking or [],
    }
    if not_before is not None:
        result["not_before"] = render_utc(not_before)
    return result


def decide(row: dict[str, Any], as_of: datetime, evidence_fresh: bool) -> dict[str, Any]:
    if not evidence_fresh:
        return _decision("HOLD_STALE_EVIDENCE", "source evidence exceeded max_age_seconds")

    commercial = row["commercial"]
    offer = commercial["offer"]
    collection = commercial["collection"]
    payment = commercial["payment"]
    delivery = commercial["delivery"]
    settlement = commercial["settlement"]
    policy = row["policy"]

    # Fresh explicit terminal evidence outranks operational gates. Otherwise a
    # settled or rejected opportunity could be mislabeled as merely expired or
    # do-not-resend, which corrupts closure accounting.
    if settlement == "REVERSED" or payment == "REFUNDED":
        return _decision("CLOSED_REVERSED", "money state is reversed/refunded")
    if settlement == "SETTLED":
        return _decision("CLOSED_WON", "payment and settlement are both settled")
    if delivery == "REJECTED" or offer == "REJECTED":
        return _decision("CLOSED_LOST", "buyer explicitly rejected the offer or delivery")

    qualification = row["qualification"]
    if qualification == "REJECT":
        return _decision("STOP_REJECTED", "qualification explicitly rejected the opportunity")
    if qualification == "HOLD":
        return _decision("HOLD_QUALIFICATION", "qualification is explicitly on hold")

    deadline = parse_utc(row["deadline_at"], "deadline_at") if row.get("deadline_at") else None
    if deadline is not None and as_of > deadline:
        return _decision("STOP_DEADLINE_PASSED", "opportunity deadline has passed")

    contact = row["contact"]
    contact_state = contact["state"]
    dnr = contact["do_not_resend"]
    if contact_state == "DO_NOT_CONTACT":
        return _decision("STOP_DNR", "contact state forbids further contact")
    if dnr and contact_state in {"NEVER_CONTACTED", "SENT_NO_RESPONSE", "BOUNCED"}:
        return _decision("STOP_DNR", "do_not_resend forbids another unsolicited transport")

    if contact_state == "NEVER_CONTACTED":
        return _decision("INITIAL_CONTACT_READY", "qualified opportunity has not been contacted")
    if contact_state == "BOUNCED":
        return _decision("CONTACT_ROUTE_REPAIR", "prior transport bounced; use a different verified route")
    if contact_state == "SENT_NO_RESPONSE":
        last = parse_utc(contact["last_contact_at"], "contact.last_contact_at")
        policy_not_before = last + timedelta(seconds=policy["followup_cooldown_seconds"])
        explicit = (
            parse_utc(contact["followup_not_before"], "contact.followup_not_before")
            if contact.get("followup_not_before")
            else None
        )
        not_before = max(policy_not_before, explicit) if explicit else policy_not_before
        if as_of < not_before:
            return _decision(
                "WAIT_FOLLOWUP",
                "cooldown or explicit follow-up fence has not elapsed",
                not_before=not_before,
            )
        return _decision("FOLLOW_UP_READY", "follow-up is permitted by explicit contact policy")

    # From here the buyer has replied, so commercial evidence controls the next step.
    if offer in {"NONE", "DRAFT"}:
        return _decision("QUOTE_READY", "buyer replied and no sent quote is awaiting decision")
    if offer == "SENT":
        return _decision("AWAIT_QUOTE_DECISION", "quote is sent but not accepted/rejected")
    if offer == "EXPIRED":
        return _decision("REQUOTE_READY", "buyer replied but the previous quote expired")

    # ACCEPTED offer.
    if collection == "NONE":
        return _decision("COLLECTION_RAIL_REQUIRED", "accepted offer has no collection rail")
    if collection == "READY":
        return _decision("ACTIVATE_COLLECTION_RAIL", "collection rail is prepared but not active")

    timing = policy["payment_timing"]
    requires_acceptance = policy["requires_delivery_acceptance"]

    def delivery_next() -> dict[str, Any] | None:
        if delivery == "NOT_READY":
            return _decision("PREPARE_DELIVERY", "accepted work is not delivery-ready")
        if delivery == "READY":
            return _decision("FULFILLMENT_READY", "delivery is ready to execute")
        if delivery == "DELIVERED" and requires_acceptance:
            return _decision("AWAIT_DELIVERY_ACCEPTANCE", "delivery acceptance is required")
        if delivery in {"DELIVERED", "ACCEPTED"}:
            if settlement == "NOT_EARNED":
                return _decision(
                    "EARNINGS_EVIDENCE_REQUIRED",
                    "delivery is complete but earned-state evidence is absent",
                )
            if settlement == "EARNED":
                return _decision("SETTLEMENT_PENDING", "earned value has not settled")
        return None

    def payment_next() -> dict[str, Any] | None:
        if payment == "NONE":
            return _decision("REQUEST_PAYMENT", "accepted offer has an active rail but no payment")
        if payment in {"PENDING", "AUTHORIZED"}:
            return _decision("AWAIT_PAYMENT", "payment is not settled")
        if payment == "FAILED":
            return _decision("PAYMENT_RECOVERY", "payment failed on an active rail")
        return None

    if timing == "BEFORE_DELIVERY":
        pay = payment_next()
        if payment != "SETTLED" and pay is not None:
            return pay
        nxt = delivery_next()
        if nxt is not None:
            return nxt
    else:
        nxt = delivery_next()
        if delivery not in {"DELIVERED", "ACCEPTED"} and nxt is not None:
            return nxt
        pay = payment_next()
        if payment != "SETTLED" and pay is not None:
            return pay
        if nxt is not None:
            return nxt

    # This should only be reachable for a state combination validated above but
    # missing an explicit evidence edge.
    return _decision(
        "EARNINGS_EVIDENCE_REQUIRED",
        "commercial evidence is internally valid but lacks a terminal earning edge",
    )


def _priority_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    # Highest priority first, then nearest deadline, then highest expected value,
    # then stable opportunity id. Missing deadlines sort last.
    deadline = row.get("deadline_at")
    deadline_key = deadline if deadline is not None else "9999-12-31T23:59:59Z"
    return (
        -row["decision"]["priority"],
        deadline_key,
        -row["expected_value_cents"],
        row["opportunity_id"],
    )


def compile_queue(payload: Any, as_of: datetime) -> dict[str, Any]:
    root, generated_at, fresh = validate_input(payload, as_of)
    rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for item in root["opportunities"]:
        decision = decide(item, as_of, fresh)
        counts[decision["action"]] = counts.get(decision["action"], 0) + 1
        row = {
            "opportunity_id": item["opportunity_id"],
            "expected_value_cents": item["expected_value_cents"],
            "currency": item["currency"],
            "deadline_at": item.get("deadline_at"),
            "decision": decision,
            "evidence_sha256": digest(item),
        }
        rows.append(row)
    rows.sort(key=_priority_sort_key)

    actionable_value_by_currency: dict[str, int] = {}
    for row in rows:
        if row["decision"]["action_ready"]:
            currency = row["currency"]
            actionable_value_by_currency[currency] = (
                actionable_value_by_currency.get(currency, 0) + row["expected_value_cents"]
            )

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "REVENUE_CLOSURE_QUEUE",
        "as_of": render_utc(as_of),
        "evidence_generated_at": render_utc(generated_at),
        "evidence_fresh": fresh,
        "authoritative": fresh,
        "input_sha256": digest(root),
        "summary": {
            "opportunity_count": len(rows),
            "action_counts": dict(sorted(counts.items())),
            "actionable_value_cents_by_currency": dict(sorted(actionable_value_by_currency.items())),
        },
        "queue": rows,
    }


def _load_path(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"unable to read input: {exc}") from exc
    return loads_strict(text)


def _write_output(path: Path | None, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if path is None:
        print(text, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8", newline="\n")
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="strict JSON evidence input")
    parser.add_argument("--as-of", required=True, help="deterministic UTC evaluation time")
    parser.add_argument("--output", type=Path, help="optional atomic JSON output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        as_of = parse_utc(args.as_of, "--as-of")
        result = compile_queue(_load_path(args.input), as_of)
        _write_output(args.output, result)
    except ContractError as exc:
        print(f"revenue-closure: {exc}", file=__import__("sys").stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
