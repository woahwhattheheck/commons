from __future__ import annotations

from datetime import datetime
from typing import Any

from firewall_codec import (
    DECISION_SCHEMA, DECISION_KEYS, FirewallError, canonical_json, sha256_hex,
    _digest, _exact_keys, _process_utc_now, _utc, _utc_text,
)
from firewall_model import compute_dedupe_key, normalize_packet


def _hard_false_authority(_items=(
    ("package_performs_send", False),
    ("buyer_qualified_or_interested", False),
    ("submission_authorized", False),
    ("signature_or_contract_authority", False),
    ("award_or_payment_authority", False),
    ("cash_or_revenue_authority", False),
)) -> dict[str, bool]:
    return dict(_items)


def _evaluate(
    normalized: dict[str, Any], as_of: datetime, *, current_process: bool,
    _authority_factory=_hard_false_authority,
) -> dict[str, Any]:
    source = normalized["source_packet"]
    contact = normalized["contact"]
    lease = normalized["writer_lease"]
    dedupe_key = compute_dedupe_key(source, contact)
    reasons: list[str] = []
    observed = _utc(source["observed_at"], "observed_at")
    if observed > as_of: reasons.append("HOLD_SOURCE_FUTURE")
    deadline = _utc(source["deadline_at"], "deadline_at")
    if int((deadline - as_of).total_seconds()) < source["min_runway_seconds"]: reasons.append("HOLD_RUNWAY")
    if source["registration_required"] and source["registration_state"] != "READY": reasons.append("HOLD_REGISTRATION")
    required_gates = [g for g in normalized["qualifications"] if g["required_for_outreach"]]
    if any(g["disposition"] == "UNSATISFIED" for g in required_gates): reasons.append("HOLD_QUALIFICATION_UNSATISFIED")
    if any(g["disposition"] == "UNKNOWN" for g in required_gates): reasons.append("HOLD_QUALIFICATION_UNKNOWN")
    if contact["relationship_state"] in {"DNR", "BOUNCE", "SENT_DNR"}: reasons.append("HOLD_RELATIONSHIP")
    qualified = not reasons
    send_reasons: list[str] = []
    if not current_process: send_reasons.append("HOLD_HISTORICAL_EVALUATION")
    if lease is None:
        send_reasons.append("HOLD_WRITER_LEASE_MISSING")
    else:
        if not lease["authority_authenticated"]: send_reasons.append("HOLD_WRITER_LEASE_UNAUTHENTICATED")
        if lease["status"] != "GO": send_reasons.append("HOLD_WRITER_LEASE_STATUS")
        if lease["collision_key"] != dedupe_key: send_reasons.append("HOLD_WRITER_LEASE_KEY")
        if lease["seat"] != normalized["requesting_seat"]: send_reasons.append("HOLD_WRITER_LEASE_SEAT")
        if lease["session_nonce"] != normalized["session_nonce"]: send_reasons.append("HOLD_WRITER_LEASE_SESSION")
        issued = _utc(lease["issued_at"], "lease.issued_at")
        expires = _utc(lease["expires_at"], "lease.expires_at")
        if as_of < issued: send_reasons.append("HOLD_WRITER_LEASE_NOT_YET_VALID")
        if as_of >= expires: send_reasons.append("HOLD_WRITER_LEASE_EXPIRED")
    authorized = qualified and not send_reasons
    decision: dict[str, Any] = {
        "schema": DECISION_SCHEMA,
        "evaluated_at": _utc_text(as_of),
        "evaluation_mode": "CURRENT_PROCESS" if current_process else "HISTORICAL_REVIEW_ONLY",
        "packet_digest": sha256_hex(canonical_json(normalized)),
        "source_packet_sha256": normalized["source_packet_sha256"],
        "dedupe_key": dedupe_key,
        "qualification_state": "QUALIFIED_FOR_OWNER_REVIEW" if qualified else "HOLD",
        "qualified_for_owner_review": qualified,
        "send_state": "AUTHORIZED_TO_SEND" if authorized else "NOT_AUTHORIZED_TO_SEND",
        "authorized_to_send": authorized,
        "hold_reasons": sorted(set(reasons + send_reasons)),
        "authority": _authority_factory(),
    }
    decision["receipt_sha256"] = sha256_hex(canonical_json(decision))
    return decision


def compile_historical(payload: Any, *, as_of: str, _normalize=normalize_packet, _evaluate_fn=_evaluate) -> dict[str, Any]:
    return _evaluate_fn(_normalize(payload), _utc(as_of, "as_of"), current_process=False)


def compile_current(payload: Any, _normalize=normalize_packet, _evaluate_fn=_evaluate, _now=_process_utc_now) -> dict[str, Any]:
    return _evaluate_fn(_normalize(payload), _now(), current_process=True)


def verify_receipt(
    payload: Any, decision: Any,
    _normalize=normalize_packet, _evaluate_fn=_evaluate, _now=_process_utc_now,
    _authority_factory=_hard_false_authority,
) -> bool:
    normalized = _normalize(payload)
    row = _exact_keys(decision, DECISION_KEYS, "decision")
    if row["schema"] != DECISION_SCHEMA: raise FirewallError("wrong decision schema")
    supplied = _digest(row["receipt_sha256"], "receipt_sha256")
    unsigned = dict(row); unsigned.pop("receipt_sha256")
    if sha256_hex(canonical_json(unsigned)) != supplied: raise FirewallError("receipt digest mismatch")
    if row["authority"] != _authority_factory(): raise FirewallError("authority ceiling changed")
    mode = row["evaluation_mode"]
    if mode not in {"CURRENT_PROCESS", "HISTORICAL_REVIEW_ONLY"}: raise FirewallError("unknown evaluation mode")
    original = _evaluate_fn(normalized, _utc(row["evaluated_at"], "evaluated_at"), current_process=(mode == "CURRENT_PROCESS"))
    if canonical_json(original) != canonical_json(row): raise FirewallError("semantic receipt mismatch")
    if mode == "CURRENT_PROCESS" and row["authorized_to_send"]:
        fresh = _evaluate_fn(normalized, _now(), current_process=True)
        if not fresh["authorized_to_send"]: raise FirewallError("current send authorization is stale")
    return True
