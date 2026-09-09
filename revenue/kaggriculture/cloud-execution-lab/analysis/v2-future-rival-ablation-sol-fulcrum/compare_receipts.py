# SPDX-License-Identifier: Apache-2.0
"""Bind arm receipts to exact frozen and materialized runtime closures."""
from __future__ import annotations

import hashlib

from compare_common import (
    ABLATION_SCENARIOS,
    CompareError,
    ENTRYPOINT_SHA256,
    FREEZE_GIT_BLOB,
    OPERATION,
    SCHEDULER_GIT_BLOB,
    SCHEDULER_SHA256,
    V2_SCENARIOS,
    closure_digest,
    require_hex,
    validate_inventory,
)

def validate_receipt(receipt: dict[str, Any], arm: str, head: str) -> None:
    if receipt.get("schema_version") != 1:
        raise CompareError(f"{arm} receipt schema mismatch")
    if receipt.get("operation") != OPERATION or receipt.get("arm") != arm:
        raise CompareError(f"{arm} receipt operation/arm mismatch")
    if receipt.get("checkout_head") != head:
        raise CompareError(f"{arm} receipt checkout head mismatch")
    source = receipt.get("source")
    materialized = receipt.get("materialized")
    entry = receipt.get("entry")
    patch = receipt.get("patch")
    if not all(isinstance(item, dict) for item in (source, materialized, entry, patch)):
        raise CompareError(f"{arm} receipt sections must be objects")

    if source.get("freeze_git_blob") != FREEZE_GIT_BLOB:
        raise CompareError(f"{arm} frozen manifest blob mismatch")
    if source.get("scheduler_git_blob") != SCHEDULER_GIT_BLOB:
        raise CompareError(f"{arm} frozen scheduler blob mismatch")
    if source.get("scheduler_sha256") != SCHEDULER_SHA256:
        raise CompareError(f"{arm} frozen scheduler digest mismatch")
    if source.get("entrypoint_sha256") != ENTRYPOINT_SHA256:
        raise CompareError(f"{arm} frozen entrypoint digest mismatch")

    source_inventory = validate_inventory(source.get("runtime_inventory"), f"{arm} source")
    materialized_inventory = validate_inventory(
        materialized.get("runtime_inventory"), f"{arm} materialized"
    )
    source_closure = require_hex(
        source.get("runtime_closure_sha256"), 64, f"{arm} source closure"
    )
    materialized_closure = require_hex(
        materialized.get("runtime_closure_sha256"), 64, f"{arm} runtime closure"
    )
    if closure_digest(source_inventory) != source_closure:
        raise CompareError(f"{arm} source inventory does not hash to its closure")
    if closure_digest(materialized_inventory) != materialized_closure:
        raise CompareError(f"{arm} materialized inventory does not hash to its closure")
    if source_inventory["scheduler.py"]["sha256"] != SCHEDULER_SHA256:
        raise CompareError(f"{arm} source scheduler inventory mismatch")
    if source_inventory["candidate.py"]["sha256"] != ENTRYPOINT_SHA256:
        raise CompareError(f"{arm} source candidate inventory mismatch")
    if materialized.get("scheduler_sha256") != materialized_inventory["scheduler.py"]["sha256"]:
        raise CompareError(f"{arm} materialized scheduler digest is inventory-detached")
    require_hex(materialized.get("scheduler_git_blob"), 40, f"{arm} materialized scheduler blob")

    changed = [
        path
        for path in sorted(set(source_inventory) | set(materialized_inventory))
        if source_inventory.get(path) != materialized_inventory.get(path)
    ]
    expected_changes = [] if arm == "control" else ["scheduler.py"]
    if changed != expected_changes or materialized.get("changed_paths") != expected_changes:
        raise CompareError(f"{arm} changed-path set mismatch")
    if arm == "control" and materialized.get("scheduler_git_blob") != SCHEDULER_GIT_BLOB:
        raise CompareError("control scheduler Git blob is not frozen V2")

    if source.get("scenario_names") != list(V2_SCENARIOS):
        raise CompareError(f"{arm} source scenario sequence mismatch")
    expected_names = list(V2_SCENARIOS if arm == "control" else ABLATION_SCENARIOS)
    if materialized.get("scenario_names") != expected_names:
        raise CompareError(f"{arm} materialized scenario sequence mismatch")

    require_hex(entry.get("runtime_closure_sha256"), 64, f"{arm} entry closure")
    require_hex(entry.get("sha256"), 64, f"{arm} entry digest")
    if entry.get("path") != "entry.py" or type(entry.get("bytes")) is not int or entry.get("bytes") <= 0:
        raise CompareError(f"{arm} generated entry metadata mismatch")
    if entry.get("runtime_closure_sha256") != materialized_closure:
        raise CompareError(f"{arm} entry is detached from materialized closure")

    diff = patch.get("unified_diff")
    if not isinstance(diff, str):
        raise CompareError(f"{arm} patch diff must be text")
    expected_patch_sha = hashlib.sha256(diff.encode("utf-8")).hexdigest()
    if patch.get("sha256") != expected_patch_sha:
        raise CompareError(f"{arm} patch digest mismatch")
    if arm == "control":
        if materialized_closure != source_closure or source_inventory != materialized_inventory:
            raise CompareError("control runtime is not the source closure")
        if diff:
            raise CompareError("control receipt unexpectedly contains a source diff")
    else:
        if materialized_closure == source_closure:
            raise CompareError("ablation runtime closure did not change")
        if not diff:
            raise CompareError("ablation receipt lacks its exact source diff")
