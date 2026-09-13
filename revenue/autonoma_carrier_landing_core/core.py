# SPDX-License-Identifier: MIT
"""Deterministic offline admission and landing receipts for parallel-agent carriers.

This module deliberately does *not* invoke git, GitHub, CI, network services, or
customer systems.  It turns a bounded batch of observed branch evidence into a
fail-closed landing plan and then applies that plan to an in-memory state
machine.  A real integration can map the returned MERGE intents to guarded
provider operations while keeping provider authority outside this core.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable


SCHEMA_VERSION = 1
_HEX = frozenset("0123456789abcdef")
_ALLOWED_BATCH_KEYS = {
    "schema_version",
    "batch_id",
    "base_sha",
    "carrier_prefix",
    "branches",
}
_ALLOWED_BRANCH_KEYS = {
    "branch_id",
    "order",
    "base_sha",
    "manifest",
    "manifest_sha256",
    "observed_paths",
    "premerge_tests",
    "postmerge_tests",
    "candidate_tree_sha",
}
_ALLOWED_MANIFEST_KEYS = {"paths", "purpose"}
_ALLOWED_TEST_KEYS = {"status", "suite_sha256"}


class LandingInputError(ValueError):
    """Raised when evidence is malformed enough that no plan can be trusted."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _require_object(value: Any, *, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LandingInputError(f"{where} must be an object")
    return value


def _require_exact_keys(
    value: dict[str, Any], allowed: set[str], *, where: str
) -> None:
    extra = sorted(set(value) - allowed)
    if extra:
        raise LandingInputError(f"{where} has unknown fields: {','.join(extra)}")


def _require_text(value: Any, *, where: str) -> str:
    if type(value) is not str or not value.strip():
        raise LandingInputError(f"{where} must be non-empty text")
    if value != value.strip():
        raise LandingInputError(f"{where} must not have surrounding whitespace")
    return value


def _require_sha(value: Any, *, where: str) -> str:
    text = _require_text(value, where=where).lower()
    if len(text) != 64 or any(ch not in _HEX for ch in text):
        raise LandingInputError(f"{where} must be a 64-character lowercase SHA-256")
    return text


