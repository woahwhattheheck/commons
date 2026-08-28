#!/usr/bin/env python3
"""Provider-neutral federated CI receipt engine.

The muhlnickel is the computer. This module plans shards, wraps a runner-neutral
command envelope, normalizes receipts, and reconciles them. It does not activate
a CI provider. Provider names are observations, not gates. Unknown providers
remain legal manifest targets. A config file or a fixture is not a measured run.

Cite PLUMB/Opus 5 #commons 2026-08-23. Do not remint. Do not invent run URLs,
quota, success, failover, or another provider going LIVE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MANIFEST_SCHEMA_VERSION = "commons-federated-job-manifest/v1"
RECEIPT_SCHEMA_VERSION = "commons-federated-receipt/v1"
RECONCILE_SCHEMA_VERSION = "commons-federated-reconciliation/v1"
SCANNER_VERSION = "commons-federated-ci-scan/v1"
ENGINE_VERSION = "commons-federated-ci/v1"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

TERMINAL_STATES = frozenset(
    {"PASSED", "FAILED", "CANCELLED", "SKIPPED", "TIMED_OUT", "FIXTURE"}
)
# FIXTURE means the receipt is a shape/config observation, not an executed job.

SUPPORTED_BY_CONTRACT = (
    "github-actions",
    "cirrus",
    "gitlab",
    "woodpecker",
    "local-fixture",
)

SCAN_PATTERNS = {
    "PRIVATE_KEY": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GITHUB_TOKEN": re.compile(rb"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "SLACK_TOKEN": re.compile(rb"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "AWS_KEY": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "STRIPE_SECRET": re.compile(rb"(?:sk|rk)_live_[A-Za-z0-9]{16,}"),
    "BEARER": re.compile(rb"Bearer\s+[A-Za-z0-9._~+/=-]{16,}", re.IGNORECASE),
    "PASSWORD": re.compile(rb"(?:password|passwd|pwd)\s*[:=]\s*[^\s,;]{4,}", re.IGNORECASE),
    "EMAIL": re.compile(rb"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "PHONE": re.compile(
        rb"(?<!\d)(?:\+?1[-. ]?)?\(?[2-9]\d{2}\)?[-. ]?\d{3}[-. ]?\d{4}(?!\d)"
    ),
}

MANIFEST_KEYS = {
    "schema_version",
    "kind",
    "job_id",
    "source_sha",
    "repository",
    "tests",
    "shard_count",
    "command_template",
    "providers",
    "timeout_s",
    "claim_boundary",
}

RECEIPT_KEYS = {
    "schema_version",
    "kind",
    "receipt_id",
    "job_id",
    "shard_id",
    "attempt",
    "parent_receipt_id",
    "source_sha",
    "test_identity",
    "command",
    "exit_code",
    "duration_ms",
    "artifacts",
    "provider",
    "run_url",
    "terminal_state",
    "measured",
    "claim_boundary",
    "scan",
}

COMMAND_KEYS = {"argv", "cwd", "env", "timeout_s", "shell"}
ARTIFACT_KEYS = {"path", "sha256", "bytes"}
CLAIM_KEYS = {
    "measured_live_run",
    "provider_activated_by_this_engine",
    "other_provider_activated",
    "fabricated_url",
    "quota_claimed",
}


class FederatedError(ValueError):
    """Schema, planning, receipt, or reconciliation boundary violation."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FederatedError(message)


def _exact_keys(value: Any, required: set[str], at: str) -> None:
    _require(isinstance(value, dict), f"{at} must be an object")
    missing = sorted(required - set(value))
    extra = sorted(set(value) - required)
    _require(not missing, f"{at} missing keys {missing!r}")
    _require(not extra, f"{at} has extra keys {extra!r}")


def scan_bytes(raw: bytes) -> dict[str, int]:
    return {name: len(pattern.findall(raw)) for name, pattern in SCAN_PATTERNS.items()}


def scan_obj(obj: Any) -> dict[str, int]:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return scan_bytes(raw)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def receipt_id_for(
    job_id: str,
    shard_id: int,
    attempt: int,
    provider: str,
    source_sha: str,
    test_identity: str,
) -> str:
    material = f"{job_id}|{shard_id}|{attempt}|{provider}|{source_sha}|{test_identity}"
    return "fcr-" + sha256_text(material)[:16]


