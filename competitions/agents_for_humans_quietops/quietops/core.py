"""Deterministic authority and receipt core for QuietOps.

This module deliberately contains no model/provider calls. The Strands layer may propose
work, but only this core can classify authority and produce executable plans.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "quietops.decision/v1"
RECEIPT_SCHEMA = "quietops.receipt/v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_NORMALIZE_DEPTH = 32
MAX_CONTAINER_ITEMS = 4096
MAX_STRING_CHARS = 131_072
SAFE_AUTOMATION_KINDS = frozenset({
    "CLASSIFY_DOCUMENT",
    "SUMMARIZE_EVIDENCE",
    "RECONCILE_RECORDS",
    "DRAFT_INTERNAL_NOTE",
    "QUEUE_INTERNAL_REVIEW",
})
HUMAN_REQUIRED_KINDS = frozenset({
    "CONTACT_CUSTOMER",
    "CONTACT_VENDOR",
    "PRICE_COMMITMENT",
    "MOVE_MONEY",
    "PAYMENT_MUTATION",
    "LEGAL_INTERPRETATION",
    "CONTRACT_ACCEPTANCE",
    "EXTERNAL_MUTATION",
    "DELETE_EXTERNAL_DATA",
})

class QuietOpsError(ValueError):
    """Fail-closed input or verification error."""


def _reject_constant(value: str) -> None:
    raise QuietOpsError(f"non-finite JSON constant rejected: {value}")


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise QuietOpsError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_json_loads(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_pairs_object,
        parse_constant=_reject_constant,
        parse_float=Decimal,
    )


def _normalize(value: Any, _depth: int = 0) -> Any:
    if _depth > MAX_NORMALIZE_DEPTH:
        raise QuietOpsError("input nesting exceeds deterministic bound")
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, str):
        if len(value) > MAX_STRING_CHARS:
            raise QuietOpsError("string exceeds deterministic size bound")
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise QuietOpsError("non-finite decimal")
        return format(value, "f")
    if isinstance(value, float):
        raise QuietOpsError("binary floating point is not accepted; use integer minor units or decimal strings")
    if isinstance(value, Mapping):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise QuietOpsError("object exceeds deterministic item bound")
        out: dict[str, Any] = {}
        for key in sorted(value):
            if not isinstance(key, str) or not key:
                raise QuietOpsError("all object keys must be non-empty strings")
            if key in {"__proto__", "prototype", "constructor"}:
                raise QuietOpsError(f"unsafe key rejected: {key}")
            out[key] = _normalize(value[key], _depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise QuietOpsError("array exceeds deterministic item bound")
        return [_normalize(v, _depth + 1) for v in value]
    raise QuietOpsError(f"unsupported value type: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    normalized = _normalize(value)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def _require_exact_keys(obj: Mapping[str, Any], required: set[str], optional: set[str] = set()) -> None:
    keys = set(obj)
    missing = required - keys
    extra = keys - required - optional
    if missing or extra:
        raise QuietOpsError(f"shape mismatch missing={sorted(missing)} extra={sorted(extra)}")


def _require_id(label: str, value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 160:
        raise QuietOpsError(f"{label} must be a non-empty string <=160 chars")
    if any(ord(ch) < 32 for ch in value):
        raise QuietOpsError(f"{label} contains control characters")
    return value


def _require_minor(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise QuietOpsError(f"{label} must be integer minor units")
    if abs(value) > 9_000_000_000_000_000:
        raise QuietOpsError(f"{label} outside safe bounded domain")
    return value


@dataclass(frozen=True)
class EvidenceRef:
    ref: str
    sha256: str


@dataclass(frozen=True)
class Decision:
    schema: str
    task_id: str
    event_id: str
    input_sha256: str
    evidence_sha256: str
    authority: str
    action: str
    reasons: tuple[str, ...]
    autonomous: bool
    human_decision_required: bool
    operation_id: str

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["reasons"] = list(self.reasons)
        return out


def validate_evidence(raw: Any) -> tuple[EvidenceRef, ...]:
    if not isinstance(raw, list) or not raw:
        raise QuietOpsError("evidence must be a non-empty list")
    if len(raw) > 128:
        raise QuietOpsError("evidence list too large")
    refs: list[EvidenceRef] = []
    by_ref: dict[str, str] = {}
    seen_pair: set[tuple[str, str]] = set()
    for row in raw:
        if not isinstance(row, Mapping):
            raise QuietOpsError("evidence rows must be objects")
        _require_exact_keys(row, {"ref", "sha256"})
        ref = _require_id("evidence.ref", row["ref"])
        h = row["sha256"]
        if not isinstance(h, str) or not SHA256_RE.fullmatch(h):
            raise QuietOpsError("evidence.sha256 must be lowercase 64-char hex")
        prior = by_ref.get(ref)
        if prior is not None and prior != h:
            raise QuietOpsError(f"evidence ref {ref!r} maps to multiple generations")
        by_ref[ref] = h
        pair = (ref, h)
        if pair in seen_pair:
            raise QuietOpsError(f"duplicate evidence row: {ref}")
        seen_pair.add(pair)
        refs.append(EvidenceRef(ref=ref, sha256=h))
    refs.sort(key=lambda r: (r.ref, r.sha256))
    return tuple(refs)


def _evidence_digest(evidence: Sequence[EvidenceRef]) -> str:
    return digest([asdict(e) for e in evidence])


def _decision_reasons(item: Mapping[str, Any], evidence: Sequence[EvidenceRef]) -> tuple[str, tuple[str, ...], bool]:
    kind = item["kind"]
    reasons: list[str] = []
    autonomous = True

    if kind in HUMAN_REQUIRED_KINDS:
        autonomous = False
        reasons.append(f"{kind} crosses a human authority boundary")
    elif kind not in SAFE_AUTOMATION_KINDS:
        autonomous = False
        reasons.append("unknown action kind fails closed")

    confidence = item.get("confidence_bps", 10_000)
    if isinstance(confidence, bool) or not isinstance(confidence, int) or not (0 <= confidence <= 10_000):
        raise QuietOpsError("confidence_bps must be integer 0..10000")
    if confidence < 9_500:
        autonomous = False
        reasons.append("confidence below 95% automation threshold")

    if item.get("ambiguous_evidence", False) is not False:
        if item.get("ambiguous_evidence") is not True:
            raise QuietOpsError("ambiguous_evidence must be boolean")
        autonomous = False
        reasons.append("evidence is explicitly ambiguous")

    amount = item.get("amount_minor")
    if amount is not None:
        amount = _require_minor(amount, "amount_minor")
        if amount != 0:
            autonomous = False
            reasons.append("money-bearing item requires a human decision")

    external = item.get("external_effect", False)
    if external is not False:
        if external is not True:
            raise QuietOpsError("external_effect must be boolean")
        autonomous = False
        reasons.append("external side effect requires a human decision")

    if not reasons:
        reasons.append("bounded reversible work with complete evidence")

    authority = "AUTONOMOUS_REVERSIBLE" if autonomous else "HUMAN_DECISION_REQUIRED"
    return authority, tuple(reasons), autonomous


def decide(raw_item: Mapping[str, Any]) -> Decision:
    if not isinstance(raw_item, Mapping):
        raise QuietOpsError("work item must be an object")
    item = _normalize(raw_item)
    if not isinstance(item, dict):
        raise QuietOpsError("work item must normalize to an object")
    _require_exact_keys(
        item,
        {"task_id", "event_id", "kind", "action", "evidence"},
        {"confidence_bps", "ambiguous_evidence", "amount_minor", "external_effect", "context"},
    )
    task_id = _require_id("task_id", item["task_id"])
    event_id = _require_id("event_id", item["event_id"])
    kind = _require_id("kind", item["kind"])
    action = _require_id("action", item["action"])
    evidence = validate_evidence(item["evidence"])
    edigest = _evidence_digest(evidence)
    # Evidence is semantically a set keyed by (ref, generation); bind the sorted
    # retained generation so source enumeration order cannot mint a new operation.
    bound_item = dict(item)
    bound_item["evidence"] = [asdict(e) for e in evidence]
    input_sha = digest(bound_item)
    authority, reasons, autonomous = _decision_reasons(item, evidence)
    operation_id = digest({
        "task_id": task_id,
        "event_id": event_id,
        "input_sha256": input_sha,
        "authority": authority,
        "action": action,
    })
    return Decision(
        schema=SCHEMA,
        task_id=task_id,
        event_id=event_id,
        input_sha256=input_sha,
        evidence_sha256=edigest,
        authority=authority,
        action=action,
        reasons=reasons,
        autonomous=autonomous,
        human_decision_required=not autonomous,
        operation_id=operation_id,
    )


def make_receipt(raw_item: Mapping[str, Any], *, result: Mapping[str, Any], executor: str = "quietops-core") -> dict[str, Any]:
    """Mint a receipt only after independently recomputing authority from raw input.

    Callers cannot supply a preconstructed Decision object to self-promote authority.
    """
    decision = decide(raw_item)
    if decision.human_decision_required:
        raise QuietOpsError("cannot make autonomous execution receipt for a human-required decision")
    normalized_result = _normalize(result)
    body = {
        "schema": RECEIPT_SCHEMA,
        "operation_id": decision.operation_id,
        "task_id": decision.task_id,
        "event_id": decision.event_id,
        "input_sha256": decision.input_sha256,
        "evidence_sha256": decision.evidence_sha256,
        "authority": decision.authority,
        "action": decision.action,
        "executor": _require_id("executor", executor),
        "result": normalized_result,
    }
    body["receipt_sha256"] = digest(body)
    return body


def verify_receipt(raw_item: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    """Verify against raw input, recomputing the authority decision instead of trusting caller state."""
    if not isinstance(receipt, Mapping):
        return False
    try:
        decision = decide(raw_item)
    except (QuietOpsError, TypeError, ValueError):
        return False
    expected_keys = {
        "schema", "operation_id", "task_id", "event_id", "input_sha256", "evidence_sha256",
        "authority", "action", "executor", "result", "receipt_sha256",
    }
    if set(receipt) != expected_keys:
        return False
    if decision.human_decision_required:
        return False
    links = {
        "schema": RECEIPT_SCHEMA,
        "operation_id": decision.operation_id,
        "task_id": decision.task_id,
        "event_id": decision.event_id,
        "input_sha256": decision.input_sha256,
        "evidence_sha256": decision.evidence_sha256,
        "authority": decision.authority,
        "action": decision.action,
    }
    if any(receipt.get(k) != v for k, v in links.items()):
        return False
    claimed = receipt.get("receipt_sha256")
    if not isinstance(claimed, str) or not SHA256_RE.fullmatch(claimed):
        return False
    body = dict(receipt)
    body.pop("receipt_sha256")
    try:
        return digest(body) == claimed
    except QuietOpsError:
        return False



def process_queue(
    raw_items: Sequence[Mapping[str, Any]],
    *,
    completed_operation_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Process a bounded queue with exact replay collapse.

    Reusing one event_id for a different content-bound operation fails closed. Exact
    duplicates collapse, and operations already present in a durable completion set
    are reported as replay-skipped rather than executed again.
    """
    if not isinstance(raw_items, (list, tuple)):
        raise QuietOpsError("queue must be a list/tuple")
    if len(raw_items) > 1024:
        raise QuietOpsError("queue too large")

    completed: set[str] = set()
    for op in completed_operation_ids:
        if not isinstance(op, str) or not SHA256_RE.fullmatch(op):
            raise QuietOpsError("completed operation IDs must be lowercase SHA-256 hex")
        completed.add(op)

    seen_events: dict[str, str] = {}
    results: list[dict[str, Any]] = []
    for raw in raw_items:
        decision = decide(raw)
        prior = seen_events.get(decision.event_id)
        if prior is not None and prior != decision.operation_id:
            raise QuietOpsError(f"event_id reused for different generation: {decision.event_id}")
        if prior == decision.operation_id:
            results.append({
                "status": "EXACT_REPLAY_SKIPPED",
                "decision": decision.to_dict(),
                "result": None,
                "receipt": None,
            })
            continue
        seen_events[decision.event_id] = decision.operation_id
        if decision.operation_id in completed:
            results.append({
                "status": "DURABLE_REPLAY_SKIPPED",
                "decision": decision.to_dict(),
                "result": None,
                "receipt": None,
            })
            continue
        processed = process_offline(raw)
        results.append({"status": "PROCESSED", **processed})
    return results