def _require_int(value: Any, *, where: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise LandingInputError(f"{where} must be an integer >= {minimum}")
    return value


def _require_path(value: Any, *, where: str) -> str:
    path = _require_text(value, where=where)
    if path.startswith("/") or path.endswith("/"):
        raise LandingInputError(f"{where} must be a relative file path")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise LandingInputError(f"{where} contains an unsafe path segment")
    if "\\" in path or "\x00" in path:
        raise LandingInputError(f"{where} must use safe POSIX separators")
    return path


def _require_paths(value: Any, *, where: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise LandingInputError(f"{where} must be a non-empty list")
    paths = [_require_path(item, where=f"{where}[{index}]") for index, item in enumerate(value)]
    if len(paths) != len(set(paths)):
        raise LandingInputError(f"{where} contains duplicate paths")
    return paths


def _normalize_prefix(value: Any) -> str:
    prefix = _require_text(value, where="carrier_prefix")
    if prefix.startswith("/") or "\\" in prefix or "\x00" in prefix:
        raise LandingInputError("carrier_prefix must be a safe relative prefix")
    if not prefix.endswith("/"):
        prefix += "/"
    _require_path(prefix[:-1], where="carrier_prefix")
    return prefix


def _normalize_tests(value: Any, *, where: str) -> dict[str, str]:
    obj = _require_object(value, where=where)
    _require_exact_keys(obj, _ALLOWED_TEST_KEYS, where=where)
    status = _require_text(obj.get("status"), where=f"{where}.status")
    if status not in {"PASS", "FAIL"}:
        raise LandingInputError(f"{where}.status must be PASS or FAIL")
    suite_sha = _require_sha(obj.get("suite_sha256"), where=f"{where}.suite_sha256")
    return {"status": status, "suite_sha256": suite_sha}


def _normalize_branch(value: Any, *, index: int) -> dict[str, Any]:
    where = f"branches[{index}]"
    obj = _require_object(value, where=where)
    _require_exact_keys(obj, _ALLOWED_BRANCH_KEYS, where=where)

    manifest = _require_object(obj.get("manifest"), where=f"{where}.manifest")
    _require_exact_keys(manifest, _ALLOWED_MANIFEST_KEYS, where=f"{where}.manifest")
    manifest_paths = _require_paths(manifest.get("paths"), where=f"{where}.manifest.paths")
    purpose = _require_text(manifest.get("purpose"), where=f"{where}.manifest.purpose")
    normalized_manifest = {"paths": manifest_paths, "purpose": purpose}

    return {
        "branch_id": _require_text(obj.get("branch_id"), where=f"{where}.branch_id"),
        "order": _require_int(obj.get("order"), where=f"{where}.order"),
        "base_sha": _require_sha(obj.get("base_sha"), where=f"{where}.base_sha"),
        "manifest": normalized_manifest,
        "manifest_sha256": _require_sha(
            obj.get("manifest_sha256"), where=f"{where}.manifest_sha256"
        ),
        "observed_paths": _require_paths(
            obj.get("observed_paths"), where=f"{where}.observed_paths"
        ),
        "premerge_tests": _normalize_tests(
            obj.get("premerge_tests"), where=f"{where}.premerge_tests"
        ),
        "postmerge_tests": _normalize_tests(
            obj.get("postmerge_tests"), where=f"{where}.postmerge_tests"
        ),
        "candidate_tree_sha": _require_sha(
            obj.get("candidate_tree_sha"), where=f"{where}.candidate_tree_sha"
        ),
    }


def normalize_batch(payload: Any) -> dict[str, Any]:
    """Return canonical batch evidence or raise before any plan is produced."""
    batch = _require_object(payload, where="batch")
    _require_exact_keys(batch, _ALLOWED_BATCH_KEYS, where="batch")
    if batch.get("schema_version") != SCHEMA_VERSION:
        raise LandingInputError(f"schema_version must be {SCHEMA_VERSION}")

    branches_raw = batch.get("branches")
    if not isinstance(branches_raw, list) or not branches_raw:
        raise LandingInputError("branches must be a non-empty list")
    branches = [_normalize_branch(item, index=i) for i, item in enumerate(branches_raw)]

    branch_ids = [branch["branch_id"] for branch in branches]
    orders = [branch["order"] for branch in branches]
    if len(branch_ids) != len(set(branch_ids)):
        raise LandingInputError("branch_id values must be unique")
    if len(orders) != len(set(orders)):
        raise LandingInputError("branch order values must be unique")

    return {
        "schema_version": SCHEMA_VERSION,
        "batch_id": _require_text(batch.get("batch_id"), where="batch_id"),
        "base_sha": _require_sha(batch.get("base_sha"), where="base_sha"),
        "carrier_prefix": _normalize_prefix(batch.get("carrier_prefix")),
        "branches": sorted(branches, key=lambda item: (item["order"], item["branch_id"])),
    }


def manifest_sha256(manifest: dict[str, Any]) -> str:
    """Compute the digest a carrier must publish for its declared manifest."""
    return _digest(manifest)


def _inside_carrier(path: str, carrier_prefix: str) -> bool:
    return path.startswith(carrier_prefix) and len(path) > len(carrier_prefix)


def _branch_reasons(
    branch: dict[str, Any], *, batch_base_sha: str, carrier_prefix: str
) -> list[str]:
    reasons: list[str] = []
    declared = branch["manifest"]["paths"]
    observed = branch["observed_paths"]

    if any(not _inside_carrier(path, carrier_prefix) for path in observed):
        reasons.append("FORBIDDEN_PATH")
    if branch["base_sha"] != batch_base_sha:
        reasons.append("STALE_BASE")
    if branch["manifest_sha256"] != manifest_sha256(branch["manifest"]):
        reasons.append("MANIFEST_MISMATCH")
    if declared != observed:
        if "MANIFEST_MISMATCH" not in reasons:
            reasons.append("MANIFEST_MISMATCH")
    if branch["premerge_tests"]["status"] != "PASS":
        reasons.append("TEST_FAILURE")
    if branch["postmerge_tests"]["status"] != "PASS":
        if "TEST_FAILURE" not in reasons:
            reasons.append("TEST_FAILURE")
    return reasons


def build_plan(payload: Any) -> dict[str, Any]:
    """Build a deterministic fail-closed landing receipt from bounded evidence.

    Admission is intentionally all-or-branch-local: one bad carrier is held but
    does not erase unrelated valid carriers.  Valid carriers may not overlap
    paths with an earlier valid carrier in the same declared landing order.
    """
    batch = normalize_batch(payload)
    decisions: list[dict[str, Any]] = []
    landing_order: list[str] = []
    claimed_paths: dict[str, str] = {}

    for branch in batch["branches"]:
        reasons = _branch_reasons(
            branch,
            batch_base_sha=batch["base_sha"],
            carrier_prefix=batch["carrier_prefix"],
        )

        if not reasons:
            collisions = sorted(
                path for path in branch["observed_paths"] if path in claimed_paths
            )
            if collisions:
                reasons.append("OWNERSHIP_COLLISION")

        disposition = "LAND" if not reasons else "HOLD"
        if disposition == "LAND":
            landing_order.append(branch["branch_id"])
            for path in branch["observed_paths"]:
                claimed_paths[path] = branch["branch_id"]

        decisions.append(
            {
                "branch_id": branch["branch_id"],
                "order": branch["order"],
                "disposition": disposition,
                "reason_codes": reasons,
                "manifest_sha256": branch["manifest_sha256"],
                "observed_paths": list(branch["observed_paths"]),
                "candidate_tree_sha": branch["candidate_tree_sha"],
                "premerge_suite_sha256": branch["premerge_tests"]["suite_sha256"],
                "postmerge_suite_sha256": branch["postmerge_tests"]["suite_sha256"],
            }
        )

    body = {
        "schema_version": SCHEMA_VERSION,
        "batch_id": batch["batch_id"],
        "base_sha": batch["base_sha"],
        "carrier_prefix": batch["carrier_prefix"],
        "input_sha256": _digest(batch),
        "landing_order": landing_order,
        "branches": decisions,
        "provider_intents": [
            {
                "operation": "MERGE",
                "branch_id": branch_id,
                "force": False,
                "delete_branch": False,
            }
            for branch_id in landing_order
        ],
    }
    body["receipt_sha256"] = _digest(body)
    return body


def verify_plan(plan: Any) -> dict[str, Any]:
    """Verify the self-digest and non-destructive provider-intent contract."""
    obj = _require_object(plan, where="plan")
    required = {
        "schema_version",
        "batch_id",
        "base_sha",
        "carrier_prefix",
        "input_sha256",
        "landing_order",
        "branches",
        "provider_intents",
        "receipt_sha256",
    }
    if set(obj) != required:
        raise LandingInputError("plan fields do not match the canonical receipt schema")
    expected = _digest({key: value for key, value in obj.items() if key != "receipt_sha256"})
    if obj["receipt_sha256"] != expected:
        raise LandingInputError("plan receipt digest mismatch")
    if not isinstance(obj["provider_intents"], list):
        raise LandingInputError("provider_intents must be a list")
    for index, intent in enumerate(obj["provider_intents"]):
        if intent != {
            "operation": "MERGE",
            "branch_id": intent.get("branch_id") if isinstance(intent, dict) else None,
            "force": False,
            "delete_branch": False,
        }:
            raise LandingInputError(
                f"provider_intents[{index}] is not a non-destructive MERGE intent"
            )
    return copy.deepcopy(obj)


@dataclass(frozen=True)
class ApplyResult:
    receipt: dict[str, Any]
    new_merges: int
    merge_events: tuple[dict[str, Any], ...]
    state: dict[str, Any]


def apply_plan(plan: Any, state: Any) -> ApplyResult:
    """Apply an already-built receipt to an in-memory idempotency state.

    The returned ``receipt`` is byte-for-byte data-equivalent on reapplication.
    State records completion by receipt digest.  Reapplying a completed receipt
    performs zero new merges and returns no new merge events.
    """
    receipt = verify_plan(plan)
    current = _require_object(state, where="state")
    allowed_state_keys = {"completed_receipts", "landed_branches", "main_green"}
    _require_exact_keys(current, allowed_state_keys, where="state")

    completed_raw = current.get("completed_receipts")
    landed_raw = current.get("landed_branches")
    if not isinstance(completed_raw, list) or not all(type(v) is str for v in completed_raw):
        raise LandingInputError("state.completed_receipts must be a list of strings")
    if not isinstance(landed_raw, list) or not all(type(v) is str for v in landed_raw):
        raise LandingInputError("state.landed_branches must be a list of strings")
    if type(current.get("main_green")) is not bool:
        raise LandingInputError("state.main_green must be boolean")
    if not current["main_green"]:
        raise LandingInputError("main must be green before landing begins")

    next_state = {
        "completed_receipts": list(completed_raw),
        "landed_branches": list(landed_raw),
        "main_green": True,
    }
    receipt_sha = receipt["receipt_sha256"]
    if receipt_sha in next_state["completed_receipts"]:
        return ApplyResult(
            receipt=receipt,
            new_merges=0,
            merge_events=(),
            state=next_state,
        )

    events: list[dict[str, Any]] = []
    for branch_id in receipt["landing_order"]:
        if branch_id in next_state["landed_branches"]:
            raise LandingInputError(
                f"branch {branch_id} was already landed outside this receipt"
            )
        next_state["landed_branches"].append(branch_id)
        events.append(
            {
                "operation": "MERGE",
                "branch_id": branch_id,
                "force": False,
                "delete_branch": False,
                "main_green_after": True,
            }
        )

    next_state["completed_receipts"].append(receipt_sha)
    return ApplyResult(
        receipt=receipt,
        new_merges=len(events),
        merge_events=tuple(events),
        state=next_state,
    )


def empty_state() -> dict[str, Any]:
    return {"completed_receipts": [], "landed_branches": [], "main_green": True}


def make_branch(
    *,
    branch_id: str,
    order: int,
    base_sha: str,
    paths: Iterable[str],
    purpose: str,
    candidate_tree_sha: str,
    premerge_status: str = "PASS",
    postmerge_status: str = "PASS",
    observed_paths: Iterable[str] | None = None,
    manifest_digest_override: str | None = None,
) -> dict[str, Any]:
    """Small fixture helper used by the deterministic acceptance generator."""
    manifest = {"paths": list(paths), "purpose": purpose}
    observed = list(manifest["paths"] if observed_paths is None else observed_paths)
    return {
        "branch_id": branch_id,
        "order": order,
        "base_sha": base_sha,
        "manifest": manifest,
        "manifest_sha256": manifest_digest_override or manifest_sha256(manifest),
        "observed_paths": observed,
        "premerge_tests": {
            "status": premerge_status,
            "suite_sha256": hashlib.sha256(f"pre:{branch_id}".encode()).hexdigest(),
        },
        "postmerge_tests": {
            "status": postmerge_status,
            "suite_sha256": hashlib.sha256(f"post:{branch_id}".encode()).hexdigest(),
        },
        "candidate_tree_sha": candidate_tree_sha,
    }
