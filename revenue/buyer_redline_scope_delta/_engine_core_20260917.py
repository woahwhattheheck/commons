"""Deterministic buyer/prime redline -> paid-scope delta compiler.

Compares structured, human-reviewed clause facts. It intentionally does not parse
contracts, render legal advice, accept terms, contact a counterparty, or mutate
commercial/payment systems.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import unicodedata
from typing import Any, Iterable

SCHEMA = "buyer-redline-draft/v1"
PACKET_SCHEMA = "buyer-redline-scope-delta/v1"
CATEGORIES = {"scope", "deliverables", "acceptance", "price_payment", "schedule", "data_security", "ip", "liability_warranty", "termination", "dependencies", "assumptions"}
LEGAL_CATEGORIES = {"ip", "liability_warranty", "termination"}
SCOPE_CATEGORIES = {"scope", "deliverables", "schedule", "dependencies", "assumptions"}
OUTCOMES = {"ACCEPTABLE_AS_WRITTEN", "OWNER_REVIEW", "REQUOTE_REQUIRED", "LEGAL_REVIEW_REQUIRED", "HOLD_CONTRADICTION"}
_SINGLETON_METRICS = {("price_payment", "fixed_price_minor"), ("price_payment", "currency"), ("price_payment", "net_days"), ("schedule", "duration_days"), ("liability_warranty", "unlimited_liability")}


class RedlineError(ValueError):
    """Controlled validation failure."""


@dataclass(frozen=True)
class Clause:
    clause_id: str
    category: str
    metric: str
    statement: str
    value: Any

    def semantic(self) -> dict[str, Any]:
        return {"id": self.clause_id, "category": self.category, "metric": self.metric, "statement": self.statement, "value": self.value}


@dataclass(frozen=True)
class Draft:
    document_id: str
    generation_id: str
    observed_at: str
    clauses: tuple[Clause, ...]
    baseline_semantic_sha256: str | None

    def semantic(self, *, include_parent: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {"schema": SCHEMA, "document_id": self.document_id, "generation_id": self.generation_id, "observed_at": self.observed_at, "clauses": [c.semantic() for c in self.clauses]}
        if include_parent and self.baseline_semantic_sha256 is not None:
            out["baseline_semantic_sha256"] = self.baseline_semantic_sha256
        return out


def _pairs_no_duplicates(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise RedlineError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_json_loads(raw: bytes | str) -> Any:
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise RedlineError("input is not strict UTF-8") from exc
    elif isinstance(raw, str):
        text = raw
    else:
        raise RedlineError("input must be bytes or str")
    _require_text(text, "json", max_len=max(len(text), 1))
    try:
        return json.loads(text, object_pairs_hook=_pairs_no_duplicates, parse_constant=lambda token: (_ for _ in ()).throw(RedlineError(f"non-finite JSON constant: {token}")))
    except RedlineError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise RedlineError("invalid JSON") from exc


def _require_text(value: Any, field: str, *, max_len: int = 4096) -> str:
    if not isinstance(value, str) or not value or len(value) > max_len:
        raise RedlineError(f"{field} must be non-empty text <= {max_len} chars")
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
        raise RedlineError(f"{field} contains a surrogate code point")
    if unicodedata.normalize("NFC", value) != value:
        raise RedlineError(f"{field} must be NFC-normalized")
    return value


def _require_token(value: Any, field: str, *, max_len: int = 128) -> str:
    text = _require_text(value, field, max_len=max_len)
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-/")
    if any(ch not in allowed for ch in text):
        raise RedlineError(f"{field} contains unsupported characters")
    return text


def _require_timestamp(value: Any, field: str) -> str:
    text = _require_text(value, field, max_len=40)
    if not text.endswith("Z"):
        raise RedlineError(f"{field} must be UTC and end in Z")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise RedlineError(f"{field} is not ISO-8601") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise RedlineError(f"{field} must be UTC")
    return text


def _normalize_value(value: Any, field: str) -> Any:
    if value is None or isinstance(value, str):
        if isinstance(value, str):
            _require_text(value, field)
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > 10**15:
            raise RedlineError(f"{field} integer out of range")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RedlineError(f"{field} must be finite")
        raise RedlineError(f"{field} floats are forbidden; use integer minor units or exact text")
    if isinstance(value, list):
        if len(value) > 100:
            raise RedlineError(f"{field} list too long")
        return [_normalize_value(item, f"{field}[]") for item in value]
    if isinstance(value, dict):
        if len(value) > 100:
            raise RedlineError(f"{field} object too large")
        return {k: _normalize_value(v, f"{field}.{k}") for k, v in sorted(value.items())}
    raise RedlineError(f"{field} contains unsupported value type")


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8", "strict")
    except (UnicodeError, ValueError, TypeError) as exc:
        raise RedlineError("value cannot be canonically encoded") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def parse_draft(raw: bytes | str, *, role: str) -> Draft:
    obj = strict_json_loads(raw)
    if not isinstance(obj, dict):
        raise RedlineError("draft must be a JSON object")
    allowed = {"schema", "document_id", "generation_id", "observed_at", "clauses", "baseline_semantic_sha256"}
    unknown = set(obj) - allowed
    if unknown:
        raise RedlineError(f"unknown draft fields: {sorted(unknown)}")
    if obj.get("schema") != SCHEMA:
        raise RedlineError(f"schema must equal {SCHEMA}")
    document_id = _require_token(obj.get("document_id"), "document_id")
    generation_id = _require_token(obj.get("generation_id"), "generation_id")
    observed_at = _require_timestamp(obj.get("observed_at"), "observed_at")
    raw_clauses = obj.get("clauses")
    if not isinstance(raw_clauses, list) or not raw_clauses:
        raise RedlineError("clauses must be a non-empty list")
    if len(raw_clauses) > 500:
        raise RedlineError("too many clauses")
    clauses: list[Clause] = []
    ids: set[str] = set()
    singleton_values: dict[tuple[str, str], Any] = {}
    for i, item in enumerate(raw_clauses):
        if not isinstance(item, dict):
            raise RedlineError(f"clauses[{i}] must be an object")
        if set(item) != {"id", "category", "metric", "statement", "value"}:
            raise RedlineError(f"clauses[{i}] fields must be exactly id/category/metric/statement/value")
        clause_id = _require_token(item["id"], f"clauses[{i}].id")
        if clause_id in ids:
            raise RedlineError(f"duplicate clause id: {clause_id}")
        ids.add(clause_id)
        category = _require_token(item["category"], f"clauses[{i}].category")
        if category not in CATEGORIES:
            raise RedlineError(f"unsupported category: {category}")
        metric = _require_token(item["metric"], f"clauses[{i}].metric")
        statement = _require_text(item["statement"], f"clauses[{i}].statement")
        value = _normalize_value(item["value"], f"clauses[{i}].value")
        clause = Clause(clause_id, category, metric, statement, value)
        key = (category, metric)
        if key in _SINGLETON_METRICS:
            if key in singleton_values and singleton_values[key] != value:
                raise RedlineError(f"contradictory singleton metric: {category}/{metric}")
            singleton_values[key] = value
        clauses.append(clause)
    clauses.sort(key=lambda c: c.clause_id)
    parent = obj.get("baseline_semantic_sha256")
    if role == "baseline":
        if parent is not None:
            raise RedlineError("baseline must not claim baseline_semantic_sha256")
    elif role == "counter":
        if not isinstance(parent, str) or len(parent) != 64 or any(ch not in "0123456789abcdef" for ch in parent):
            raise RedlineError("counter baseline_semantic_sha256 must be 64 lowercase hex chars")
    else:
        raise RedlineError("invalid role")
    return Draft(document_id, generation_id, observed_at, tuple(clauses), parent)


def semantic_digest(draft: Draft) -> str:
    return _sha(draft.semantic(include_parent=False))


def _raw_sha(raw: bytes | str) -> str:
    b = raw if isinstance(raw, bytes) else raw.encode("utf-8", "strict")
    return hashlib.sha256(b).hexdigest()


def _clause_change(before: Clause | None, after: Clause | None) -> dict[str, Any]:
    if before is None and after is not None:
        change, category, metric = "ADDED", after.category, after.metric
    elif before is not None and after is None:
        change, category, metric = "REMOVED", before.category, before.metric
    elif before is not None and after is not None:
        change = "UNCHANGED" if before.semantic() == after.semantic() else "CHANGED"
        category, metric = after.category, after.metric
    else:
        raise AssertionError("both clauses missing")
    return {"clause_id": (after or before).clause_id, "category": category, "metric": metric, "change": change, "baseline": before.semantic() if before else None, "counter": after.semantic() if after else None}


def _metric_value(draft: Draft, category: str, metric: str) -> Any:
    values = [c.value for c in draft.clauses if c.category == category and c.metric == metric]
    if not values:
        return None
    if len(values) != 1:
        raise RedlineError(f"ambiguous metric {category}/{metric}")
    return values[0]


def _classify(delta: dict[str, Any], baseline: Draft, counter: Draft) -> tuple[str, list[str]]:
    if delta["change"] == "UNCHANGED":
        return "NONE", []
    category, metric, change = delta["category"], delta["metric"], delta["change"]
    before = delta["baseline"]["value"] if delta["baseline"] else None
    after = delta["counter"]["value"] if delta["counter"] else None
    if category in LEGAL_CATEGORIES:
        reasons = [f"{category} changed; legal review boundary"]
        if category == "liability_warranty" and metric == "unlimited_liability" and after is True:
            reasons.append("counterdraft introduces unlimited liability")
        return "LEGAL_REVIEW_REQUIRED", reasons
    if category == "price_payment":
        if metric == "currency" and before != after:
            return "REQUOTE_REQUIRED", ["currency changed"]
        if metric == "fixed_price_minor" and before != after:
            return "REQUOTE_REQUIRED", ["fixed price changed"]
        if metric == "net_days" and isinstance(before, int) and isinstance(after, int) and after > before:
            return "REQUOTE_REQUIRED", ["payment timing widened"]
        return "OWNER_REVIEW", ["commercial payment term changed"]
    if category == "schedule" and metric == "duration_days" and isinstance(before, int) and isinstance(after, int):
        if after < before:
            return "REQUOTE_REQUIRED", ["delivery duration shortened"]
        return "OWNER_REVIEW", ["delivery duration changed"]
    if category in {"scope", "deliverables"} and change == "ADDED":
        base_price = _metric_value(baseline, "price_payment", "fixed_price_minor")
        counter_price = _metric_value(counter, "price_payment", "fixed_price_minor")
        if isinstance(base_price, int) and isinstance(counter_price, int) and counter_price <= base_price:
            return "REQUOTE_REQUIRED", ["scope/deliverable added without higher fixed price"]
        return "OWNER_REVIEW", ["scope/deliverable added"]
    if category in {"dependencies", "assumptions"} and change == "REMOVED":
        return "REQUOTE_REQUIRED", ["dependency/assumption removed; supplier burden may expand"]
    if category == "acceptance" and change == "REMOVED":
        return "OWNER_REVIEW", ["acceptance criterion deleted"]
    if category == "data_security":
        return "OWNER_REVIEW", ["data/security obligation changed"]
    if category in SCOPE_CATEGORIES or category == "acceptance":
        return "OWNER_REVIEW", [f"{category} changed"]
    return "OWNER_REVIEW", ["material clause changed"]


def compile_redline(baseline_raw: bytes | str, counter_raw: bytes | str) -> dict[str, Any]:
    baseline = parse_draft(baseline_raw, role="baseline")
    counter = parse_draft(counter_raw, role="counter")
    baseline_digest, counter_digest = semantic_digest(baseline), semantic_digest(counter)
    source_reasons: list[str] = []
    if baseline.document_id != counter.document_id:
        source_reasons.append("document_id mismatch")
    if counter.baseline_semantic_sha256 != baseline_digest:
        source_reasons.append("counterdraft is not bound to this baseline semantic digest")
    if counter.observed_at < baseline.observed_at:
        source_reasons.append("counterdraft observed_at predates baseline")
    if counter.generation_id == baseline.generation_id and counter_digest != baseline_digest:
        source_reasons.append("same generation_id carries changed semantics")

    by_before = {c.clause_id: c for c in baseline.clauses}
    by_after = {c.clause_id: c for c in counter.clauses}
    deltas = [_clause_change(by_before.get(cid), by_after.get(cid)) for cid in sorted(set(by_before) | set(by_after))]
    precedence = {"NONE": 0, "OWNER_REVIEW": 1, "REQUOTE_REQUIRED": 2, "LEGAL_REVIEW_REQUIRED": 3, "HOLD_CONTRADICTION": 4}
    classifications: list[dict[str, Any]] = []
    max_state = "NONE"
    for delta in deltas:
        state, reasons = _classify(delta, baseline, counter)
        if delta["change"] != "UNCHANGED":
            classifications.append({**delta, "decision": state, "reasons": reasons})
        if precedence[state] > precedence[max_state]:
            max_state = state
    overall = "HOLD_CONTRADICTION" if source_reasons else ("ACCEPTABLE_AS_WRITTEN" if max_state == "NONE" else max_state)
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "status": overall,
        "source": {
            "baseline_raw_sha256": _raw_sha(baseline_raw), "counter_raw_sha256": _raw_sha(counter_raw),
            "baseline_semantic_sha256": baseline_digest, "counter_semantic_sha256": counter_digest,
            "document_id": baseline.document_id, "baseline_generation_id": baseline.generation_id,
            "counter_generation_id": counter.generation_id, "baseline_observed_at": baseline.observed_at,
            "counter_observed_at": counter.observed_at, "binding_ok": not source_reasons,
            "binding_reasons": source_reasons,
        },
        "summary": {
            "changed_clause_count": len(classifications),
            "decision_counts": {state: sum(1 for d in classifications if d["decision"] == state) for state in sorted(OUTCOMES - {"ACCEPTABLE_AS_WRITTEN", "HOLD_CONTRADICTION"})},
        },
        "deltas": classifications,
        "authority": {"legal_advice": False, "accept_terms": False, "sign_contract": False, "send_to_counterparty": False, "mutate_price": False, "mutate_payment": False, "book_revenue": False},
        "operator_note": "Decision support only. Human owner/legal/commercial review remains authoritative.",
    }
    packet["receipt_sha256"] = _sha(packet)
    return packet


def verify_packet(packet: dict[str, Any]) -> bool:
    if not isinstance(packet, dict) or packet.get("schema") != PACKET_SCHEMA:
        return False
    receipt = packet.get("receipt_sha256")
    if not isinstance(receipt, str) or len(receipt) != 64:
        return False
    body = dict(packet); body.pop("receipt_sha256", None)
    try:
        expected = _sha(body)
    except RedlineError:
        return False
    if receipt != expected:
        return False
    authority = packet.get("authority")
    if not isinstance(authority, dict) or any(authority.values()):
        return False
    return packet.get("status") in OUTCOMES


def render_owner_markdown(packet: dict[str, Any]) -> str:
    if not verify_packet(packet):
        raise RedlineError("packet receipt invalid")
    lines = ["# Buyer Redline Scope Delta", "", f"**Decision:** `{packet['status']}`", f"**Changed clauses:** {packet['summary']['changed_clause_count']}", f"**Receipt:** `{packet['receipt_sha256']}`", "", "> Decision support only. This packet does not accept/sign terms, give legal advice, send anything, mutate price/payment, or recognize revenue.", ""]
    if packet["source"]["binding_reasons"]:
        lines.extend(["## Source hold", *[f"- {r}" for r in packet["source"]["binding_reasons"]], ""])
    if packet["deltas"]:
        lines.append("## Clause deltas")
        for item in packet["deltas"]:
            lines.append(f"- `{item['clause_id']}` — **{item['decision']}** — {item['change']} — {'; '.join(item['reasons']) or 'material change'}")
    else:
        lines.append("No material clause deltas were found in the structured facts.")
    lines.extend(["", "## Source identity", f"- baseline semantic SHA-256: `{packet['source']['baseline_semantic_sha256']}`", f"- counter semantic SHA-256: `{packet['source']['counter_semantic_sha256']}`"])
    return "\n".join(lines) + "\n"
