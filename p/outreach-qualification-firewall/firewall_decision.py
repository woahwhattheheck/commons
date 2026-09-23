from __future__ import annotations

import time as _time_module
from datetime import datetime, timezone
from typing import Any

from firewall_codec import (
    DECISION_SCHEMA,
    DECISION_KEYS,
    MAX_RELATIONSHIP_AGE_SECONDS,
    FirewallError,
    canonical_json,
    sha256_hex,
    _digest,
    _exact_keys,
    _utc,
    _utc_text,
)
from firewall_model import compute_dedupe_key, normalize_packet


def _hard_false_authority() -> dict[str, bool]:
    return {
        "package_performs_send": False,
        "buyer_qualified_or_interested": False,
        "submission_authorized": False,
        "signature_or_contract_authority": False,
        "award_or_payment_authority": False,
        "cash_or_revenue_authority": False,
    }


def _make_current_clock(clock, fromtimestamp, utc_zone):
    def current_clock() -> datetime:
        return fromtimestamp(clock(), utc_zone).replace(microsecond=0)
    return current_clock


_CURRENT_CLOCK = _make_current_clock(
    _time_module.time,
    datetime.fromtimestamp,
    timezone.utc,
)


def _make_evaluator(
    authority_factory,
    dedupe,
    utc,
    utc_text,
    canonical,
    sha,
    max_relationship_age,
    decision_schema,
):
    def evaluate(
        normalized: dict[str, Any],
        as_of: datetime,
        *,
        current_process: bool,
    ) -> dict[str, Any]:
        source = normalized["source_packet"]
        contact = normalized["contact"]
        identity = normalized["identity_binding"]
        lease = normalized["writer_lease"]
        dedupe_key = dedupe(source, contact)
        reasons: list[str] = []

        observed = utc(source["observed_at"], "observed_at")
        if observed > as_of:
            reasons.append("HOLD_SOURCE_FUTURE")
        deadline = utc(source["deadline_at"], "deadline_at")
        if int((deadline - as_of).total_seconds()) < source["min_runway_seconds"]:
            reasons.append("HOLD_RUNWAY")
        if source["registration_required"] and source["registration_state"] != "READY":
            reasons.append("HOLD_REGISTRATION")

        required_gates = [
            gate
            for gate in normalized["qualifications"]
            if gate["required_for_outreach"]
        ]
        if any(gate["disposition"] == "UNSATISFIED" for gate in required_gates):
            reasons.append("HOLD_QUALIFICATION_UNSATISFIED")
        if any(gate["disposition"] == "UNKNOWN" for gate in required_gates):
            reasons.append("HOLD_QUALIFICATION_UNKNOWN")

        identity_observed = utc(identity["observed_at"], "identity.observed_at")
        identity_valid_until = utc(identity["valid_until"], "identity.valid_until")
        if not identity["authority_authenticated"]:
            reasons.append("HOLD_IDENTITY_AUTHORITY")
        if identity_observed > as_of:
            reasons.append("HOLD_IDENTITY_FUTURE")
        if as_of >= identity_valid_until:
            reasons.append("HOLD_IDENTITY_EXPIRED")

        relationship_observed = utc(
            contact["relationship_observed_at"],
            "relationship_observed_at",
        )
        relationship_valid_until = utc(
            contact["relationship_valid_until"],
            "relationship_valid_until",
        )
        if not contact["relationship_authority_authenticated"]:
            reasons.append("HOLD_RELATIONSHIP_AUTHORITY")
        if relationship_observed > as_of:
            reasons.append("HOLD_RELATIONSHIP_FUTURE")
        if (
            as_of >= relationship_valid_until
            or (as_of - relationship_observed).total_seconds() > max_relationship_age
        ):
            reasons.append("HOLD_RELATIONSHIP_STALE")
        if contact["relationship_state"] in {"DNR", "BOUNCE", "SENT_DNR"}:
            reasons.append("HOLD_RELATIONSHIP")

        qualified = not reasons
        send_reasons: list[str] = []
        if not current_process:
            send_reasons.append("HOLD_HISTORICAL_EVALUATION")
        if lease is None:
            send_reasons.append("HOLD_WRITER_LEASE_MISSING")
        else:
            if not lease["authority_authenticated"]:
                send_reasons.append("HOLD_WRITER_LEASE_UNAUTHENTICATED")
            if lease["status"] != "GO":
                send_reasons.append("HOLD_WRITER_LEASE_STATUS")
            if lease["collision_key"] != dedupe_key:
                send_reasons.append("HOLD_WRITER_LEASE_KEY")
            if lease["seat"] != normalized["requesting_seat"]:
                send_reasons.append("HOLD_WRITER_LEASE_SEAT")
            if lease["session_nonce"] != normalized["session_nonce"]:
                send_reasons.append("HOLD_WRITER_LEASE_SESSION")
            issued = utc(lease["issued_at"], "lease.issued_at")
            expires = utc(lease["expires_at"], "lease.expires_at")
            if as_of < issued:
                send_reasons.append("HOLD_WRITER_LEASE_NOT_YET_VALID")
            if as_of >= expires:
                send_reasons.append("HOLD_WRITER_LEASE_EXPIRED")
            if current_process and relationship_observed < issued:
                send_reasons.append("HOLD_RELATIONSHIP_PRECEDES_LEASE")

        authorized = qualified and not send_reasons
        decision: dict[str, Any] = {
            "schema": decision_schema,
            "evaluated_at": utc_text(as_of),
            "evaluation_mode": (
                "CURRENT_PROCESS"
                if current_process
                else "HISTORICAL_REVIEW_ONLY"
            ),
            "packet_digest": sha(canonical(normalized)),
            "source_packet_sha256": normalized["source_packet_sha256"],
            "dedupe_key": dedupe_key,
            "qualification_state": (
                "QUALIFIED_FOR_OWNER_REVIEW" if qualified else "HOLD"
            ),
            "qualified_for_owner_review": qualified,
            "send_state": (
                "AUTHORIZED_TO_SEND"
                if authorized
                else "NOT_AUTHORIZED_TO_SEND"
            ),
            "authorized_to_send": authorized,
            "hold_reasons": sorted(set(reasons + send_reasons)),
            "authority": authority_factory(),
        }
        decision["receipt_sha256"] = sha(canonical(decision))
        return decision

    return evaluate


