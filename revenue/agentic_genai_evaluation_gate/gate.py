"""Deterministic pre-release evidence gate for agentic GenAI evaluations.

This module never executes an agent or tool. It only compiles already-produced
synthetic/non-production evaluation evidence into a deterministic review receipt.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = 1
RECEIPT_SCHEMA_VERSION = 1
DECISION_RELEASE = "RELEASE_CANDIDATE"
DECISION_HOLD = "HOLD"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_CATEGORIES = {"NORMAL", "TOOL_USING", "ADVERSARIAL", "DEGRADED_OBSERVABILITY"}
_ALLOWED_EFFECTS = {"READ_ONLY", "LOCAL_MUTATION", "EXTERNAL_SIDE_EFFECT"}
_ALLOWED_RESULT = {"SUCCESS", "FAILURE", "UNKNOWN"}
_ALLOWED_PASSFAIL = {"PASS", "FAIL"}
_ALLOWED_SAFETY = {"PASS", "FAIL", "UNKNOWN"}
_ALLOWED_OBSERVABILITY = {"COMPLETE", "DEGRADED", "MISSING"}

_TOP_KEYS = {
    "schema_version", "evaluation_id", "evaluation_set", "agent_build",
    "rubric", "policy", "scenarios",
}
_ESET_KEYS = {"set_id", "generation", "sha256", "required_scenarios"}
_BUILD_KEYS = {"agent_id", "version", "sha256"}
_RUBRIC_KEYS = {"rubric_id", "generation", "sha256", "minimum_score_bps"}
_POLICY_KEYS = {"max_evidence_age_seconds", "require_human_review", "require_complete_observability"}
_SCENARIO_KEYS = {
    "scenario_id", "category", "agent_build_sha256", "rubric_sha256",
    "trace_sha256", "result_sha256", "evidence_at", "automated_score_bps",
    "automated_status", "automated_evidence_sha256", "human_review", "safety", "observability", "tool_calls",
}
_REVIEW_KEYS = {
    "review_id", "reviewer_role", "decision", "decided_at",
    "agent_build_sha256", "rubric_sha256", "trace_sha256", "result_sha256",
}
_SAFETY_KEYS = {
    "status", "checks_sha256", "observed_at", "agent_build_sha256",
    "trace_sha256", "result_sha256",
}
_OBS_KEYS = {"status", "pointer_sha256", "observed_at", "trace_sha256", "result_sha256"}
_TOOL_KEYS = {"call_id", "tool", "action", "effect_class", "result_status", "trace_sha256"}

_REASON_ORDER = [
    "INVALID_SCHEMA_VERSION",
    "INVALID_EVALUATION_ID",
    "INVALID_EVALUATION_SET",
    "INVALID_AGENT_BUILD",
    "INVALID_RUBRIC",
    "INVALID_POLICY",
    "INVALID_SCENARIO",
    "DUPLICATE_SCENARIO_ID",
    "SCENARIO_UNIVERSE_MISMATCH",
    "AGENT_BUILD_MISMATCH",
    "RUBRIC_MISMATCH",
    "TRACE_BINDING_MISMATCH",
    "RESULT_BINDING_MISMATCH",
    "FUTURE_EVIDENCE",
    "STALE_EVIDENCE",
    "AUTOMATED_RESULT_BINDING_MISMATCH",
    "AUTOMATED_SCORE_BELOW_THRESHOLD",
    "AUTOMATED_EVALUATION_FAILED",
    "HUMAN_REVIEW_MISSING",
    "HUMAN_REVIEW_FAILED",
    "SAFETY_UNKNOWN",
    "SAFETY_FAILED",
    "OBSERVABILITY_INCOMPLETE",
    "TOOL_RESULT_UNKNOWN",
    "TOOL_RESULT_FAILED",
]


class EvidenceError(ValueError):
    """Raised for malformed evidence that cannot safely be interpreted."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_object(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _require_dict(value: Any, *, name: str, keys: set[str]) -> dict[str, Any]:
    if type(value) is not dict:
        raise EvidenceError(f"{name}: expected object")
    unknown = set(value) - keys
    missing = keys - set(value)
    if unknown or missing:
        raise EvidenceError(f"{name}: keys mismatch missing={sorted(missing)} unknown={sorted(unknown)}")
    return value


