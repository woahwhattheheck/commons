"""Hardened buyer/prime redline -> paid-scope delta compiler.

Structured decision support only: no contract parsing, legal advice, acceptance,
counterparty send, payment mutation, or revenue recognition.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from . import _engine_v1 as _v1

SCHEMA = _v1.SCHEMA
PACKET_SCHEMA = "buyer-redline-scope-delta/v2"
CATEGORIES = _v1.CATEGORIES
OUTCOMES = _v1.OUTCOMES
RedlineError = _v1.RedlineError
Clause = _v1.Clause
Draft = _v1.Draft
strict_json_loads = _v1.strict_json_loads


def _dt(text: str) -> datetime:
    try:
        return datetime.fromisoformat(text[:-1] + "+00:00").astimezone(timezone.utc)
    except (ValueError, TypeError) as exc:
        raise RedlineError("invalid UTC chronology") from exc


def _typed_singletons(draft: Draft) -> None:
    for c in draft.clauses:
        key = (c.category, c.metric)
        v = c.value
        if key == ("price_payment", "fixed_price_minor"):
            if not isinstance(v, int) or isinstance(v, bool):
                raise RedlineError("price_payment/fixed_price_minor must be integer minor units")
        elif key == ("price_payment", "currency"):
            if not isinstance(v, str):
                raise RedlineError("price_payment/currency must be text")
        elif key == ("price_payment", "net_days"):
            if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                raise RedlineError("price_payment/net_days must be a non-negative integer")
        elif key == ("schedule", "duration_days"):
            if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                raise RedlineError("schedule/duration_days must be a positive integer")
        elif key == ("liability_warranty", "unlimited_liability"):
            if not isinstance(v, bool):
                raise RedlineError("liability_warranty/unlimited_liability must be boolean")


def parse_draft(raw: bytes | str, *, role: str) -> Draft:
    draft = _v1.parse_draft(raw, role=role)
    _typed_singletons(draft)
    return draft


def semantic_digest(draft: Draft) -> str:
    return _v1.semantic_digest(draft)


def _identity(c: Clause) -> tuple[str, str, str]:
    return (c.clause_id, c.category, c.metric)


def _delta(before: Clause | None, after: Clause | None, key: tuple[str, str, str]) -> dict[str, Any]:
    if before is None:
        change = "ADDED"
    elif after is None:
        change = "REMOVED"
    else:
        change = "UNCHANGED" if before.semantic() == after.semantic() else "CHANGED"
    cid, category, metric = key
    return {
        "clause_id": cid, "category": category, "metric": metric, "change": change,
        "baseline": before.semantic() if before else None,
        "counter": after.semantic() if after else None,
    }


def compile_redline(baseline_raw: bytes | str, counter_raw: bytes | str) -> dict[str, Any]:
    baseline = parse_draft(baseline_raw, role="baseline")
    counter = parse_draft(counter_raw, role="counter")
    bd, cd = semantic_digest(baseline), semantic_digest(counter)
    reasons: list[str] = []
    if baseline.document_id != counter.document_id:
        reasons.append("document_id mismatch")
    if counter.baseline_semantic_sha256 != bd:
        reasons.append("counterdraft is not bound to this baseline semantic digest")
    if _dt(counter.observed_at) < _dt(baseline.observed_at):
        reasons.append("counterdraft observed_at predates baseline")
    if counter.generation_id == baseline.generation_id and cd != bd:
        reasons.append("same generation_id carries changed semantics")

    before = {_identity(c): c for c in baseline.clauses}
    after = {_identity(c): c for c in counter.clauses}
    deltas = [_delta(before.get(k), after.get(k), k) for k in sorted(set(before) | set(after))]
    precedence = {"NONE": 0, "OWNER_REVIEW": 1, "REQUOTE_REQUIRED": 2, "LEGAL_REVIEW_REQUIRED": 3}
    classified: list[dict[str, Any]] = []
    maximum = "NONE"
    for d in deltas:
        state, why = _v1._classify(d, baseline, counter)
        if d["change"] != "UNCHANGED":
            classified.append({**d, "decision": state, "reasons": why})
        if precedence[state] > precedence[maximum]:
            maximum = state
    status = "HOLD_CONTRADICTION" if reasons else ("ACCEPTABLE_AS_WRITTEN" if maximum == "NONE" else maximum)
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "status": status,
        "source": {
            "baseline_raw_sha256": _v1._raw_sha(baseline_raw),
            "counter_raw_sha256": _v1._raw_sha(counter_raw),
            "baseline_semantic_sha256": bd,
            "counter_semantic_sha256": cd,
            "document_id": baseline.document_id,
            "baseline_generation_id": baseline.generation_id,
            "counter_generation_id": counter.generation_id,
            "baseline_observed_at": baseline.observed_at,
            "counter_observed_at": counter.observed_at,
            "binding_ok": not reasons,
            "binding_reasons": reasons,
        },
        "summary": {
            "changed_clause_count": len(classified),
            "decision_counts": {
                s: sum(1 for d in classified if d["decision"] == s)
                for s in ("LEGAL_REVIEW_REQUIRED", "OWNER_REVIEW", "REQUOTE_REQUIRED")
            },
        },
        "deltas": classified,
        "authority": {
            "legal_advice": False, "accept_terms": False, "sign_contract": False,
            "send_to_counterparty": False, "mutate_price": False,
            "mutate_payment": False, "book_revenue": False,
        },
        "operator_note": "Decision support only. Human owner/legal/commercial review remains authoritative.",
    }
    packet["receipt_sha256"] = _v1._sha(packet)
    return packet


def verify_packet(packet: dict[str, Any], baseline_raw: bytes | str, counter_raw: bytes | str) -> bool:
    """Replay exact retained source bytes; a self-recomputed packet hash is not authority."""
    if not isinstance(packet, dict):
        return False
    try:
        return packet == compile_redline(baseline_raw, counter_raw)
    except (RedlineError, UnicodeError, ValueError, TypeError):
        return False


def render_owner_markdown(packet: dict[str, Any], baseline_raw: bytes | str, counter_raw: bytes | str) -> str:
    if not verify_packet(packet, baseline_raw, counter_raw):
        raise RedlineError("packet does not semantically verify against source bytes")
    lines = [
        "# Buyer Redline Scope Delta", "", f"**Decision:** `{packet['status']}`",
        f"**Changed clauses:** {packet['summary']['changed_clause_count']}",
        f"**Receipt:** `{packet['receipt_sha256']}`", "",
        "> Decision support only. This packet does not accept/sign terms, give legal advice, send anything, mutate price/payment, or recognize revenue.", "",
    ]
    if packet["source"]["binding_reasons"]:
        lines.extend(["## Source hold", *[f"- {x}" for x in packet["source"]["binding_reasons"]], ""])
    if packet["deltas"]:
        lines.append("## Clause deltas")
        for d in packet["deltas"]:
            lines.append(
                f"- `{d['clause_id']}` `{d['category']}/{d['metric']}` — **{d['decision']}** — "
                f"{d['change']} — {'; '.join(d['reasons']) or 'material change'}"
            )
    else:
        lines.append("No material clause deltas were found in the structured facts.")
    lines.extend([
        "", "## Source identity",
        f"- baseline raw SHA-256: `{packet['source']['baseline_raw_sha256']}`",
        f"- counter raw SHA-256: `{packet['source']['counter_raw_sha256']}`",
        f"- baseline semantic SHA-256: `{packet['source']['baseline_semantic_sha256']}`",
        f"- counter semantic SHA-256: `{packet['source']['counter_semantic_sha256']}`",
    ])
    return "\n".join(lines) + "\n"


__all__ = [
    "SCHEMA", "PACKET_SCHEMA", "CATEGORIES", "OUTCOMES", "RedlineError", "Clause", "Draft",
    "strict_json_loads", "parse_draft", "semantic_digest", "compile_redline",
    "verify_packet", "render_owner_markdown",
]