_evaluate = _make_evaluator(
    _hard_false_authority,
    compute_dedupe_key,
    _utc,
    _utc_text,
    canonical_json,
    sha256_hex,
    MAX_RELATIONSHIP_AGE_SECONDS,
    DECISION_SCHEMA,
)


def _make_compile_historical(normalize, evaluate, utc):
    def compile_historical(payload: Any, *, as_of: str) -> dict[str, Any]:
        return evaluate(
            normalize(payload),
            utc(as_of, "as_of"),
            current_process=False,
        )

    return compile_historical


compile_historical = _make_compile_historical(
    normalize_packet,
    _evaluate,
    _utc,
)


def _make_compile_current(normalize, evaluate, current_clock):
    def compile_current(payload: Any) -> dict[str, Any]:
        return evaluate(
            normalize(payload),
            current_clock(),
            current_process=True,
        )

    return compile_current


compile_current = _make_compile_current(
    normalize_packet,
    _evaluate,
    _CURRENT_CLOCK,
)


def _make_verify_receipt(
    normalize,
    evaluate,
    current_clock,
    authority_factory,
    exact,
    decision_keys,
    decision_schema,
    digest,
    canonical,
    sha,
    utc,
    err,
):
    keys = frozenset(decision_keys)

    def verify_receipt(payload: Any, decision: Any) -> bool:
        normalized = normalize(payload)
        row = exact(decision, keys, "decision")
        if row["schema"] != decision_schema:
            raise err("wrong decision schema")
        supplied = digest(row["receipt_sha256"], "receipt_sha256")
        unsigned = dict(row)
        unsigned.pop("receipt_sha256")
        if sha(canonical(unsigned)) != supplied:
            raise err("receipt digest mismatch")
        if row["authority"] != authority_factory():
            raise err("authority ceiling changed")
        mode = row["evaluation_mode"]
        if mode not in {"CURRENT_PROCESS", "HISTORICAL_REVIEW_ONLY"}:
            raise err("unknown evaluation mode")
        original = evaluate(
            normalized,
            utc(row["evaluated_at"], "evaluated_at"),
            current_process=(mode == "CURRENT_PROCESS"),
        )
        if canonical(original) != canonical(row):
            raise err("semantic receipt mismatch")
        if mode == "CURRENT_PROCESS" and row["authorized_to_send"]:
            fresh = evaluate(
                normalized,
                current_clock(),
                current_process=True,
            )
            if not fresh["authorized_to_send"]:
                raise err("current send authorization is stale")
        return True

    return verify_receipt


verify_receipt = _make_verify_receipt(
    normalize_packet,
    _evaluate,
    _CURRENT_CLOCK,
    _hard_false_authority,
    _exact_keys,
    DECISION_KEYS,
    DECISION_SCHEMA,
    _digest,
    canonical_json,
    sha256_hex,
    _utc,
    FirewallError,
)

del (
    _make_current_clock,
    _make_evaluator,
    _make_compile_historical,
    _make_compile_current,
    _make_verify_receipt,
)
