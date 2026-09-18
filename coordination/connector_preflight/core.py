"""Deterministic connector discovery and write-capability preflight.

The compiler consumes normalized evidence only. It never invokes a connector or
mutates a provider. Public SHA-256 values are integrity commitments, not
authentication or delegated authority.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INPUT_SCHEMA = "commons.connector-preflight/v1"
PACKET_SCHEMA = "commons.connector-preflight-packet/v1"
BUNDLE_SCHEMA = "commons.connector-preflight-bundle/v1"
RECEIPT_SCHEMA = "commons.connector-preflight-receipt/v1"
CONNECTORS = ("GitHub", "Slack")
ACCESS = {"READ", "WRITE"}
RESULTS = {
    "SUCCESS",
    "UNAVAILABLE",
    "AUTH_REQUIRED",
    "RATE_LIMITED",
    "REJECTED",
    "ERROR",
    "OUTCOME_UNKNOWN",
}
CLAIMS = {"CAPABILITY_REPORT", "NO_WRITE_RAIL"}
MODES = {"CURRENT", "HISTORICAL_INTEGRITY_ONLY"}
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]{2,95}$")
ACTION_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{1,127}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ACTIONS = 512
MAX_ATTEMPTS = 512
MAX_DISCOVERIES = 32
MAX_AGE_SECONDS = 7 * 24 * 3600


class PreflightError(ValueError):
    """Stable public error boundary for malformed or unsafe evidence."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_text(canonical_json(value))


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise PreflightError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value: str) -> None:
    raise PreflightError(f"non-finite JSON number: {value}")


