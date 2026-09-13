#!/usr/bin/env python3
"""Deterministic offline acceptance evaluator for LACSD project 04254 evidence.

This module evaluates synthetic or customer-approved fixture packets only. It emits
work *intents* as evidence objects; it never executes maintenance, network, or buyer
operations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "lacsd-04254-evidence-v1"
POLICY_VERSION = "lacsd-04254-policy-v1"
RECEIPT_VERSION = "lacsd-04254-receipt-v1"
OPPORTUNITY_ID = "LACSD-04254"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
_SITE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,31}$")
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

_ALLOWED_QUALITY = frozenset({"GOOD", "MISSING", "SUSPECT"})
_ALLOWED_DECISIONS = frozenset({"WORK_INTENT", "NO_ACTION", "HOLD"})
_ALLOWED_ANOMALIES = frozenset({
    "BLOCKAGE_SUSPECTED",
    "I_AND_I_SUSPECTED",
    "NONE",
    "UNDETERMINED",
})
_REQUIRED_INTENTS = ("INSPECT_BLOCKAGE", "INVESTIGATE_I_AND_I")


class ValidationError(ValueError):
    """Raised when an input or policy violates the fail-closed contract."""


def canonical_bytes(value: Any) -> bytes:
    """Return the canonical UTF-8 JSON encoding used for every content hash."""

    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"value is not canonical JSON: {exc}") from exc
    return encoded.encode("utf-8")


def canonical_text(value: Any) -> str:
    """Return a newline-terminated human/tool friendly canonical receipt."""

    return json.dumps(
        value,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _reject_duplicate_keys(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except ValidationError:
        raise
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}"
        ) from exc


def _require_object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be an object")
    return value


def _require_list(value: Any, name: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{name} must be an array")
    return value


def _require_exact_keys(
    value: Mapping[str, Any], *, required: set[str], name: str
) -> None:
    keys = set(value)
    missing = sorted(required - keys)
    extra = sorted(keys - required)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if extra:
            details.append(f"extra={','.join(extra)}")
        raise ValidationError(f"{name} keys invalid ({'; '.join(details)})")


def _require_string(value: Any, name: str, *, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{name} must be a non-empty string")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise ValidationError(f"{name} has invalid format")
    return value


def _require_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{name} must be boolean")
    return value


def _require_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{name} must be an integer")
    if value < minimum or value > maximum:
        raise ValidationError(f"{name} must be in [{minimum}, {maximum}]")
    return value


def _require_number(value: Any, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValidationError(f"{name} must be finite")
    if number < minimum or number > maximum:
        raise ValidationError(f"{name} must be in [{minimum}, {maximum}]")
    return number


def _parse_timestamp(value: Any, name: str) -> datetime:
    text = _require_string(value, name, pattern=_TIMESTAMP_RE)
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValidationError(f"{name} is not a valid UTC timestamp") from exc
    return parsed.replace(tzinfo=timezone.utc)


def _validate_policy(policy: Any) -> Mapping[str, Any]:
    obj = _require_object(policy, "policy")
    _require_exact_keys(
        obj,
        required={
            "schema_version",
            "policy_id",
            "external_execution",
            "allowed_intents",
            "work_intent_namespace",
            "min_points",
            "freshness_max_seconds",
            "max_gap_seconds",
            "numeric_bounds",
            "blockage",
            "storm_ii",
        },
        name="policy",
    )
    if obj["schema_version"] != POLICY_VERSION:
        raise ValidationError(f"policy.schema_version must equal {POLICY_VERSION}")
    _require_string(obj["policy_id"], "policy.policy_id", pattern=_ID_RE)
    if _require_bool(obj["external_execution"], "policy.external_execution"):
        raise ValidationError("policy.external_execution must remain false")

    intents = _require_list(obj["allowed_intents"], "policy.allowed_intents")
    if tuple(intents) != _REQUIRED_INTENTS:
        raise ValidationError(
            "policy.allowed_intents must be exactly INSPECT_BLOCKAGE, "
            "INVESTIGATE_I_AND_I"
        )
    _require_string(
        obj["work_intent_namespace"],
        "policy.work_intent_namespace",
        pattern=_ID_RE,
    )
    _require_int(obj["min_points"], "policy.min_points", 4, 64)
    _require_int(
        obj["freshness_max_seconds"],
        "policy.freshness_max_seconds",
        1,
        86_400,
    )
    _require_int(obj["max_gap_seconds"], "policy.max_gap_seconds", 1, 86_400)

    bounds = _require_object(obj["numeric_bounds"], "policy.numeric_bounds")
    _require_exact_keys(
        bounds,
        required={"flow_lps", "level_pct", "rain_mm_15m"},
        name="policy.numeric_bounds",
    )
    for key in ("flow_lps", "level_pct", "rain_mm_15m"):
        pair = _require_list(bounds[key], f"policy.numeric_bounds.{key}")
        if len(pair) != 2:
            raise ValidationError(f"policy.numeric_bounds.{key} must have two values")
        low = _require_number(pair[0], f"policy.numeric_bounds.{key}[0]", -1e12, 1e12)
        high = _require_number(pair[1], f"policy.numeric_bounds.{key}[1]", -1e12, 1e12)
        if low >= high:
            raise ValidationError(f"policy.numeric_bounds.{key} must increase")

    blockage = _require_object(obj["blockage"], "policy.blockage")
    _require_exact_keys(
        blockage,
        required={"max_rain_mm_15m", "min_level_rise_pct", "min_flow_drop_ratio"},
        name="policy.blockage",
    )
    _require_number(
        blockage["max_rain_mm_15m"],
        "policy.blockage.max_rain_mm_15m",
        0.0,
        1000.0,
    )
    _require_number(
        blockage["min_level_rise_pct"],
        "policy.blockage.min_level_rise_pct",
        0.0,
        100.0,
    )
    _require_number(
        blockage["min_flow_drop_ratio"],
        "policy.blockage.min_flow_drop_ratio",
        0.0,
        1.0,
    )

    storm = _require_object(obj["storm_ii"], "policy.storm_ii")
    _require_exact_keys(
        storm,
        required={"min_rain_mm_15m", "min_level_rise_pct", "min_flow_rise_ratio"},
        name="policy.storm_ii",
    )
    _require_number(
        storm["min_rain_mm_15m"],
        "policy.storm_ii.min_rain_mm_15m",
        0.0,
        1000.0,
    )
    _require_number(
        storm["min_level_rise_pct"],
        "policy.storm_ii.min_level_rise_pct",
        0.0,
        100.0,
    )
    _require_number(
        storm["min_flow_rise_ratio"],
        "policy.storm_ii.min_flow_rise_ratio",
        0.0,
        10.0,
    )

    if int(obj["max_gap_seconds"]) > int(obj["freshness_max_seconds"]):
        raise ValidationError(
            "policy.max_gap_seconds cannot exceed freshness_max_seconds"
        )
    return obj


def _validate_expected(value: Any, name: str) -> Mapping[str, Any]:
    expected = _require_object(value, name)
    _require_exact_keys(
        expected,
        required={"decision", "anomaly_class", "work_intents", "hold_reason"},
        name=name,
    )
    decision = _require_string(expected["decision"], f"{name}.decision")
    if decision not in _ALLOWED_DECISIONS:
        raise ValidationError(f"{name}.decision is not approved")
    anomaly = _require_string(expected["anomaly_class"], f"{name}.anomaly_class")
    if anomaly not in _ALLOWED_ANOMALIES:
        raise ValidationError(f"{name}.anomaly_class is not approved")
    work_intents = _require_int(expected["work_intents"], f"{name}.work_intents", 0, 1)
    hold_reason = expected["hold_reason"]
    if hold_reason is not None:
        _require_string(hold_reason, f"{name}.hold_reason", pattern=_ID_RE)

    if decision == "WORK_INTENT":
        if work_intents != 1 or anomaly not in {
            "BLOCKAGE_SUSPECTED",
            "I_AND_I_SUSPECTED",
        } or hold_reason is not None:
            raise ValidationError(f"{name} has inconsistent WORK_INTENT expectation")
    elif decision == "NO_ACTION":
        if work_intents != 0 or anomaly != "NONE" or hold_reason is not None:
            raise ValidationError(f"{name} has inconsistent NO_ACTION expectation")
    else:
        if work_intents != 0 or anomaly != "UNDETERMINED" or hold_reason is None:
            raise ValidationError(f"{name} has inconsistent HOLD expectation")
    return expected


def _validate_packet(
    value: Any, name: str, bounds: Mapping[str, Any]
) -> dict[str, Any]:
    packet = _require_object(value, name)
    _require_exact_keys(
        packet,
        required={
            "packet_id",
            "observed_at",
            "flow_lps",
            "level_pct",
            "rain_mm_15m",
            "quality",
        },
        name=name,
    )
    packet_id = _require_string(packet["packet_id"], f"{name}.packet_id", pattern=_ID_RE)
    observed_at = _require_string(
        packet["observed_at"], f"{name}.observed_at", pattern=_TIMESTAMP_RE
    )
    _parse_timestamp(observed_at, f"{name}.observed_at")
    quality = _require_string(packet["quality"], f"{name}.quality")
    if quality not in _ALLOWED_QUALITY:
        raise ValidationError(f"{name}.quality is not approved")

    normalized: dict[str, Any] = {
        "packet_id": packet_id,
        "observed_at": observed_at,
        "flow_lps": _require_number(
            packet["flow_lps"],
            f"{name}.flow_lps",
            float(bounds["flow_lps"][0]),
            float(bounds["flow_lps"][1]),
        ),
        "level_pct": _require_number(
            packet["level_pct"],
            f"{name}.level_pct",
            float(bounds["level_pct"][0]),
            float(bounds["level_pct"][1]),
        ),
        "rain_mm_15m": _require_number(
            packet["rain_mm_15m"],
            f"{name}.rain_mm_15m",
            float(bounds["rain_mm_15m"][0]),
            float(bounds["rain_mm_15m"][1]),
        ),
        "quality": quality,
    }
    return normalized


def _validate_document(document: Any, policy: Mapping[str, Any]) -> Mapping[str, Any]:
    obj = _require_object(document, "document")
    _require_exact_keys(
        obj,
        required={"schema_version", "opportunity_id", "model", "fixtures"},
        name="document",
    )
    if obj["schema_version"] != SCHEMA_VERSION:
        raise ValidationError(f"document.schema_version must equal {SCHEMA_VERSION}")
    if obj["opportunity_id"] != OPPORTUNITY_ID:
        raise ValidationError(f"document.opportunity_id must equal {OPPORTUNITY_ID}")

    model = _require_object(obj["model"], "document.model")
    _require_exact_keys(
        model,
        required={"model_id", "artifact_sha256", "configuration_id"},
        name="document.model",
    )
    _require_string(model["model_id"], "document.model.model_id", pattern=_ID_RE)
    _require_string(
        model["configuration_id"],
        "document.model.configuration_id",
        pattern=_ID_RE,
    )
    _require_string(
        model["artifact_sha256"],
        "document.model.artifact_sha256",
        pattern=_SHA256_RE,
    )

    fixtures = _require_list(obj["fixtures"], "document.fixtures")
    if not fixtures or len(fixtures) > 100:
        raise ValidationError("document.fixtures must contain 1..100 scenarios")

    seen_scenarios: set[str] = set()
    for index, raw in enumerate(fixtures):
        name = f"document.fixtures[{index}]"
        scenario = _require_object(raw, name)
        _require_exact_keys(
            scenario,
            required={
                "scenario_id",
                "site_id",
                "evaluation_at",
                "packets",
                "expected",
            },
            name=name,
        )
        scenario_id = _require_string(
            scenario["scenario_id"], f"{name}.scenario_id", pattern=_ID_RE
        )
        if scenario_id in seen_scenarios:
            raise ValidationError(f"duplicate scenario_id: {scenario_id}")
        seen_scenarios.add(scenario_id)
        _require_string(scenario["site_id"], f"{name}.site_id", pattern=_SITE_RE)
        _parse_timestamp(scenario["evaluation_at"], f"{name}.evaluation_at")
        packets = _require_list(scenario["packets"], f"{name}.packets")
        if not packets or len(packets) > 128:
            raise ValidationError(f"{name}.packets must contain 1..128 packets")
        for packet_index, packet in enumerate(packets):
            _validate_packet(
                packet,
                f"{name}.packets[{packet_index}]",
                policy["numeric_bounds"],
            )
        _validate_expected(scenario["expected"], f"{name}.expected")
    return obj


def _hold_result(reason: str, duplicate_count: int = 0) -> dict[str, Any]:
    return {
        "decision": "HOLD",
        "anomaly_class": "UNDETERMINED",
        "hold_reason": reason,
        "work_intents": [],
        "duplicates_suppressed": duplicate_count,
    }


def _make_work_intent(
    *,
    action: str,
    anomaly_class: str,
    scenario_id: str,
    site_id: str,
    unique_packets: Sequence[Mapping[str, Any]],
    model: Mapping[str, Any],
    policy: Mapping[str, Any],
    policy_sha256: str,
) -> dict[str, Any]:
    evidence_sha256 = sha256_hex(list(unique_packets))
    identity_material = {
        "namespace": policy["work_intent_namespace"],
        "scenario_id": scenario_id,
        "site_id": site_id,
        "action": action,
        "anomaly_class": anomaly_class,
        "evidence_sha256": evidence_sha256,
        "model_artifact_sha256": model["artifact_sha256"],
        "policy_sha256": policy_sha256,
    }
    intent_id = "wi_" + sha256_hex(identity_material)[:32]
    return {
        "work_intent_id": intent_id,
        "idempotency_key": intent_id,
        "action": action,
        "site_id": site_id,
        "anomaly_class": anomaly_class,
        "evidence_sha256": evidence_sha256,
        "model_id": model["model_id"],
        "model_artifact_sha256": model["artifact_sha256"],
        "configuration_id": model["configuration_id"],
        "policy_id": policy["policy_id"],
        "policy_sha256": policy_sha256,
        "intent_only": True,
        "external_execution": False,
    }


def _evaluate_scenario(
    scenario: Mapping[str, Any],
    *,
    model: Mapping[str, Any],
    policy: Mapping[str, Any],
    policy_sha256: str,
) -> dict[str, Any]:
    normalized_packets = [
        _validate_packet(
            packet,
            f"scenario[{scenario['scenario_id']}].packet",
            policy["numeric_bounds"],
        )
        for packet in scenario["packets"]
    ]

    seen: dict[str, bytes] = {}
    unique_packets: list[dict[str, Any]] = []
    duplicate_count = 0
    for packet in normalized_packets:
        fingerprint = canonical_bytes(packet)
        packet_id = packet["packet_id"]
        if packet_id in seen:
            if seen[packet_id] != fingerprint:
                result = _hold_result("CONFLICTING_PACKET_ID", duplicate_count)
                result["evidence"] = {
                    "packet_count": len(normalized_packets),
                    "unique_packet_count": len(unique_packets),
                    "packet_ids": [p["packet_id"] for p in unique_packets],
                }
                return result
            duplicate_count += 1
            continue
        seen[packet_id] = fingerprint
        unique_packets.append(packet)

    if len(unique_packets) < int(policy["min_points"]):
        result = _hold_result("INSUFFICIENT_POINTS", duplicate_count)
        result["evidence"] = {
            "packet_count": len(normalized_packets),
            "unique_packet_count": len(unique_packets),
            "packet_ids": [p["packet_id"] for p in unique_packets],
        }
        return result

    observed = [
        _parse_timestamp(packet["observed_at"], "packet.observed_at")
        for packet in unique_packets
    ]
    for previous, current in zip(observed, observed[1:]):
        if current <= previous:
            result = _hold_result("NON_MONOTONIC_TIME", duplicate_count)
            result["evidence"] = {
                "packet_count": len(normalized_packets),
                "unique_packet_count": len(unique_packets),
                "packet_ids": [p["packet_id"] for p in unique_packets],
            }
            return result

    if any(packet["quality"] != "GOOD" for packet in unique_packets):
        result = _hold_result("SENSOR_QUALITY", duplicate_count)
        result["evidence"] = {
            "packet_count": len(normalized_packets),
            "unique_packet_count": len(unique_packets),
            "packet_ids": [p["packet_id"] for p in unique_packets],
        }
        return result

    gaps = [int((current - previous).total_seconds()) for previous, current in zip(observed, observed[1:])]
    max_gap = max(gaps, default=0)
    if max_gap > int(policy["max_gap_seconds"]):
        result = _hold_result("SENSOR_GAP", duplicate_count)
        result["evidence"] = {
            "packet_count": len(normalized_packets),
            "unique_packet_count": len(unique_packets),
            "packet_ids": [p["packet_id"] for p in unique_packets],
            "max_gap_seconds": max_gap,
        }
        return result

    evaluation_at = _parse_timestamp(scenario["evaluation_at"], "scenario.evaluation_at")
    age_seconds = int((evaluation_at - observed[-1]).total_seconds())
    if age_seconds < 0:
        result = _hold_result("EVALUATION_BEFORE_LAST_PACKET", duplicate_count)
        result["evidence"] = {
            "packet_count": len(normalized_packets),
            "unique_packet_count": len(unique_packets),
            "packet_ids": [p["packet_id"] for p in unique_packets],
            "age_seconds": age_seconds,
        }
        return result
    if age_seconds > int(policy["freshness_max_seconds"]):
        result = _hold_result("STALE_EVIDENCE", duplicate_count)
        result["evidence"] = {
            "packet_count": len(normalized_packets),
            "unique_packet_count": len(unique_packets),
            "packet_ids": [p["packet_id"] for p in unique_packets],
            "age_seconds": age_seconds,
        }
        return result

    first = unique_packets[0]
    last = unique_packets[-1]
    first_flow = float(first["flow_lps"])
    last_flow = float(last["flow_lps"])
    level_rise = float(last["level_pct"]) - float(first["level_pct"])
    max_rain = max(float(packet["rain_mm_15m"]) for packet in unique_packets)
    flow_drop_ratio = (first_flow - last_flow) / first_flow if first_flow > 0 else 0.0
    flow_rise_ratio = (last_flow - first_flow) / first_flow if first_flow > 0 else 0.0

    evidence = {
        "packet_count": len(normalized_packets),
        "unique_packet_count": len(unique_packets),
        "packet_ids": [packet["packet_id"] for packet in unique_packets],
        "first_observed_at": unique_packets[0]["observed_at"],
        "last_observed_at": unique_packets[-1]["observed_at"],
        "age_seconds": age_seconds,
        "max_gap_seconds": max_gap,
        "level_rise_pct": round(level_rise, 9),
        "flow_drop_ratio": round(flow_drop_ratio, 9),
        "flow_rise_ratio": round(flow_rise_ratio, 9),
        "max_rain_mm_15m": round(max_rain, 9),
        "evidence_sha256": sha256_hex(unique_packets),
    }

    blockage = (
        max_rain <= float(policy["blockage"]["max_rain_mm_15m"])
        and level_rise >= float(policy["blockage"]["min_level_rise_pct"])
        and flow_drop_ratio >= float(policy["blockage"]["min_flow_drop_ratio"])
    )
    storm_ii = (
        max_rain >= float(policy["storm_ii"]["min_rain_mm_15m"])
        and level_rise >= float(policy["storm_ii"]["min_level_rise_pct"])
        and flow_rise_ratio >= float(policy["storm_ii"]["min_flow_rise_ratio"])
    )

    if blockage:
        anomaly = "BLOCKAGE_SUSPECTED"
        intent = _make_work_intent(
            action="INSPECT_BLOCKAGE",
            anomaly_class=anomaly,
            scenario_id=scenario["scenario_id"],
            site_id=scenario["site_id"],
            unique_packets=unique_packets,
            model=model,
            policy=policy,
            policy_sha256=policy_sha256,
        )
        return {
            "decision": "WORK_INTENT",
            "anomaly_class": anomaly,
            "hold_reason": None,
            "work_intents": [intent],
            "duplicates_suppressed": duplicate_count,
            "evidence": evidence,
        }

    if storm_ii:
        anomaly = "I_AND_I_SUSPECTED"
        intent = _make_work_intent(
            action="INVESTIGATE_I_AND_I",
            anomaly_class=anomaly,
            scenario_id=scenario["scenario_id"],
            site_id=scenario["site_id"],
            unique_packets=unique_packets,
            model=model,
            policy=policy,
            policy_sha256=policy_sha256,
        )
        return {
            "decision": "WORK_INTENT",
            "anomaly_class": anomaly,
            "hold_reason": None,
            "work_intents": [intent],
            "duplicates_suppressed": duplicate_count,
            "evidence": evidence,
        }

    return {
        "decision": "NO_ACTION",
        "anomaly_class": "NONE",
        "hold_reason": None,
        "work_intents": [],
        "duplicates_suppressed": duplicate_count,
        "evidence": evidence,
    }


def _assertion(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> dict[str, Any]:
    actual_summary = {
        "decision": actual["decision"],
        "anomaly_class": actual["anomaly_class"],
        "work_intents": len(actual["work_intents"]),
        "hold_reason": actual["hold_reason"],
    }
    expected_summary = {
        "decision": expected["decision"],
        "anomaly_class": expected["anomaly_class"],
        "work_intents": expected["work_intents"],
        "hold_reason": expected["hold_reason"],
    }
    return {
        "passed": actual_summary == expected_summary,
        "expected": expected_summary,
        "actual": actual_summary,
    }


def evaluate_document(
    document: Any,
    policy: Any,
    *,
    evaluator_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate and evaluate one complete fixture document."""

    validated_policy = _validate_policy(policy)
    validated_document = _validate_document(document, validated_policy)
    policy_sha256 = sha256_hex(validated_policy)
    input_sha256 = sha256_hex(validated_document)
    if evaluator_sha256 is None:
        evaluator_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if _SHA256_RE.fullmatch(evaluator_sha256) is None:
        raise ValidationError("evaluator_sha256 must be a lowercase SHA-256 digest")

    results: list[dict[str, Any]] = []
    all_intent_ids: set[str] = set()
    duplicate_intent_ids: list[str] = []
    for scenario in validated_document["fixtures"]:
        evaluated = _evaluate_scenario(
            scenario,
            model=validated_document["model"],
            policy=validated_policy,
            policy_sha256=policy_sha256,
        )
        assertion = _assertion(evaluated, scenario["expected"])
        for intent in evaluated["work_intents"]:
            intent_id = intent["work_intent_id"]
            if intent_id in all_intent_ids:
                duplicate_intent_ids.append(intent_id)
            all_intent_ids.add(intent_id)
        results.append(
            {
                "scenario_id": scenario["scenario_id"],
                "site_id": scenario["site_id"],
                "claim": {
                    "expected": scenario["expected"],
                    "scope": "synthetic acceptance fixture",
                },
                "test": {
                    "policy_id": validated_policy["policy_id"],
                    "policy_sha256": policy_sha256,
                    "model_id": validated_document["model"]["model_id"],
                    "model_artifact_sha256": validated_document["model"]["artifact_sha256"],
                    "configuration_id": validated_document["model"]["configuration_id"],
                },
                "result": evaluated,
                "assertion": assertion,
            }
        )

    passed = sum(1 for item in results if item["assertion"]["passed"])
    total_intents = sum(len(item["result"]["work_intents"]) for item in results)
    duplicates_suppressed = sum(
        int(item["result"]["duplicates_suppressed"]) for item in results
    )
    status = "READY"
    hold_reasons: list[str] = []
    if passed != len(results):
        status = "HOLD"
        hold_reasons.append("FIXTURE_ASSERTION_FAILED")
    if duplicate_intent_ids:
        status = "HOLD"
        hold_reasons.append("DUPLICATE_WORK_INTENT_ID")

    receipt_identity = {
        "receipt_version": RECEIPT_VERSION,
        "opportunity_id": OPPORTUNITY_ID,
        "input_sha256": input_sha256,
        "policy_sha256": policy_sha256,
        "evaluator_sha256": evaluator_sha256,
    }
    return {
        "receipt_version": RECEIPT_VERSION,
        "receipt_id": "lacsd04254_" + sha256_hex(receipt_identity)[:32],
        "opportunity_id": OPPORTUNITY_ID,
        "status": status,
        "hold_reasons": sorted(set(hold_reasons)),
        "scope": {
            "fixture_class": "synthetic_or_customer_approved_deidentified",
            "external_execution": False,
            "operational_control": False,
            "prime_bid_status": "NOT_CLAIMED",
            "buyer_acceptance": "NOT_CLAIMED",
        },
        "lineage": {
            "input_sha256": input_sha256,
            "policy_id": validated_policy["policy_id"],
            "policy_sha256": policy_sha256,
            "evaluator_sha256": evaluator_sha256,
            "model": validated_document["model"],
        },
        "metrics": {
            "scenarios_total": len(results),
            "assertions_passed": passed,
            "assertions_failed": len(results) - passed,
            "work_intents_total": total_intents,
            "unique_work_intent_ids": len(all_intent_ids),
            "duplicate_work_intent_ids": len(duplicate_intent_ids),
            "duplicate_packets_suppressed": duplicates_suppressed,
        },
        "scenarios": results,
        "non_claims": [
            "No LACSD endorsement, engagement, award, acceptance, or buyer relationship.",
            "No Token Junkie Labs prime-bid or prequalification status.",
            "No production sewer telemetry, work-order, maintenance, or control-system access.",
            "No operational action is executed; work objects are deterministic intents only.",
            "No accuracy, savings, compliance, safety, or performance claim beyond these fixtures.",
        ],
    }


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def build_parser() -> argparse.ArgumentParser:
    package_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Evaluate the bounded LACSD 04254 synthetic evidence packet."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=package_dir / "fixtures.json",
        help="fixture document (default: packaged fixtures.json)",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=package_dir / "policy.json",
        help="policy document (default: packaged policy.json)",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="receipt path, or - for stdout (default: -)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        document = load_json(args.input)
        policy = load_json(args.policy)
        evaluator_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        receipt = evaluate_document(
            document, policy, evaluator_sha256=evaluator_sha256
        )
        text = canonical_text(receipt)
        if args.output == "-":
            sys.stdout.write(text)
        else:
            _write_atomic(Path(args.output), text)
        return 0 if receipt["status"] == "READY" else 1
    except ValidationError as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"HOLD: local I/O failure: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
