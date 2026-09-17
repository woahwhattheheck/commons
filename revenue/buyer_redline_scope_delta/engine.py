"""Hardened public facade for the buyer-redline paid-scope delta compiler.

The original reviewed compiler is preserved byte-for-byte in
``_engine_core_20260917.py``.  This facade repairs source chronology and packet
verification without reminting the product's classification semantics.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from . import _engine_core_20260917 as _core

RedlineError = _core.RedlineError
Clause = _core.Clause
Draft = _core.Draft
SCHEMA = _core.SCHEMA
PACKET_SCHEMA = _core.PACKET_SCHEMA
CATEGORIES = _core.CATEGORIES
OUTCOMES = _core.OUTCOMES
parse_draft = _core.parse_draft
semantic_digest = _core.semantic_digest
strict_json_loads = _core.strict_json_loads

_AUTHORITY_KEYS = frozenset({
    "legal_advice",
    "accept_terms",
    "sign_contract",
    "send_to_counterparty",
    "mutate_price",
    "mutate_payment",
    "book_revenue",
})
_SOURCE_KEYS = frozenset({
    "baseline_raw_sha256",
    "counter_raw_sha256",
    "baseline_semantic_sha256",
    "counter_semantic_sha256",
    "document_id",
    "baseline_generation_id",
    "counter_generation_id",
    "baseline_observed_at",
    "counter_observed_at",
    "binding_ok",
    "binding_reasons",
})
_TOP_LEVEL_KEYS = frozenset({
    "schema",
    "status",
    "source",
    "summary",
    "deltas",
    "authority",
    "operator_note",
    "receipt_sha256",
})
_DELTA_KEYS = frozenset({
    "clause_id",
    "category",
    "metric",
    "change",
    "baseline",
    "counter",
    "decision",
    "reasons",
})
_DECISIONS = ("OWNER_REVIEW", "REQUOTE_REQUIRED", "LEGAL_REVIEW_REQUIRED")
_PRECEDENCE = {"OWNER_REVIEW": 1, "REQUOTE_REQUIRED": 2, "LEGAL_REVIEW_REQUIRED": 3}
_BINDING_REASON_SET = frozenset({
    "document_id mismatch",
    "counterdraft is not bound to this baseline semantic digest",
    "counterdraft observed_at predates baseline",
    "same generation_id carries changed semantics",
})
_HEX = frozenset("0123456789abcdef")


def _instant(text: Any, field: str) -> datetime:
    validated = _core._require_timestamp(text, field)
    return datetime.fromisoformat(validated[:-1] + "+00:00")


def _source_reasons(
    baseline: Draft,
    counter: Draft,
    baseline_digest: str,
    counter_digest: str,
) -> list[str]:
    reasons: list[str] = []
    if baseline.document_id != counter.document_id:
        reasons.append("document_id mismatch")
    if counter.baseline_semantic_sha256 != baseline_digest:
        reasons.append("counterdraft is not bound to this baseline semantic digest")
    if _instant(counter.observed_at, "counter.observed_at") < _instant(
        baseline.observed_at, "baseline.observed_at"
    ):
        reasons.append("counterdraft observed_at predates baseline")
    if counter.generation_id == baseline.generation_id and counter_digest != baseline_digest:
        reasons.append("same generation_id carries changed semantics")
    return reasons


def _status_from_deltas(deltas: Any) -> str | None:
    if not isinstance(deltas, list):
        return None
    if not deltas:
        return "ACCEPTABLE_AS_WRITTEN"
    state = "OWNER_REVIEW"
    seen = False
    for item in deltas:
        if not isinstance(item, dict):
            return None
        decision = item.get("decision")
        if decision not in _PRECEDENCE:
            return None
        if not seen or _PRECEDENCE[decision] > _PRECEDENCE[state]:
            state = decision
        seen = True
    return state if seen else "ACCEPTABLE_AS_WRITTEN"


def compile_redline(baseline_raw: bytes | str, counter_raw: bytes | str) -> dict[str, Any]:
    """Compile with instant-based chronology rather than lexical timestamp order."""
    baseline = _core.parse_draft(baseline_raw, role="baseline")
    counter = _core.parse_draft(counter_raw, role="counter")
    baseline_digest = _core.semantic_digest(baseline)
    counter_digest = _core.semantic_digest(counter)

    packet = _core.compile_redline(baseline_raw, counter_raw)
    reasons = _source_reasons(baseline, counter, baseline_digest, counter_digest)
    packet["source"]["binding_reasons"] = reasons
    packet["source"]["binding_ok"] = not reasons
    if reasons:
        packet["status"] = "HOLD_CONTRADICTION"
    else:
        derived = _status_from_deltas(packet["deltas"])
        if derived is None:  # pragma: no cover - the frozen core only emits known decisions
            raise RedlineError("core emitted an unsupported delta decision")
        packet["status"] = derived
    packet.pop("receipt_sha256", None)
    packet["receipt_sha256"] = _core._sha(packet)
    return packet


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in _HEX for ch in value)


def _valid_delta(item: Any) -> bool:
    if not isinstance(item, dict) or set(item) != _DELTA_KEYS:
        return False
    try:
        _core._require_token(item["clause_id"], "delta.clause_id")
        category = _core._require_token(item["category"], "delta.category")
        _core._require_token(item["metric"], "delta.metric")
    except RedlineError:
        return False
    if category not in CATEGORIES:
        return False
    if item["change"] not in {"ADDED", "REMOVED", "CHANGED"}:
        return False
    if item["decision"] not in _PRECEDENCE:
        return False
    reasons = item["reasons"]
    if not isinstance(reasons, list) or not reasons:
        return False
    try:
        for reason in reasons:
            _core._require_text(reason, "delta.reason")
    except RedlineError:
        return False
    return True


def verify_packet(packet: dict[str, Any]) -> bool:
    """Verify exact structure, receipt, binding chronology, and authority ceiling."""
    if not isinstance(packet, dict) or set(packet) != _TOP_LEVEL_KEYS:
        return False
    if packet.get("schema") != PACKET_SCHEMA or packet.get("status") not in OUTCOMES:
        return False

    receipt = packet.get("receipt_sha256")
    if not _is_sha256(receipt):
        return False
    body = dict(packet)
    body.pop("receipt_sha256")
    try:
        if _core._sha(body) != receipt:
            return False
    except RedlineError:
        return False

    authority = packet.get("authority")
    if not isinstance(authority, dict) or set(authority) != _AUTHORITY_KEYS:
        return False
    if any(type(value) is not bool or value is not False for value in authority.values()):
        return False

    source = packet.get("source")
    if not isinstance(source, dict) or set(source) != _SOURCE_KEYS:
        return False
    for key in (
        "baseline_raw_sha256",
        "counter_raw_sha256",
        "baseline_semantic_sha256",
        "counter_semantic_sha256",
    ):
        if not _is_sha256(source.get(key)):
            return False
    try:
        _core._require_token(source.get("document_id"), "source.document_id")
        _core._require_token(source.get("baseline_generation_id"), "source.baseline_generation_id")
        _core._require_token(source.get("counter_generation_id"), "source.counter_generation_id")
        baseline_instant = _instant(source.get("baseline_observed_at"), "source.baseline_observed_at")
        counter_instant = _instant(source.get("counter_observed_at"), "source.counter_observed_at")
    except RedlineError:
        return False
    if type(source.get("binding_ok")) is not bool:
        return False
    reasons = source.get("binding_reasons")
    if (
        not isinstance(reasons, list)
        or len(reasons) != len(set(reasons))
        or any(reason not in _BINDING_REASON_SET for reason in reasons)
    ):
        return False
    chronology_reason = "counterdraft observed_at predates baseline"
    if (counter_instant < baseline_instant) != (chronology_reason in reasons):
        return False
    if source["binding_ok"] != (not reasons):
        return False

    deltas = packet.get("deltas")
    if not isinstance(deltas, list) or any(not _valid_delta(item) for item in deltas):
        return False
    summary = packet.get("summary")
    if not isinstance(summary, dict) or set(summary) != {"changed_clause_count", "decision_counts"}:
        return False
    if type(summary["changed_clause_count"]) is not int or summary["changed_clause_count"] != len(deltas):
        return False
    counts = summary.get("decision_counts")
    expected_counts = {decision: sum(1 for item in deltas if item["decision"] == decision) for decision in sorted(_DECISIONS)}
    if counts != expected_counts:
        return False

    if reasons:
        if packet["status"] != "HOLD_CONTRADICTION":
            return False
    else:
        expected_status = _status_from_deltas(deltas)
        if expected_status is None or packet["status"] != expected_status:
            return False

    try:
        _core._require_text(packet.get("operator_note"), "operator_note")
    except RedlineError:
        return False
    return True


def render_owner_markdown(packet: dict[str, Any]) -> str:
    if not verify_packet(packet):
        raise RedlineError("packet receipt or semantic structure invalid")
    return _core.render_owner_markdown(packet)