def strict_loads(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
    except PreflightError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise PreflightError(f"invalid JSON: {exc}") from exc


def _detach(value: Any, path: str = "$", depth: int = 0) -> Any:
    if depth > 64:
        raise PreflightError(f"{path}: nesting exceeds 64")
    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is float:
        if value != value or value in (float("inf"), float("-inf")):
            raise PreflightError(f"{path}: non-finite number")
        return value
    if type(value) is list:
        return [_detach(item, f"{path}[{index}]", depth + 1) for index, item in enumerate(value)]
    if type(value) is dict:
        out: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise PreflightError(f"{path}: object key must be string")
            if key in out:
                raise PreflightError(f"{path}: duplicate key {key}")
            out[key] = _detach(item, f"{path}.{key}", depth + 1)
        return out
    raise PreflightError(f"{path}: unsupported runtime type {type(value).__name__}")


def _exact_keys(value: Any, expected: set[str], path: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise PreflightError(f"{path}: expected object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise PreflightError(f"{path}: key mismatch missing={missing} extra={extra}")
    return value


def _bounded_text(value: Any, path: str, *, pattern: re.Pattern[str] | None = None, max_len: int = 128) -> str:
    if type(value) is not str:
        raise PreflightError(f"{path}: expected string")
    if not value or len(value) > max_len:
        raise PreflightError(f"{path}: length must be 1..{max_len}")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise PreflightError(f"{path}: control character rejected")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise PreflightError(f"{path}: invalid format")
    return value


def _safe_int(value: Any, path: str, minimum: int, maximum: int) -> int:
    if type(value) is not int:
        raise PreflightError(f"{path}: expected integer")
    if value < minimum or value > maximum:
        raise PreflightError(f"{path}: expected {minimum}..{maximum}")
    return value


def _bool(value: Any, path: str) -> bool:
    if type(value) is not bool:
        raise PreflightError(f"{path}: expected boolean")
    return value


def _sha(value: Any, path: str) -> str:
    return _bounded_text(value, path, pattern=SHA_RE, max_len=64)


def parse_utc(value: Any, path: str = "timestamp") -> datetime:
    text = _bounded_text(value, path, max_len=32)
    if UTC_RE.fullmatch(text) is None:
        raise PreflightError(f"{path}: expected canonical whole-second UTC")
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise PreflightError(f"{path}: invalid UTC timestamp") from exc
    return parsed


def format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise PreflightError("evaluation time must be timezone-aware")
    value = value.astimezone(timezone.utc).replace(microsecond=0)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _normalize_policy(raw: Any) -> dict[str, Any]:
    obj = _exact_keys(raw, {"max_age_seconds", "required_actions"}, "$.policy")
    max_age = _safe_int(obj["max_age_seconds"], "$.policy.max_age_seconds", 1, MAX_AGE_SECONDS)
    actions_obj = _exact_keys(obj["required_actions"], set(CONNECTORS), "$.policy.required_actions")
    required: dict[str, list[str]] = {}
    for connector in CONNECTORS:
        rows = actions_obj[connector]
        if type(rows) is not list or not rows or len(rows) > 32:
            raise PreflightError(f"$.policy.required_actions.{connector}: expected 1..32 actions")
        seen: set[str] = set()
        normalized: list[str] = []
        for index, row in enumerate(rows):
            name = _bounded_text(row, f"$.policy.required_actions.{connector}[{index}]", pattern=ACTION_RE)
            if name in seen:
                raise PreflightError(f"$.policy.required_actions.{connector}: duplicate action {name}")
            seen.add(name)
            normalized.append(name)
        required[connector] = sorted(normalized)
    return {"max_age_seconds": max_age, "required_actions": required}


def _normalize_action(raw: Any, path: str, paths: set[str]) -> dict[str, str]:
    obj = _exact_keys(raw, {"connector", "name", "access"}, path)
    connector = _bounded_text(obj["connector"], f"{path}.connector", max_len=16)
    if connector not in CONNECTORS:
        raise PreflightError(f"{path}.connector: unsupported connector")
    if connector not in paths:
        raise PreflightError(f"{path}.connector: action connector not requested")
    name = _bounded_text(obj["name"], f"{path}.name", pattern=ACTION_RE)
    access = _bounded_text(obj["access"], f"{path}.access", max_len=8)
    if access not in ACCESS:
        raise PreflightError(f"{path}.access: expected READ or WRITE")
    return {"connector": connector, "name": name, "access": access}


def _normalize_discovery(raw: Any, index: int, captured: datetime) -> dict[str, Any]:
    path = f"$.discoveries[{index}]"
    obj = _exact_keys(
        raw,
        {"request_id", "requested_at", "completed_at", "paths", "query", "complete", "actions", "evidence_sha256"},
        path,
    )
    request_id = _bounded_text(obj["request_id"], f"{path}.request_id", pattern=ID_RE, max_len=96)
    requested_text = _bounded_text(obj["requested_at"], f"{path}.requested_at", max_len=32)
    completed_text = _bounded_text(obj["completed_at"], f"{path}.completed_at", max_len=32)
    requested = parse_utc(requested_text, f"{path}.requested_at")
    completed = parse_utc(completed_text, f"{path}.completed_at")
    if completed < requested:
        raise PreflightError(f"{path}: completion precedes request")
    if completed > captured:
        raise PreflightError(f"{path}: completion after snapshot capture")
    raw_paths = obj["paths"]
    if type(raw_paths) is not list or not raw_paths or len(raw_paths) > len(CONNECTORS):
        raise PreflightError(f"{path}.paths: expected 1..{len(CONNECTORS)} connectors")
    seen_paths: set[str] = set()
    for pindex, item in enumerate(raw_paths):
        connector = _bounded_text(item, f"{path}.paths[{pindex}]", max_len=16)
        if connector not in CONNECTORS:
            raise PreflightError(f"{path}.paths[{pindex}]: unsupported connector")
        if connector in seen_paths:
            raise PreflightError(f"{path}.paths: duplicate connector {connector}")
        seen_paths.add(connector)
    query = obj["query"]
    if query is not None:
        query = _bounded_text(query, f"{path}.query", max_len=128)
    complete = _bool(obj["complete"], f"{path}.complete")
    raw_actions = obj["actions"]
    if type(raw_actions) is not list or len(raw_actions) > MAX_ACTIONS:
        raise PreflightError(f"{path}.actions: expected list up to {MAX_ACTIONS}")
    actions: list[dict[str, str]] = []
    identities: set[tuple[str, str]] = set()
    for aindex, row in enumerate(raw_actions):
        action = _normalize_action(row, f"{path}.actions[{aindex}]", seen_paths)
        identity = (action["connector"], action["name"])
        if identity in identities:
            raise PreflightError(f"{path}.actions: duplicate action identity {identity}")
        identities.add(identity)
        actions.append(action)
    evidence = _sha(obj["evidence_sha256"], f"{path}.evidence_sha256")
    ordered_paths = [connector for connector in CONNECTORS if connector in seen_paths]
    return {
        "request_id": request_id,
        "requested_at": requested_text,
        "completed_at": completed_text,
        "paths": ordered_paths,
        "query": query,
        "complete": complete,
        "actions": sorted(actions, key=lambda row: (row["connector"], row["name"], row["access"])),
        "evidence_sha256": evidence,
    }


def _normalize_attempt(raw: Any, index: int, captured: datetime) -> dict[str, Any]:
    path = f"$.attempts[{index}]"
    obj = _exact_keys(
        raw,
        {
            "attempt_id",
            "operation_id",
            "discovery_request_id",
            "connector",
            "action",
            "access",
            "attempted_at",
            "result",
            "error_code",
            "evidence_sha256",
        },
        path,
    )
    attempt_id = _bounded_text(obj["attempt_id"], f"{path}.attempt_id", pattern=ID_RE, max_len=96)
    operation_id = _bounded_text(obj["operation_id"], f"{path}.operation_id", pattern=ID_RE, max_len=96)
    discovery_id = _bounded_text(obj["discovery_request_id"], f"{path}.discovery_request_id", pattern=ID_RE, max_len=96)
    connector = _bounded_text(obj["connector"], f"{path}.connector", max_len=16)
    if connector not in CONNECTORS:
        raise PreflightError(f"{path}.connector: unsupported connector")
    action = _bounded_text(obj["action"], f"{path}.action", pattern=ACTION_RE)
    access = _bounded_text(obj["access"], f"{path}.access", max_len=8)
    if access not in ACCESS:
        raise PreflightError(f"{path}.access: expected READ or WRITE")
    attempted_text = _bounded_text(obj["attempted_at"], f"{path}.attempted_at", max_len=32)
    attempted = parse_utc(attempted_text, f"{path}.attempted_at")
    if attempted > captured:
        raise PreflightError(f"{path}: attempt after snapshot capture")
    result = _bounded_text(obj["result"], f"{path}.result", max_len=32)
    if result not in RESULTS:
        raise PreflightError(f"{path}.result: unsupported result")
    error_code = obj["error_code"]
    if error_code is not None:
        error_code = _bounded_text(error_code, f"{path}.error_code", max_len=96)
    evidence = _sha(obj["evidence_sha256"], f"{path}.evidence_sha256")
    return {
        "attempt_id": attempt_id,
        "operation_id": operation_id,
        "discovery_request_id": discovery_id,
        "connector": connector,
        "action": action,
        "access": access,
        "attempted_at": attempted_text,
        "result": result,
        "error_code": error_code,
        "evidence_sha256": evidence,
    }


def normalize_input(raw: Any, evaluated_at: datetime) -> dict[str, Any]:
    doc = _detach(raw)
    obj = _exact_keys(doc, {"schema", "snapshot_id", "claim", "captured_at", "policy", "discoveries", "attempts"}, "$")
    if obj["schema"] != INPUT_SCHEMA:
        raise PreflightError(f"$.schema: expected {INPUT_SCHEMA}")
    snapshot_id = _bounded_text(obj["snapshot_id"], "$.snapshot_id", pattern=ID_RE, max_len=96)
    claim = _bounded_text(obj["claim"], "$.claim", max_len=32)
    if claim not in CLAIMS:
        raise PreflightError("$.claim: unsupported claim")
    captured_text = _bounded_text(obj["captured_at"], "$.captured_at", max_len=32)
    captured = parse_utc(captured_text, "$.captured_at")
    evaluated = evaluated_at.astimezone(timezone.utc).replace(microsecond=0)
    if captured > evaluated:
        raise PreflightError("$.captured_at: snapshot is from the future")
    policy = _normalize_policy(obj["policy"])
    age = int((evaluated - captured).total_seconds())
    if age > policy["max_age_seconds"]:
        raise PreflightError("$.captured_at: snapshot is stale")
    raw_discoveries = obj["discoveries"]
    if type(raw_discoveries) is not list or len(raw_discoveries) > MAX_DISCOVERIES:
        raise PreflightError(f"$.discoveries: expected list up to {MAX_DISCOVERIES}")
    discoveries: list[dict[str, Any]] = []
    request_ids: set[str] = set()
    for index, row in enumerate(raw_discoveries):
        discovery = _normalize_discovery(row, index, captured)
        if discovery["request_id"] in request_ids:
            raise PreflightError(f"$.discoveries: duplicate request_id {discovery['request_id']}")
        request_ids.add(discovery["request_id"])
        discoveries.append(discovery)
    raw_attempts = obj["attempts"]
    if type(raw_attempts) is not list or len(raw_attempts) > MAX_ATTEMPTS:
        raise PreflightError(f"$.attempts: expected list up to {MAX_ATTEMPTS}")
    attempts: list[dict[str, Any]] = []
    attempt_ids: set[str] = set()
    operation_ids: set[str] = set()
    for index, row in enumerate(raw_attempts):
        attempt = _normalize_attempt(row, index, captured)
        if attempt["attempt_id"] in attempt_ids:
            raise PreflightError(f"$.attempts: duplicate attempt_id {attempt['attempt_id']}")
        if attempt["operation_id"] in operation_ids:
            raise PreflightError(f"$.attempts: duplicate operation_id {attempt['operation_id']}")
        attempt_ids.add(attempt["attempt_id"])
        operation_ids.add(attempt["operation_id"])
        attempts.append(attempt)
    return {
        "schema": INPUT_SCHEMA,
        "snapshot_id": snapshot_id,
        "claim": claim,
        "captured_at": captured_text,
        "policy": policy,
        "discoveries": sorted(discoveries, key=lambda row: row["request_id"]),
        "attempts": sorted(attempts, key=lambda row: (row["attempted_at"], row["attempt_id"])),
    }


def _latest_attempts(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        previous = latest.get(row["action"])
        if previous is None or (row["attempted_at"], row["attempt_id"]) > (previous["attempted_at"], previous["attempt_id"]):
            latest[row["action"]] = row
    return latest


def _semantic_projection(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_sha256": packet["source_sha256"],
        "claim": packet["claim"],
        "connectors": packet["connectors"],
        "overall_state": packet["overall_state"],
        "work_blocked_claim_supported": packet["work_blocked_claim_supported"],
        "reasons": packet["reasons"],
        "authority": packet["authority"],
    }


def evaluate(normalized: dict[str, Any], evaluated_at: datetime, mode: str) -> dict[str, Any]:
    if mode not in MODES:
        raise PreflightError("unsupported evaluation mode")
    evaluated_text = format_utc(evaluated_at)
    all_connectors = set(CONNECTORS)
    qualified = [
        row
        for row in normalized["discoveries"]
        if row["complete"] and row["query"] is None and set(row["paths"]) == all_connectors
    ]
    discovery_by_id = {row["request_id"]: row for row in normalized["discoveries"]}
    semantic_hold: list[str] = []
    identity_access: dict[tuple[str, str], str] = {}
    for row in normalized["discoveries"]:
        for action in row["actions"]:
            identity = (action["connector"], action["name"])
            previous = identity_access.get(identity)
            if previous is not None and previous != action["access"]:
                semantic_hold.append(f"ACTION_ACCESS_CONFLICT_{action['connector']}_{action['name']}")
            identity_access[identity] = action["access"]
    for attempt in normalized["attempts"]:
        discovery = discovery_by_id.get(attempt["discovery_request_id"])
        if discovery is None:
            semantic_hold.append(f"ATTEMPT_DISCOVERY_MISSING_{attempt['attempt_id']}")
            continue
        if parse_utc(attempt["attempted_at"]) < parse_utc(discovery["completed_at"]):
            semantic_hold.append(f"ATTEMPT_BEFORE_DISCOVERY_{attempt['attempt_id']}")
        matching = [
            action
            for action in discovery["actions"]
            if action["connector"] == attempt["connector"] and action["name"] == attempt["action"]
        ]
        if not matching:
            semantic_hold.append(f"ATTEMPT_ACTION_UNDISCOVERED_{attempt['attempt_id']}")
        elif matching[0]["access"] != attempt["access"]:
            semantic_hold.append(f"ATTEMPT_ACCESS_MISMATCH_{attempt['attempt_id']}")
    connector_rows: list[dict[str, Any]] = []
    connector_blockers: dict[str, bool] = {}
    for connector in CONNECTORS:
        reasons: list[str] = []
        required = normalized["policy"]["required_actions"][connector]
        if not qualified:
            state = "NOT_DISCOVERED"
            exposed: list[str] = []
            blocker = False
            reasons.append("COMPLETE_UNFILTERED_GITHUB_SLACK_DISCOVERY_MISSING")
        else:
            catalog = {
                action["name"]
                for discovery in qualified
                for action in discovery["actions"]
                if action["connector"] == connector and action["access"] == "WRITE"
            }
            exposed = sorted(set(required) & catalog)
            if not exposed:
                state = "DISCOVERED_READ_ONLY"
                blocker = normalized["claim"] == "NO_WRITE_RAIL"
                reasons.append("REQUIRED_WRITE_ACTIONS_NOT_EXPOSED")
            else:
                relevant = [
                    attempt
                    for attempt in normalized["attempts"]
                    if attempt["connector"] == connector
                    and attempt["access"] == "WRITE"
                    and attempt["action"] in exposed
                    and attempt["discovery_request_id"] in {row["request_id"] for row in qualified}
                ]
                latest = _latest_attempts(relevant)
                if any(row["result"] == "SUCCESS" for row in relevant):
                    state = "WRITE_RAIL_CONFIRMED"
                    blocker = False
                    reasons.append("WRITE_ACTION_SUCCEEDED")
                elif not relevant:
                    state = "WRITE_ATTEMPT_REQUIRED" if normalized["claim"] == "NO_WRITE_RAIL" else "WRITE_ACTIONS_EXPOSED"
                    blocker = False
                    reasons.append("RELEVANT_WRITE_ATTEMPT_MISSING")
                else:
                    state = "WRITE_ATTEMPT_FAILED"
                    unavailable = all(action in latest and latest[action]["result"] == "UNAVAILABLE" for action in exposed)
                    blocker = normalized["claim"] == "NO_WRITE_RAIL" and unavailable
                    if unavailable:
                        reasons.append("ALL_EXPOSED_REQUIRED_WRITE_ACTIONS_UNAVAILABLE")
                    else:
                        reasons.append("WRITE_FAILURE_DOES_NOT_PROVE_RAIL_ABSENCE")
        read_failures = [
            attempt
            for attempt in normalized["attempts"]
            if attempt["connector"] == connector and attempt["access"] == "READ" and attempt["result"] != "SUCCESS"
        ]
        if read_failures:
            reasons.append("READ_FAILURE_DOES_NOT_PROVE_WRITE_ABSENCE")
        connector_blockers[connector] = blocker
        connector_rows.append(
            {
                "connector": connector,
                "state": state,
                "required_write_actions": required,
                "exposed_required_write_actions": exposed,
                "blocker_supported": blocker,
                "reasons": sorted(set(reasons)),
            }
        )
    if semantic_hold:
        overall_state = "HOLD"
        work_blocked = False
        overall_reasons = sorted(set(semantic_hold))
    elif normalized["claim"] == "NO_WRITE_RAIL" and all(connector_blockers.values()):
        overall_state = "BLOCKER_SUPPORTED"
        work_blocked = True
        overall_reasons = ["COMPLETE_EVIDENCE_SUPPORTS_NO_WRITE_RAIL"]
    elif all(row["state"] == "WRITE_RAIL_CONFIRMED" for row in connector_rows):
        overall_state = "WRITE_RAIL_CONFIRMED"
        work_blocked = False
        overall_reasons = ["GITHUB_AND_SLACK_WRITE_RAILS_CONFIRMED"]
    elif any(row["state"] == "WRITE_ATTEMPT_REQUIRED" for row in connector_rows):
        overall_state = "WRITE_ATTEMPT_REQUIRED"
        work_blocked = False
        overall_reasons = ["NO_WRITE_RAIL_CLAIM_REQUIRES_RELEVANT_WRITE_ATTEMPTS"]
    elif any(row["state"] in {"WRITE_ACTIONS_EXPOSED", "WRITE_ATTEMPT_FAILED", "WRITE_RAIL_CONFIRMED"} for row in connector_rows):
        overall_state = "WRITE_ACTIONS_EXPOSED"
        work_blocked = False
        overall_reasons = ["WRITE_CAPABILITY_PRESENT_OR_NOT_DISPROVEN"]
    elif any(row["state"] == "NOT_DISCOVERED" for row in connector_rows):
        overall_state = "NOT_DISCOVERED"
        work_blocked = False
        overall_reasons = ["COMPLETE_DISCOVERY_REQUIRED"]
    else:
        overall_state = "DISCOVERED_READ_ONLY"
        work_blocked = normalized["claim"] == "NO_WRITE_RAIL" and all(connector_blockers.values())
        overall_reasons = ["REQUIRED_WRITE_ACTIONS_NOT_EXPOSED"]
    packet = {
        "schema": PACKET_SCHEMA,
        "snapshot_id": normalized["snapshot_id"],
        "claim": normalized["claim"],
        "evaluation_mode": mode,
        "evaluated_at": evaluated_text,
        "captured_at": normalized["captured_at"],
        "snapshot_age_seconds": int((evaluated_at - parse_utc(normalized["captured_at"])).total_seconds()),
        "source_sha256": sha256_json(normalized),
        "connectors": connector_rows,
        "overall_state": overall_state,
        "work_blocked_claim_supported": work_blocked,
        "reasons": sorted(set(overall_reasons)),
        "authority": {
            "provider_mutation_authorized": False,
            "repository_mutation_authorized": False,
            "external_send_authorized": False,
            "customer_contact_authorized": False,
            "payment_mutation_authorized": False,
            "submission_authorized": False,
            "revenue_claimed": False,
        },
    }
    return packet


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# Connector capability preflight",
        "",
        f"- Snapshot: `{packet['snapshot_id']}`",
        f"- Claim: `{packet['claim']}`",
        f"- Evaluation: `{packet['evaluation_mode']}` at `{packet['evaluated_at']}`",
        f"- Overall: **{packet['overall_state']}**",
        f"- Work-blocked claim supported: **{str(packet['work_blocked_claim_supported']).lower()}**",
        "",
        "| Connector | State | Required writes | Exposed required writes | Blocker supported |",
        "|---|---|---|---|---|",
    ]
    for row in packet["connectors"]:
        required = ", ".join(f"`{item}`" for item in row["required_write_actions"])
        exposed = ", ".join(f"`{item}`" for item in row["exposed_required_write_actions"]) or "—"
        lines.append(
            f"| {row['connector']} | `{row['state']}` | {required} | {exposed} | "
            f"{str(row['blocker_supported']).lower()} |"
        )
    lines.extend(["", "## Reasons"])
    for reason in packet["reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(
        [
            "",
            "## Authority ceiling",
            "",
            "This receipt is internal coordination evidence. It performs no connector call and grants no provider, repository, customer, payment, submission, or revenue authority.",
            "",
        ]
    )
    return "\n".join(lines)


def compile_at(raw: Any, evaluated_at: datetime, *, mode: str = "HISTORICAL_INTEGRITY_ONLY") -> dict[str, Any]:
    evaluated = evaluated_at.astimezone(timezone.utc).replace(microsecond=0)
    normalized = normalize_input(raw, evaluated)
    packet = evaluate(normalized, evaluated, mode)
    markdown = render_markdown(packet)
    packet_digest = sha256_json(packet)
    markdown_digest = sha256_text(markdown)
    receipt_core = {
        "schema": RECEIPT_SCHEMA,
        "source_sha256": packet["source_sha256"],
        "packet_sha256": packet_digest,
        "markdown_sha256": markdown_digest,
        "snapshot_id": packet["snapshot_id"],
        "evaluated_at": packet["evaluated_at"],
        "overall_state": packet["overall_state"],
    }
    receipt = {**receipt_core, "receipt_sha256": sha256_json(receipt_core)}
    return {
        "schema": BUNDLE_SCHEMA,
        "packet": packet,
        "markdown": markdown,
        "packet_sha256": packet_digest,
        "markdown_sha256": markdown_digest,
        "receipt": receipt,
    }


def _compile_current_at(raw: Any, evaluated_at: datetime) -> dict[str, Any]:
    return compile_at(raw, evaluated_at, mode="CURRENT")


def compile_current(raw: Any) -> dict[str, Any]:
    """Compile current capability truth using process-owned UTC only."""
    return _compile_current_at(raw, utc_now())


def _validate_bundle_shape(bundle: Any) -> dict[str, Any]:
    detached = _detach(bundle)
    obj = _exact_keys(detached, {"schema", "packet", "markdown", "packet_sha256", "markdown_sha256", "receipt"}, "$bundle")
    if obj["schema"] != BUNDLE_SCHEMA:
        raise PreflightError("$bundle.schema: unexpected schema")
    if type(obj["markdown"]) is not str:
        raise PreflightError("$bundle.markdown: expected string")
    _sha(obj["packet_sha256"], "$bundle.packet_sha256")
    _sha(obj["markdown_sha256"], "$bundle.markdown_sha256")
    receipt = _exact_keys(
        obj["receipt"],
        {"schema", "source_sha256", "packet_sha256", "markdown_sha256", "snapshot_id", "evaluated_at", "overall_state", "receipt_sha256"},
        "$bundle.receipt",
    )
    if receipt["schema"] != RECEIPT_SCHEMA:
        raise PreflightError("$bundle.receipt.schema: unexpected schema")
    for key in ("source_sha256", "packet_sha256", "markdown_sha256", "receipt_sha256"):
        _sha(receipt[key], f"$bundle.receipt.{key}")
    parse_utc(receipt["evaluated_at"], "$bundle.receipt.evaluated_at")
    return obj


def verify_integrity(raw: Any, bundle: Any) -> bool:
    try:
        supplied = _validate_bundle_shape(bundle)
        packet = supplied["packet"]
        if type(packet) is not dict:
            return False
        evaluated = parse_utc(packet.get("evaluated_at"), "$bundle.packet.evaluated_at")
        mode = packet.get("evaluation_mode")
        if mode not in MODES:
            return False
        rebuilt = compile_at(raw, evaluated, mode=mode)
        return canonical_json(rebuilt) == canonical_json(supplied)
    except (PreflightError, KeyError, TypeError, ValueError, RecursionError):
        return False


def _verify_current_at(raw: Any, bundle: Any, evaluated_at: datetime) -> dict[str, Any]:
    integrity = verify_integrity(raw, bundle)
    evaluated = evaluated_at.astimezone(timezone.utc).replace(microsecond=0)
    result: dict[str, Any] = {
        "schema": "commons.connector-preflight-verification/v1",
        "integrity_valid": integrity,
        "current_valid": False,
        "evaluated_at": format_utc(evaluated),
        "current_state": "INVALID",
        "reasons": [],
    }
    if not integrity:
        result["reasons"] = ["BUNDLE_INTEGRITY_INVALID"]
        return result
    try:
        current_bundle = _compile_current_at(raw, evaluated)
    except PreflightError as exc:
        result["current_state"] = "STALE_OR_INVALID"
        result["reasons"] = [str(exc)]
        return result
    original_packet = _validate_bundle_shape(bundle)["packet"]
    current_packet = current_bundle["packet"]
    current = _semantic_projection(original_packet) == _semantic_projection(current_packet)
    result["current_valid"] = current
    result["current_state"] = current_packet["overall_state"]
    result["reasons"] = [] if current else ["CURRENT_SEMANTICS_DRIFTED"]
    return result


def verify_current(raw: Any, bundle: Any) -> dict[str, Any]:
    """Verify current capability truth using process-owned UTC only."""
    return _verify_current_at(raw, bundle, utc_now())


def read_json_file(path: Path, *, max_bytes: int = MAX_FILE_BYTES) -> Any:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise PreflightError(f"cannot open input: {exc}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise PreflightError("input must be a regular file")
        if info.st_size > max_bytes:
            raise PreflightError("input exceeds size limit")
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            part = os.read(fd, min(65536, remaining))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        data = b"".join(chunks)
        if len(data) > max_bytes:
            raise PreflightError("input grew beyond size limit")
    finally:
        os.close(fd)
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise PreflightError("input is not strict UTF-8") from exc
    return strict_loads(text)


def write_json_exclusive(path: Path, value: Any) -> None:
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise PreflightError(f"cannot create output exclusively: {exc}") from exc
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise PreflightError("short output write")
            view = view[written:]
        os.fsync(fd)
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    finally:
        os.close(fd)
