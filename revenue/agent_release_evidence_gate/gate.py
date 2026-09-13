#!/usr/bin/env python3
"""Deterministic pre-effect admission gate for agent tool operations.

The gate does not execute tools or grant credentials.  It consumes a manifest assembled
from authoritative control-plane evidence and returns HOLD/RELEASE plus a
content-addressed receipt.  Freshness is always measured against a trusted evaluation
time supplied by the caller of :func:`evaluate` (the CLI uses the system UTC clock),
never against a caller-selected "current" timestamp inside the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

VERSION = 1
EFFECTS = {"read", "write", "external"}
PASS = "pass"


class GateInputError(ValueError):
    """Raised for structurally malformed manifests, never for policy HOLDs."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise GateInputError(f"{field} must be a non-empty RFC3339 timestamp")
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise GateInputError(f"{field} must be RFC3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GateInputError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GateInputError(f"{field} must be an object")
    return value


def _require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise GateInputError(f"{field} must be an array")
    return value


def _positive_int(value: Any, field: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GateInputError(f"{field} must be an integer")
    floor = 0 if allow_zero else 1
    if value < floor:
        relation = ">= 0" if allow_zero else "> 0"
        raise GateInputError(f"{field} must be {relation}")
    return value


def _request_fingerprint(request: dict[str, Any]) -> str:
    return sha256_json(request)


def _normalize_evaluated_at(evaluated_at: datetime) -> datetime:
    if not isinstance(evaluated_at, datetime) or evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise GateInputError("evaluated_at must be a timezone-aware datetime")
    return evaluated_at.astimezone(timezone.utc)


def _capability_allows(capabilities: list[Any], request: dict[str, Any]) -> bool:
    for index, raw in enumerate(capabilities):
        capability = _require_dict(raw, f"policy.capabilities[{index}]")
        required = {"tool", "operation", "effect", "target_prefix"}
        if not required.issubset(capability):
            raise GateInputError(f"policy.capabilities[{index}] is missing required fields")
        if not all(isinstance(capability[key], str) for key in required):
            raise GateInputError(f"policy.capabilities[{index}] fields must be strings")
        if (
            capability["tool"] == request["tool"]
            and capability["operation"] == request["operation"]
            and capability["effect"] == request["effect"]
            and request["target"].startswith(capability["target_prefix"])
        ):
            return True
    return False


def _decision_expiry(
    evaluated_at: datetime,
    policy: dict[str, Any],
    snapshot_at: datetime,
    evidence_times: Iterable[datetime],
    approval_expires_at: datetime | None,
) -> datetime:
    candidates = [evaluated_at + timedelta(seconds=policy["decision_ttl_seconds"])]
    candidates.append(snapshot_at + timedelta(seconds=policy["max_snapshot_age_seconds"]))
    for observed_at in evidence_times:
        candidates.append(observed_at + timedelta(seconds=policy["max_check_age_seconds"]))
    if approval_expires_at is not None:
        candidates.append(approval_expires_at)
    return min(candidates)


def evaluate(manifest: dict[str, Any], evaluated_at: datetime) -> dict[str, Any]:
    """Evaluate one request against a fail-closed release policy.

    ``evaluated_at`` must come from a trusted execution clock.  It is deliberately not
    read from the manifest.  Policy violations return ``HOLD`` with stable reason
    codes.  Structural/schema defects raise :class:`GateInputError` and therefore
    cannot accidentally become a RELEASE.
    """

    evaluated_at = _normalize_evaluated_at(evaluated_at)
    manifest = _require_dict(manifest, "manifest")
    if manifest.get("version") != VERSION:
        raise GateInputError(f"manifest.version must equal {VERSION}")
    for key in ("run_id", "agent_id", "snapshot_at", "request", "policy", "evidence"):
        if key not in manifest:
            raise GateInputError(f"manifest missing {key}")
    if not isinstance(manifest["run_id"], str) or not manifest["run_id"]:
        raise GateInputError("run_id must be a non-empty string")
    if not isinstance(manifest["agent_id"], str) or not manifest["agent_id"]:
        raise GateInputError("agent_id must be a non-empty string")

    request = _require_dict(manifest["request"], "request")
    for key in ("tool", "operation", "effect", "target", "payload", "payload_sha256"):
        if key not in request:
            raise GateInputError(f"request missing {key}")
    for key in ("tool", "operation", "effect", "target", "payload_sha256"):
        if not isinstance(request[key], str) or not request[key]:
            raise GateInputError(f"request.{key} must be a non-empty string")
    if request["effect"] not in EFFECTS:
        raise GateInputError(f"request.effect must be one of {sorted(EFFECTS)}")
    if not isinstance(request["payload"], (dict, list)):
        raise GateInputError("request.payload must be an object or array")

    policy = _require_dict(manifest["policy"], "policy")
    for key in (
        "capabilities",
        "required_checks",
        "approval_required_effects",
        "approvers",
        "effect_budget",
        "max_snapshot_age_seconds",
        "max_future_skew_seconds",
        "max_check_age_seconds",
        "decision_ttl_seconds",
    ):
        if key not in policy:
            raise GateInputError(f"policy missing {key}")
    capabilities = _require_list(policy["capabilities"], "policy.capabilities")
    required_checks = _require_list(policy["required_checks"], "policy.required_checks")
    approval_required_effects = _require_list(
        policy["approval_required_effects"], "policy.approval_required_effects"
    )
    approvers = _require_list(policy["approvers"], "policy.approvers")
    effect_budget = _require_dict(policy["effect_budget"], "policy.effect_budget")
    policy["max_snapshot_age_seconds"] = _positive_int(
        policy["max_snapshot_age_seconds"], "policy.max_snapshot_age_seconds"
    )
    policy["max_future_skew_seconds"] = _positive_int(
        policy["max_future_skew_seconds"], "policy.max_future_skew_seconds", allow_zero=True
    )
    policy["max_check_age_seconds"] = _positive_int(
        policy["max_check_age_seconds"], "policy.max_check_age_seconds"
    )
    policy["decision_ttl_seconds"] = _positive_int(
        policy["decision_ttl_seconds"], "policy.decision_ttl_seconds"
    )
    if any(not isinstance(name, str) or not name for name in required_checks):
        raise GateInputError("policy.required_checks entries must be non-empty strings")
    if len(set(required_checks)) != len(required_checks):
        raise GateInputError("policy.required_checks must not contain duplicates")
    if any(effect not in EFFECTS for effect in approval_required_effects):
        raise GateInputError("policy.approval_required_effects contains an unknown effect")
    if any(not isinstance(actor, str) or not actor for actor in approvers):
        raise GateInputError("policy.approvers entries must be non-empty strings")
    for effect in EFFECTS:
        if effect not in effect_budget:
            raise GateInputError(f"policy.effect_budget missing {effect}")
        effect_budget[effect] = _positive_int(
            effect_budget[effect], f"policy.effect_budget.{effect}", allow_zero=True
        )

    evidence = _require_dict(manifest["evidence"], "evidence")
    checks = _require_dict(evidence.get("checks"), "evidence.checks")
    completed_effects = _require_list(evidence.get("completed_effects"), "evidence.completed_effects")

    snapshot_at = _parse_time(manifest["snapshot_at"], "snapshot_at")
    request_sha = _request_fingerprint(request)
    reasons: list[str] = []

    payload_sha = sha256_json(request["payload"])
    if payload_sha != request["payload_sha256"]:
        reasons.append("PAYLOAD_HASH_MISMATCH")

    max_future_skew = timedelta(seconds=policy["max_future_skew_seconds"])
    snapshot_age = evaluated_at - snapshot_at
    if snapshot_at - evaluated_at > max_future_skew:
        reasons.append("SNAPSHOT_FROM_FUTURE")
    elif snapshot_age > timedelta(seconds=policy["max_snapshot_age_seconds"]):
        reasons.append("STALE_SNAPSHOT")

    if not _capability_allows(capabilities, request):
        reasons.append("CAPABILITY_NOT_ALLOWED")

    evidence_times: list[datetime] = []
    for check_name in required_checks:
        raw = checks.get(check_name)
        if raw is None:
            reasons.append(f"CHECK_MISSING:{check_name}")
            continue
        check = _require_dict(raw, f"evidence.checks.{check_name}")
        status = check.get("status")
        if status != PASS:
            reasons.append(f"CHECK_NOT_PASS:{check_name}")
        if check.get("subject_sha256") != request_sha:
            reasons.append(f"CHECK_SUBJECT_MISMATCH:{check_name}")
        observed_at = _parse_time(check.get("observed_at"), f"evidence.checks.{check_name}.observed_at")
        evidence_times.append(observed_at)
        if observed_at - evaluated_at > max_future_skew:
            reasons.append(f"CHECK_FROM_FUTURE:{check_name}")
        elif evaluated_at - observed_at > timedelta(seconds=policy["max_check_age_seconds"]):
            reasons.append(f"CHECK_STALE:{check_name}")

    completed_for_effect = 0
    seen_effect_ids: set[str] = set()
    for index, raw in enumerate(completed_effects):
        item = _require_dict(raw, f"evidence.completed_effects[{index}]")
        for field in ("effect_id", "effect", "request_sha256", "status"):
            if not isinstance(item.get(field), str) or not item[field]:
                raise GateInputError(f"evidence.completed_effects[{index}].{field} must be a non-empty string")
        if item["effect"] not in EFFECTS:
            raise GateInputError(f"evidence.completed_effects[{index}].effect is unknown")
        if item["effect_id"] in seen_effect_ids:
            raise GateInputError("evidence.completed_effects contains duplicate effect_id")
        seen_effect_ids.add(item["effect_id"])
        if item["status"] != "committed":
            raise GateInputError("completed effect status must be committed")
        if item["request_sha256"] == request_sha:
            reasons.append("ALREADY_EFFECTED")
        if item["effect"] == request["effect"]:
            completed_for_effect += 1
    if completed_for_effect >= effect_budget[request["effect"]]:
        reasons.append("EFFECT_BUDGET_EXHAUSTED")

    approval_expires_at: datetime | None = None
    if request["effect"] in approval_required_effects:
        raw_approval = manifest.get("approval")
        if raw_approval is None:
            reasons.append("APPROVAL_MISSING")
        else:
            approval = _require_dict(raw_approval, "approval")
            for field in ("approval_id", "actor", "request_sha256", "issued_at", "expires_at"):
                if not isinstance(approval.get(field), str) or not approval[field]:
                    raise GateInputError(f"approval.{field} must be a non-empty string")
            issued_at = _parse_time(approval["issued_at"], "approval.issued_at")
            approval_expires_at = _parse_time(approval["expires_at"], "approval.expires_at")
            if approval["actor"] not in approvers:
                reasons.append("APPROVER_NOT_ALLOWED")
            if approval["request_sha256"] != request_sha:
                reasons.append("APPROVAL_SCOPE_MISMATCH")
            if issued_at - evaluated_at > max_future_skew:
                reasons.append("APPROVAL_FROM_FUTURE")
            if approval_expires_at <= evaluated_at:
                reasons.append("APPROVAL_EXPIRED")
            if approval_expires_at <= issued_at:
                reasons.append("APPROVAL_INVALID_INTERVAL")

    reasons = sorted(set(reasons))
    decision = "RELEASE" if not reasons else "HOLD"

    receipt: dict[str, Any] = {
        "version": VERSION,
        "run_id": manifest["run_id"],
        "agent_id": manifest["agent_id"],
        "request_sha256": request_sha,
        "evaluated_at": _iso(evaluated_at),
        "decision": decision,
        "reasons": reasons,
        "authority_boundary": (
            "Pre-effect admission only; this receipt does not grant credentials, execute the tool, "
            "prove provider state, settle payment, or authorize reuse after expiry."
        ),
    }
    if decision == "RELEASE":
        expires_at = _decision_expiry(
            evaluated_at, policy, snapshot_at, evidence_times, approval_expires_at
        )
        if expires_at <= evaluated_at:
            # This should normally have been caught by a stale/future/approval reason, but fail closed
            # if an edge condition ever collapses the release interval.
            receipt["decision"] = "HOLD"
            receipt["reasons"] = ["NO_POSITIVE_RELEASE_WINDOW"]
        else:
            receipt["release_expires_at"] = _iso(expires_at)
    receipt["receipt_sha256"] = sha256_json(receipt)
    return receipt


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate an agent tool request against a release manifest")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        receipt = evaluate(_load(args.manifest), datetime.now(timezone.utc))
    except (GateInputError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"decision": "HOLD", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0 if receipt["decision"] == "RELEASE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