def command_envelope(
    argv: list[str],
    cwd: str = ".",
    env: dict[str, str] | None = None,
    timeout_s: int = 60,
    shell: bool = False,
) -> dict[str, Any]:
    _require(isinstance(argv, list) and argv and all(isinstance(x, str) for x in argv), "argv invalid")
    _require(isinstance(cwd, str) and cwd and ".." not in Path(cwd).parts, "cwd escapes")
    _require(shell is False, "shell envelopes are refused")
    env = env or {}
    _require(isinstance(env, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()), "env invalid")
    banned = {k.upper() for k in env}
    _require(not (banned & {"GITHUB_TOKEN", "GH_TOKEN", "AWS_SECRET_ACCESS_KEY", "SLACK_BOT_TOKEN"}), "env carries a secret name")
    _require(isinstance(timeout_s, int) and 1 <= timeout_s <= 21600, "timeout_s out of range")
    envelope = {
        "argv": list(argv),
        "cwd": cwd,
        "env": dict(sorted(env.items())),
        "timeout_s": timeout_s,
        "shell": False,
    }
    _exact_keys(envelope, COMMAND_KEYS, "command")
    return envelope


def plan_shards(tests: list[str], shard_count: int) -> list[dict[str, Any]]:
    _require(isinstance(tests, list) and tests, "tests must be a non-empty list")
    _require(all(isinstance(t, str) and t.strip() and t == t.strip() for t in tests), "test identity invalid")
    _require(len(set(tests)) == len(tests), "duplicate test identities")
    _require(isinstance(shard_count, int) and shard_count >= 1, "shard_count must be >= 1")
    _require(shard_count <= len(tests), "shard_count exceeds test count")
    ordered = sorted(tests)
    shards: list[list[str]] = [[] for _ in range(shard_count)]
    for index, identity in enumerate(ordered):
        shards[index % shard_count].append(identity)
    planned = []
    for shard_id, members in enumerate(shards):
        planned.append(
            {
                "shard_id": shard_id,
                "tests": members,
                "test_identity": "+".join(members),
            }
        )
    return planned


def validate_claim_boundary(boundary: Any, at: str = "claim_boundary") -> dict[str, Any]:
    _exact_keys(boundary, CLAIM_KEYS, at)
    for key in CLAIM_KEYS:
        _require(isinstance(boundary[key], bool), f"{at}.{key} must be bool")
    _require(boundary["fabricated_url"] is False, "fabricated_url must stay false")
    _require(boundary["quota_claimed"] is False, "quota_claimed must stay false")
    if boundary["measured_live_run"] is False:
        _require(boundary["provider_activated_by_this_engine"] is False, "unmeasured run cannot claim activation")
    _require(boundary["other_provider_activated"] is False, "must not claim another provider was activated")
    return boundary


def validate_manifest(manifest: Any) -> dict[str, Any]:
    _exact_keys(manifest, MANIFEST_KEYS, "manifest")
    _require(manifest["schema_version"] == MANIFEST_SCHEMA_VERSION, "manifest schema_version drift")
    _require(manifest["kind"] == "FEDERATED_JOB_MANIFEST", "manifest kind drift")
    _require(isinstance(manifest["job_id"], str) and manifest["job_id"], "job_id invalid")
    _require(bool(HEX40.fullmatch(manifest["source_sha"])), "source_sha invalid")
    _require(manifest["repository"] == "woahwhattheheck/commons", "repository drift")
    _require(isinstance(manifest["timeout_s"], int) and manifest["timeout_s"] >= 1, "timeout_s invalid")
    tmpl = manifest["command_template"]
    _require(isinstance(tmpl, dict) and isinstance(tmpl.get("argv"), list), "command_template invalid")
    command_envelope(
        list(tmpl["argv"]),
        cwd=tmpl.get("cwd", "."),
        env=tmpl.get("env") or {},
        timeout_s=int(tmpl.get("timeout_s", manifest["timeout_s"])),
        shell=bool(tmpl.get("shell", False)),
    )
    providers = manifest["providers"]
    _require(isinstance(providers, list) and providers, "providers must be a list")
    _require(all(isinstance(p, str) and p.strip() for p in providers), "provider name invalid")
    # Unknown names stay legal. Presence is not activation.
    validate_claim_boundary(manifest["claim_boundary"], "manifest.claim_boundary")
    _require(manifest["claim_boundary"]["measured_live_run"] is False, "manifest is a plan, not a measured run")
    plan_shards(list(manifest["tests"]), int(manifest["shard_count"]))
    hits = scan_obj(manifest)
    _require(not any(hits.values()), f"manifest secret/PII scan hits {hits}")
    return manifest


