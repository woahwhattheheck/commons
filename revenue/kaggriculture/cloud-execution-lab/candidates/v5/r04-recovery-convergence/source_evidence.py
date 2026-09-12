# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import base64, hashlib, subprocess
from pathlib import Path
from typing import Any, Mapping

from common import (
    GateError, HEX40, HEX64, exact_bool, git_blob_sha1, hex_value,
    loads_raw, plain_int, safe_path, text,
)

SOURCE_RECEIPT_SCHEMA = "titan-v5-r04-component-source-receipt/v1"
SOURCE_MANIFEST_SCHEMA = "titan-v5-r04-composition-source-manifest/v1"
FORBIDDEN_SUFFIXES = ("/r04_full_router.py", "/r01_tapes.py")


def _source_manifest(manifest: Mapping[str, Any]):
    value, _, observed = loads_raw(
        manifest.get("composition_source_manifest_raw"),
        "composition_source_manifest_raw",
    )
    declared = hex_value(
        manifest.get("composition_source_manifest_sha256"),
        "composition_source_manifest_sha256",
        HEX64,
    )
    if observed != declared:
        raise GateError("composition source manifest byte hash mismatch")
    if type(value) is not dict or set(value) != {"schema", "target_version", "files"}:
        raise GateError("composition source manifest has wrong closed shape")
    if value["schema"] != SOURCE_MANIFEST_SCHEMA or value["target_version"] != "v5":
        raise GateError("composition source manifest authority mismatch")
    files = value["files"]
    if type(files) is not dict or not files:
        raise GateError("composition source manifest files must be a non-empty object")
    normalized = {}
    for path, row in files.items():
        path = safe_path(path, "composition source manifest path", FORBIDDEN_SUFFIXES)
        if type(row) is not dict or set(row) != {"sha256", "git_blob_sha1", "bytes"}:
            raise GateError(f"source manifest entry has wrong shape: {path}")
        normalized[path] = {
            "sha256": hex_value(row["sha256"], f"{path}.sha256", HEX64),
            "git_blob_sha1": hex_value(row["git_blob_sha1"], f"{path}.git_blob_sha1", HEX40),
            "bytes": plain_int(row["bytes"], f"{path}.bytes"),
        }
    return normalized, observed


def _component(
    raw_component: Any,
    index: int,
    source_manifest,
    source_manifest_sha: str,
    required_slots,
    forbidden_active_slots,
):
    prefix = f"components[{index}]"
    required_shape = {
        "slot", "current_abi", "producer_ownership",
        "source_receipt_raw", "source_receipt_sha256",
    }
    if type(raw_component) is not dict or set(raw_component) != required_shape:
        raise GateError(f"{prefix} has wrong closed shape")
    slot = text(raw_component["slot"], f"{prefix}.slot")
    if slot in forbidden_active_slots:
        raise GateError(f"{slot} is not an active standalone slot in submitted V3.1")
    if slot not in required_slots:
        raise GateError(f"unknown recovery slot: {slot}")
    if not exact_bool(raw_component["current_abi"], f"{prefix}.current_abi"):
        raise GateError(f"{slot} must be current-ABI")
    ownership = text(raw_component["producer_ownership"], f"{prefix}.producer_ownership")
    expected = "single_parent_delegate" if slot == "fert_hand_boundary" else "none"
    if ownership != expected:
        raise GateError(f"{slot} producer_ownership must be {expected}")

    receipt, _, receipt_sha = loads_raw(
        raw_component["source_receipt_raw"], f"{prefix}.source_receipt_raw"
    )
    if receipt_sha != hex_value(
        raw_component["source_receipt_sha256"], f"{prefix}.source_receipt_sha256", HEX64
    ):
        raise GateError(f"{slot} source receipt byte hash mismatch")
    receipt_shape = {
        "schema", "slot", "current_abi", "producer_ownership",
        "composition_source_manifest_sha256", "files",
    }
    if type(receipt) is not dict or set(receipt) != receipt_shape:
        raise GateError(f"{slot} source receipt has wrong closed shape")
    if receipt["schema"] != SOURCE_RECEIPT_SCHEMA:
        raise GateError(f"{slot} source receipt schema mismatch")
    if receipt["slot"] != slot or receipt["current_abi"] is not True:
        raise GateError(f"{slot} source receipt identity/current-ABI mismatch")
    if receipt["producer_ownership"] != ownership:
        raise GateError(f"{slot} source receipt producer ownership mismatch")
    if receipt["composition_source_manifest_sha256"] != source_manifest_sha:
        raise GateError(f"{slot} source receipt binds a different composition source manifest")

    rows = receipt["files"]
    if type(rows) is not list or not rows:
        raise GateError(f"{slot} source receipt files must be a non-empty list")
    payloads, normalized_files = {}, []
    for file_index, row in enumerate(rows):
        field = f"{prefix}.source_receipt.files[{file_index}]"
        if type(row) is not dict or set(row) != {
            "path", "content_b64", "sha256", "git_blob_sha1"
        }:
            raise GateError(f"{field} has wrong closed shape")
        path = safe_path(row["path"], f"{field}.path", FORBIDDEN_SUFFIXES)
        if path in payloads:
            raise GateError(f"{slot} source receipt repeats path: {path}")
        try:
            payload = base64.b64decode(text(row["content_b64"], f"{field}.content_b64"), validate=True)
        except Exception as exc:
            raise GateError(f"{field}.content_b64 is not strict base64") from exc
        sha256 = hex_value(row["sha256"], f"{field}.sha256", HEX64)
        blob = hex_value(row["git_blob_sha1"], f"{field}.git_blob_sha1", HEX40)
        if hashlib.sha256(payload).hexdigest() != sha256:
            raise GateError(f"{slot} source payload SHA-256 mismatch: {path}")
        if git_blob_sha1(payload) != blob:
            raise GateError(f"{slot} source payload Git-blob mismatch: {path}")
        if source_manifest.get(path) != {
            "sha256": sha256, "git_blob_sha1": blob, "bytes": len(payload)
        }:
            raise GateError(f"{slot} source payload disagrees with composition manifest: {path}")
        payloads[path] = payload
        normalized_files.append({
            "path": path, "sha256": sha256, "git_blob_sha1": blob, "bytes": len(payload)
        })
    return slot, {
        "slot": slot,
        "current_abi": True,
        "producer_ownership": ownership,
        "source_receipt_sha256": receipt_sha,
        "files": normalized_files,
    }, payloads