def reconcile_records(context: Mapping[str, Any]) -> dict[str, Any]:
    """Example reversible professional tool: reconcile expected vs observed minor units.

    It never moves money or contacts anyone. Non-zero variance is surfaced as owner review.
    """
    if not isinstance(context, Mapping):
        raise QuietOpsError("context must be object")
    _require_exact_keys(context, {"expected_minor", "observed_minor", "currency"})
    expected = _require_minor(context["expected_minor"], "expected_minor")
    observed = _require_minor(context["observed_minor"], "observed_minor")
    currency = context["currency"]
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        raise QuietOpsError("currency must be ISO-style three uppercase letters")
    variance = observed - expected
    return {
        "currency": currency,
        "expected_minor": expected,
        "observed_minor": observed,
        "variance_minor": variance,
        "status": "MATCH" if variance == 0 else "OWNER_REVIEW_VARIANCE",
    }


def process_offline(raw_item: Mapping[str, Any]) -> dict[str, Any]:
    """Run the deterministic no-model path, including deterministic outcome escalation."""
    decision = decide(raw_item)
    out: dict[str, Any] = {
        "decision": decision.to_dict(),
        "receipt": None,
        "result": None,
        "followup": None,
    }
    if not decision.autonomous:
        out["followup"] = {
            "human_decision_required": True,
            "kind": "INPUT_AUTHORITY_DECISION",
            "task_id": decision.task_id,
            "event_id": decision.event_id,
            "operation_id": decision.operation_id,
            "reasons": list(decision.reasons),
            "external_action_taken": False,
        }
        return out
    if raw_item["kind"] == "RECONCILE_RECORDS":
        context = raw_item.get("context")
        if not isinstance(context, Mapping):
            raise QuietOpsError("RECONCILE_RECORDS requires context")
        result = reconcile_records(context)
    else:
        result = {"status": "COMPLETED_REVERSIBLE", "action": raw_item["action"]}
    receipt = make_receipt(raw_item, result=result)
    out["result"] = result
    out["receipt"] = receipt
    if result.get("status") == "OWNER_REVIEW_VARIANCE":
        out["followup"] = {
            "human_decision_required": True,
            "kind": "RECONCILIATION_VARIANCE_DECISION",
            "task_id": decision.task_id,
            "event_id": decision.event_id,
            "operation_id": decision.operation_id,
            "reasons": [
                "reconciliation completed autonomously but observed evidence differs from expected evidence",
                "no money movement, contact, correction, or accounting conclusion was authorized",
            ],
            "variance_minor": result["variance_minor"],
            "currency": result["currency"],
            "external_action_taken": False,
        }
    return out