def _require_str(value: Any, *, name: str, allowed: set[str] | None = None) -> str:
    if type(value) is not str or not value:
        raise EvidenceError(f"{name}: expected non-empty string")
    if allowed is not None and value not in allowed:
        raise EvidenceError(f"{name}: invalid value")
    return value


def _require_id(value: Any, *, name: str) -> str:
    text = _require_str(value, name=name)
    if not _ID_RE.fullmatch(text):
        raise EvidenceError(f"{name}: invalid identifier")
    return text


def _require_sha(value: Any, *, name: str) -> str:
    text = _require_str(value, name=name)
    if not _SHA_RE.fullmatch(text):
        raise EvidenceError(f"{name}: invalid sha256")
    return text


def _require_int(value: Any, *, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not (minimum <= value <= maximum):
        raise EvidenceError(f"{name}: expected integer in [{minimum}, {maximum}]")
    return value


def _require_bool(value: Any, *, name: str) -> bool:
    if type(value) is not bool:
        raise EvidenceError(f"{name}: expected boolean")
    return value


def _parse_utc(value: Any, *, name: str) -> datetime:
    text = _require_str(value, name=name)
    if not text.endswith("Z"):
        raise EvidenceError(f"{name}: must be UTC Z timestamp")
    try:
        dt = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise EvidenceError(f"{name}: invalid timestamp") from exc
    if dt.tzinfo != timezone.utc:
        raise EvidenceError(f"{name}: must be UTC")
    # Canonical second precision only.
    canonical = dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if text != canonical:
        raise EvidenceError(f"{name}: non-canonical timestamp")
    return dt


def _format_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise EvidenceError("evaluation instant must be timezone-aware")
    normalized = dt.astimezone(timezone.utc).replace(microsecond=0)
    return normalized.isoformat().replace("+00:00", "Z")


def _validate_time(
    value: Any,
    *,
    name: str,
    evaluated_at: datetime,
    max_age_seconds: int,
    reasons: set[str],
) -> datetime | None:
    dt = _parse_utc(value, name=name)
    if dt > evaluated_at:
        reasons.add("FUTURE_EVIDENCE")
    elif int((evaluated_at - dt).total_seconds()) > max_age_seconds:
        reasons.add("STALE_EVIDENCE")
    return dt


def _validate_tool_calls(
    calls: Any,
    *,
    scenario_id: str,
    trace_sha: str,
    reasons: set[str],
) -> list[dict[str, Any]]:
    if type(calls) is not list:
        raise EvidenceError(f"scenario[{scenario_id}].tool_calls: expected array")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(calls):
        call = _require_dict(raw, name=f"scenario[{scenario_id}].tool_calls[{index}]", keys=_TOOL_KEYS)
        call_id = _require_id(call["call_id"], name="call_id")
        if call_id in seen:
            raise EvidenceError(f"scenario[{scenario_id}]: duplicate tool call id")
        seen.add(call_id)
        _require_id(call["tool"], name="tool")
        _require_id(call["action"], name="action")
        _require_str(call["effect_class"], name="effect_class", allowed=_ALLOWED_EFFECTS)
        status = _require_str(call["result_status"], name="result_status", allowed=_ALLOWED_RESULT)
        call_trace = _require_sha(call["trace_sha256"], name="tool trace_sha256")
        if call_trace != trace_sha:
            reasons.add("TRACE_BINDING_MISMATCH")
        if status == "UNKNOWN":
            reasons.add("TOOL_RESULT_UNKNOWN")
        elif status == "FAILURE":
            reasons.add("TOOL_RESULT_FAILED")
        normalized.append(deepcopy(call))
    normalized.sort(key=lambda item: item["call_id"])
    return normalized


def _validate_scenario(
    raw: Any,
    *,
    build_sha: str,
    rubric_sha: str,
    minimum_score_bps: int,
    evaluated_at: datetime,
    policy: Mapping[str, Any],
    reasons: set[str],
) -> dict[str, Any]:
    scenario = _require_dict(raw, name="scenario", keys=_SCENARIO_KEYS)
    scenario_id = _require_id(scenario["scenario_id"], name="scenario_id")
    _require_str(scenario["category"], name="category", allowed=_ALLOWED_CATEGORIES)

    scenario_build = _require_sha(scenario["agent_build_sha256"], name="scenario agent_build_sha256")
    scenario_rubric = _require_sha(scenario["rubric_sha256"], name="scenario rubric_sha256")
    trace_sha = _require_sha(scenario["trace_sha256"], name="scenario trace_sha256")
    result_sha = _require_sha(scenario["result_sha256"], name="scenario result_sha256")
    max_age = policy["max_evidence_age_seconds"]
    _validate_time(
        scenario["evidence_at"],
        name=f"scenario[{scenario_id}].evidence_at",
        evaluated_at=evaluated_at,
        max_age_seconds=max_age,
        reasons=reasons,
    )
    if scenario_build != build_sha:
        reasons.add("AGENT_BUILD_MISMATCH")
    if scenario_rubric != rubric_sha:
        reasons.add("RUBRIC_MISMATCH")

    score = _require_int(
        scenario["automated_score_bps"],
        name=f"scenario[{scenario_id}].automated_score_bps",
        minimum=0,
        maximum=10_000,
    )
    automated = _require_str(
        scenario["automated_status"],
        name=f"scenario[{scenario_id}].automated_status",
        allowed=_ALLOWED_PASSFAIL,
    )
    automated_binding = _require_sha(
        scenario["automated_evidence_sha256"],
        name=f"scenario[{scenario_id}].automated_evidence_sha256",
    )
    expected_automated_binding = sha256_object(
        {
            "scenario_id": scenario_id,
            "trace_sha256": trace_sha,
            "result_sha256": result_sha,
            "automated_score_bps": score,
            "automated_status": automated,
        }
    )
    if automated_binding != expected_automated_binding:
        reasons.add("AUTOMATED_RESULT_BINDING_MISMATCH")
    if score < minimum_score_bps:
        reasons.add("AUTOMATED_SCORE_BELOW_THRESHOLD")
    if automated != "PASS":
        reasons.add("AUTOMATED_EVALUATION_FAILED")

    review_raw = scenario["human_review"]
    if review_raw is None:
        if policy["require_human_review"]:
            reasons.add("HUMAN_REVIEW_MISSING")
        review = None
    else:
        review = _require_dict(review_raw, name=f"scenario[{scenario_id}].human_review", keys=_REVIEW_KEYS)
        _require_id(review["review_id"], name="review_id")
        _require_id(review["reviewer_role"], name="reviewer_role")
        decision = _require_str(review["decision"], name="review decision", allowed=_ALLOWED_PASSFAIL)
        _validate_time(
            review["decided_at"],
            name=f"scenario[{scenario_id}].human_review.decided_at",
            evaluated_at=evaluated_at,
            max_age_seconds=max_age,
            reasons=reasons,
        )
        if _require_sha(review["agent_build_sha256"], name="review agent_build_sha256") != build_sha:
            reasons.add("AGENT_BUILD_MISMATCH")
        if _require_sha(review["rubric_sha256"], name="review rubric_sha256") != rubric_sha:
            reasons.add("RUBRIC_MISMATCH")
        if _require_sha(review["trace_sha256"], name="review trace_sha256") != trace_sha:
            reasons.add("TRACE_BINDING_MISMATCH")
        if _require_sha(review["result_sha256"], name="review result_sha256") != result_sha:
            reasons.add("RESULT_BINDING_MISMATCH")
        if decision != "PASS":
            reasons.add("HUMAN_REVIEW_FAILED")

    safety = _require_dict(scenario["safety"], name=f"scenario[{scenario_id}].safety", keys=_SAFETY_KEYS)
    safety_status = _require_str(safety["status"], name="safety status", allowed=_ALLOWED_SAFETY)
    _require_sha(safety["checks_sha256"], name="safety checks_sha256")
    _validate_time(
        safety["observed_at"],
        name=f"scenario[{scenario_id}].safety.observed_at",
        evaluated_at=evaluated_at,
        max_age_seconds=max_age,
        reasons=reasons,
    )
    if _require_sha(safety["agent_build_sha256"], name="safety agent_build_sha256") != build_sha:
        reasons.add("AGENT_BUILD_MISMATCH")
    if _require_sha(safety["trace_sha256"], name="safety trace_sha256") != trace_sha:
        reasons.add("TRACE_BINDING_MISMATCH")
    if _require_sha(safety["result_sha256"], name="safety result_sha256") != result_sha:
        reasons.add("RESULT_BINDING_MISMATCH")
    if safety_status == "UNKNOWN":
        reasons.add("SAFETY_UNKNOWN")
    elif safety_status == "FAIL":
        reasons.add("SAFETY_FAILED")

    observability = _require_dict(
        scenario["observability"], name=f"scenario[{scenario_id}].observability", keys=_OBS_KEYS
    )
    obs_status = _require_str(
        observability["status"], name="observability status", allowed=_ALLOWED_OBSERVABILITY
    )
    _require_sha(observability["pointer_sha256"], name="observability pointer_sha256")
    _validate_time(
        observability["observed_at"],
        name=f"scenario[{scenario_id}].observability.observed_at",
        evaluated_at=evaluated_at,
        max_age_seconds=max_age,
        reasons=reasons,
    )
    if _require_sha(observability["trace_sha256"], name="observability trace_sha256") != trace_sha:
        reasons.add("TRACE_BINDING_MISMATCH")
    if _require_sha(observability["result_sha256"], name="observability result_sha256") != result_sha:
        reasons.add("RESULT_BINDING_MISMATCH")
    if policy["require_complete_observability"] and obs_status != "COMPLETE":
        reasons.add("OBSERVABILITY_INCOMPLETE")

    normalized = deepcopy(scenario)
    normalized["tool_calls"] = _validate_tool_calls(
        scenario["tool_calls"], scenario_id=scenario_id, trace_sha=trace_sha, reasons=reasons
    )
    return normalized


def _ordered_reasons(reasons: Iterable[str]) -> list[str]:
    values = set(reasons)
    known = [reason for reason in _REASON_ORDER if reason in values]
    unknown = sorted(values - set(_REASON_ORDER))
    return known + unknown


def validate_packet(packet: Any, *, evaluated_at: datetime) -> tuple[dict[str, Any], list[str]]:
    """Validate and normalize one evaluation packet."""
    top = _require_dict(packet, name="packet", keys=_TOP_KEYS)
    if _require_int(top["schema_version"], name="schema_version", minimum=1, maximum=1) != SCHEMA_VERSION:
        raise EvidenceError("unsupported schema_version")
    _require_id(top["evaluation_id"], name="evaluation_id")

    eset = _require_dict(top["evaluation_set"], name="evaluation_set", keys=_ESET_KEYS)
    _require_id(eset["set_id"], name="evaluation_set.set_id")
    _require_int(eset["generation"], name="evaluation_set.generation", minimum=1, maximum=2**31 - 1)
    _require_sha(eset["sha256"], name="evaluation_set.sha256")
    required = eset["required_scenarios"]
    if type(required) is not list or not required:
        raise EvidenceError("evaluation_set.required_scenarios: expected non-empty array")
    required_ids = [_require_id(item, name="required scenario id") for item in required]
    if len(required_ids) != len(set(required_ids)):
        raise EvidenceError("evaluation_set.required_scenarios: duplicate id")

    build = _require_dict(top["agent_build"], name="agent_build", keys=_BUILD_KEYS)
    _require_id(build["agent_id"], name="agent_build.agent_id")
    _require_id(build["version"], name="agent_build.version")
    build_sha = _require_sha(build["sha256"], name="agent_build.sha256")

    rubric = _require_dict(top["rubric"], name="rubric", keys=_RUBRIC_KEYS)
    _require_id(rubric["rubric_id"], name="rubric.rubric_id")
    _require_int(rubric["generation"], name="rubric.generation", minimum=1, maximum=2**31 - 1)
    rubric_sha = _require_sha(rubric["sha256"], name="rubric.sha256")
    minimum_score = _require_int(
        rubric["minimum_score_bps"], name="rubric.minimum_score_bps", minimum=0, maximum=10_000
    )

    policy = _require_dict(top["policy"], name="policy", keys=_POLICY_KEYS)
    _require_int(
        policy["max_evidence_age_seconds"],
        name="policy.max_evidence_age_seconds",
        minimum=60,
        maximum=31_536_000,
    )
    _require_bool(policy["require_human_review"], name="policy.require_human_review")
    _require_bool(policy["require_complete_observability"], name="policy.require_complete_observability")

    if type(top["scenarios"]) is not list:
        raise EvidenceError("scenarios: expected array")

    reasons: set[str] = set()
    normalized_scenarios: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in top["scenarios"]:
        normalized = _validate_scenario(
            raw,
            build_sha=build_sha,
            rubric_sha=rubric_sha,
            minimum_score_bps=minimum_score,
            evaluated_at=evaluated_at,
            policy=policy,
            reasons=reasons,
        )
        scenario_id = normalized["scenario_id"]
        if scenario_id in seen:
            reasons.add("DUPLICATE_SCENARIO_ID")
        seen.add(scenario_id)
        normalized_scenarios.append(normalized)

    if seen != set(required_ids) or len(normalized_scenarios) != len(required_ids):
        reasons.add("SCENARIO_UNIVERSE_MISMATCH")

    normalized_packet = deepcopy(top)
    normalized_packet["evaluation_set"]["required_scenarios"] = sorted(required_ids)
    normalized_packet["scenarios"] = sorted(normalized_scenarios, key=lambda item: item["scenario_id"])
    return normalized_packet, _ordered_reasons(reasons)


def compile_receipt(packet: Any, *, evaluated_at: datetime) -> dict[str, Any]:
    """Compile deterministic release-review evidence for one trusted instant."""
    evaluated_text = _format_utc(evaluated_at)
    normalized, reasons = validate_packet(packet, evaluated_at=_parse_utc(evaluated_text, name="evaluated_at"))
    categories = {name: 0 for name in sorted(_ALLOWED_CATEGORIES)}
    tool_calls = 0
    side_effect_calls = 0
    for scenario in normalized["scenarios"]:
        categories[scenario["category"]] += 1
        tool_calls += len(scenario["tool_calls"])
        side_effect_calls += sum(
            1 for item in scenario["tool_calls"] if item["effect_class"] == "EXTERNAL_SIDE_EFFECT"
        )

    receipt: dict[str, Any] = {
        "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
        "evaluation_id": normalized["evaluation_id"],
        "evaluation_set": {
            "set_id": normalized["evaluation_set"]["set_id"],
            "generation": normalized["evaluation_set"]["generation"],
            "sha256": normalized["evaluation_set"]["sha256"],
        },
        "agent_build": deepcopy(normalized["agent_build"]),
        "rubric": deepcopy(normalized["rubric"]),
        "evaluated_at": evaluated_text,
        "packet_sha256": sha256_object(normalized),
        "scenario_count": len(normalized["scenarios"]),
        "category_counts": categories,
        "tool_call_count": tool_calls,
        "external_side_effect_call_count": side_effect_calls,
        "decision": DECISION_RELEASE if not reasons else DECISION_HOLD,
        "reason_codes": reasons,
        "authority": {
            "model_deployment": False,
            "tool_execution": False,
            "provider_mutation": False,
            "customer_data_access": False,
            "compliance_certification": False,
            "payment": False,
            "external_contact": False,
            "revenue_recognition": False,
        },
    }
    receipt["receipt_sha256"] = sha256_object(receipt)
    return receipt


def verify_receipt(packet: Any, receipt: Any, *, verified_at: datetime) -> dict[str, Any]:
    """Verify receipt integrity and reassess release truth at verifier-owned current time."""
    if type(receipt) is not dict:
        return {"valid": False, "reason": "RECEIPT_NOT_OBJECT"}
    try:
        claimed_at = _parse_utc(receipt.get("evaluated_at"), name="receipt.evaluated_at")
        verified_text = _format_utc(verified_at)
        verifier_now = _parse_utc(verified_text, name="verified_at")
        if claimed_at > verifier_now:
            return {"valid": False, "reason": "RECEIPT_FROM_FUTURE"}
        historical = compile_receipt(packet, evaluated_at=claimed_at)
    except EvidenceError as exc:
        return {"valid": False, "reason": "MALFORMED_EVIDENCE", "detail": str(exc)}

    if _canonical_bytes(receipt) != _canonical_bytes(historical):
        return {"valid": False, "reason": "RECEIPT_MISMATCH"}

    try:
        current = compile_receipt(packet, evaluated_at=verifier_now)
    except EvidenceError as exc:
        return {"valid": False, "reason": "MALFORMED_EVIDENCE", "detail": str(exc)}

    if current["decision"] != DECISION_RELEASE:
        return {
            "valid": False,
            "reason": "CURRENT_EVIDENCE_HOLD",
            "decision": DECISION_HOLD,
            "reason_codes": current["reason_codes"],
            "receipt_sha256": historical["receipt_sha256"],
            "verified_at": verified_text,
        }
    return {
        "valid": True,
        "reason": "VERIFIED",
        "decision": DECISION_RELEASE,
        "receipt_sha256": historical["receipt_sha256"],
        "verified_at": verified_text,
    }


def render_markdown(receipt: Mapping[str, Any]) -> str:
    """Render a compact deterministic human review projection."""
    reasons = receipt["reason_codes"] or ["NONE"]
    cats = receipt["category_counts"]
    return "\n".join(
        [
            "# Agentic GenAI Evaluation Evidence Gate",
            "",
            f"- Decision: **{receipt['decision']}**",
            f"- Evaluation: `{receipt['evaluation_id']}`",
            f"- Agent build: `{receipt['agent_build']['agent_id']}@{receipt['agent_build']['version']}`",
            f"- Agent SHA-256: `{receipt['agent_build']['sha256']}`",
            f"- Rubric: `{receipt['rubric']['rubric_id']}@{receipt['rubric']['generation']}`",
            f"- Evaluated at: `{receipt['evaluated_at']}`",
            f"- Scenarios: `{receipt['scenario_count']}`",
            f"- Categories: `{json.dumps(cats, sort_keys=True, separators=(',', ':'))}`",
            f"- Tool calls: `{receipt['tool_call_count']}` "
            f"(external-side-effect evidence: `{receipt['external_side_effect_call_count']}`)",
            f"- Reasons: `{','.join(reasons)}`",
            f"- Packet SHA-256: `{receipt['packet_sha256']}`",
            f"- Receipt SHA-256: `{receipt['receipt_sha256']}`",
            "",
            "This receipt is review evidence only. It authorizes no deployment, tool execution, "
            "provider mutation, customer-data access, compliance conclusion, payment, contact, "
            "or revenue recognition.",
            "",
        ]
    )