def validate_receipt(receipt: Any, expected_source_sha: str | None = None) -> dict[str, Any]:
    _exact_keys(receipt, RECEIPT_KEYS, "receipt")
    _require(receipt["schema_version"] == RECEIPT_SCHEMA_VERSION, "receipt schema_version drift")
    _require(receipt["kind"] == "FEDERATED_CI_RECEIPT", "receipt kind drift")
    _require(isinstance(receipt["receipt_id"], str) and receipt["receipt_id"].startswith("fcr-"), "receipt_id invalid")
    _require(isinstance(receipt["job_id"], str) and receipt["job_id"], "job_id invalid")
    _require(isinstance(receipt["shard_id"], int) and receipt["shard_id"] >= 0, "shard_id invalid")
    _require(isinstance(receipt["attempt"], int) and receipt["attempt"] >= 1, "attempt invalid")
    parent = receipt["parent_receipt_id"]
    _require(parent is None or (isinstance(parent, str) and parent.startswith("fcr-")), "parent_receipt_id invalid")
    if receipt["attempt"] == 1:
        _require(parent is None, "attempt 1 cannot carry parent lineage")
    else:
        _require(isinstance(parent, str), "retry missing parent_receipt_id")
    _require(bool(HEX40.fullmatch(receipt["source_sha"])), "source_sha invalid")
    if expected_source_sha is not None:
        _require(receipt["source_sha"] == expected_source_sha, "stale-source run")
    _require(isinstance(receipt["test_identity"], str) and receipt["test_identity"], "test_identity invalid")
    cmd = receipt["command"]
    _exact_keys(cmd, COMMAND_KEYS, "receipt.command")
    command_envelope(cmd["argv"], cmd["cwd"], cmd["env"], cmd["timeout_s"], cmd["shell"])
    _require(isinstance(receipt["exit_code"], int), "exit_code invalid")
    _require(isinstance(receipt["duration_ms"], int) and receipt["duration_ms"] >= 0, "duration_ms invalid")
    artifacts = receipt["artifacts"]
    _require(isinstance(artifacts, list), "artifacts must be a list")
    for i, art in enumerate(artifacts):
        _exact_keys(art, ARTIFACT_KEYS, f"artifacts[{i}]")
        _require(isinstance(art["path"], str) and art["path"] and ".." not in Path(art["path"]).parts, "artifact path escapes")
        _require(bool(HEX64.fullmatch(art["sha256"])), "artifact sha256 invalid")
        _require(isinstance(art["bytes"], int) and art["bytes"] >= 0, "artifact bytes invalid")
    _require(isinstance(receipt["provider"], str) and receipt["provider"].strip(), "provider invalid")
    run_url = receipt["run_url"]
    _require(run_url is None or (isinstance(run_url, str) and run_url.startswith(("https://", "fixture://"))), "run_url invalid")
    _require(receipt["terminal_state"] in TERMINAL_STATES, "terminal_state invalid")
    _require(isinstance(receipt["measured"], bool), "measured invalid")
    validate_claim_boundary(receipt["claim_boundary"], "receipt.claim_boundary")
    if receipt["measured"] is True:
        _require(receipt["terminal_state"] != "FIXTURE", "measured receipt cannot be FIXTURE")
        _require(receipt["claim_boundary"]["measured_live_run"] is True, "measured flag disagrees with claim_boundary")
    else:
        _require(receipt["claim_boundary"]["measured_live_run"] is False, "unmeasured receipt claims live run")
        _require(receipt["run_url"] is None or str(receipt["run_url"]).startswith("fixture://"), "unmeasured receipt has a live URL")
    scan = receipt["scan"]
    _require(isinstance(scan, dict) and scan.get("scanner_version") == SCANNER_VERSION, "scan header drift")
    _require(scan.get("status") == "PASS_ZERO_HITS", "scan status drift")
    _require(not any(scan.get("hit_counts", {}).values()), "recorded scan contains hits")
    hits = scan_obj({k: receipt[k] for k in receipt if k != "scan"})
    _require(not any(hits.values()), f"receipt secret/PII scan hits {hits}")
    expected_id = receipt_id_for(
        receipt["job_id"],
        receipt["shard_id"],
        receipt["attempt"],
        receipt["provider"],
        receipt["source_sha"],
        receipt["test_identity"],
    )
    _require(receipt["receipt_id"] == expected_id, "receipt_id not deterministic")
    return receipt