def _git(repository_root: Path, *args: str) -> bytes:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repository_root), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    except OSError as exc:
        raise GateError("cannot execute git for composition authority") from exc
    if proc.returncode != 0:
        message = proc.stderr.decode("utf-8", "replace").strip()
        raise GateError(f"git composition authority failed: {message or args!r}")
    return proc.stdout


def _verify_git(repository_root: Path, commit_value: Any, payloads):
    commit = hex_value(commit_value, "composition_git_commit", HEX40)
    resolved = _git(repository_root, "rev-parse", "--verify", f"{commit}^{{commit}}").decode().strip()
    if resolved != commit:
        raise GateError("composition_git_commit does not resolve to the exact requested commit")
    tree = _git(repository_root, "rev-parse", f"{commit}^{{tree}}").decode().strip()
    if HEX40.fullmatch(tree) is None:
        raise GateError("composition Git tree identity is noncanonical")
    for path, payload in sorted(payloads.items()):
        blob = _git(repository_root, "rev-parse", f"{commit}:{path}").decode().strip()
        if blob != git_blob_sha1(payload):
            raise GateError(f"composition Git path/blob authority mismatch: {path}")
        if _git(repository_root, "show", f"{commit}:{path}") != payload:
            raise GateError(f"composition Git path bytes disagree with source receipt: {path}")
    return commit, tree


def validate_sources(
    manifest: Mapping[str, Any],
    repository_root: Path | None,
    required_slots,
    forbidden_active_slots,
):
    source_manifest, source_manifest_sha = _source_manifest(manifest)
    raw_components = manifest.get("components")
    if type(raw_components) is not list:
        raise GateError("components must be a list")

    components, payloads = {}, {}
    blockers = []
    for index, raw_component in enumerate(raw_components):
        slot, normalized, component_payloads = _component(
            raw_component, index, source_manifest, source_manifest_sha,
            required_slots, forbidden_active_slots,
        )
        if slot in components:
            raise GateError(f"duplicate semantic slot: {slot}")
        components[slot] = normalized
        for path, payload in component_payloads.items():
            if path in payloads and payloads[path] != payload:
                raise GateError(f"conflicting source bytes across component receipts: {path}")
            payloads[path] = payload

    for slot in required_slots:
        if slot not in components:
            blockers.append(f"missing_component:{slot}")
    if set(payloads) != set(source_manifest):
        missing = sorted(set(source_manifest) - set(payloads))
        extra = sorted(set(payloads) - set(source_manifest))
        raise GateError(
            f"composition source manifest coverage mismatch; missing={missing!r} extra={extra!r}"
        )

    if repository_root is None:
        commit = tree = None
        blockers.append("git_tree_not_authenticated")
    else:
        commit, tree = _verify_git(repository_root, manifest.get("composition_git_commit"), payloads)

    ordered = [components[slot] for slot in required_slots if slot in components]
    return ordered, source_manifest_sha, commit, tree, blockers
