# SPDX-License-Identifier: Apache-2.0
"""Execute the exact control or one-factor future-rival materialization."""
from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any

from materialize_custody import (
    ABLATION_SCENARIOS,
    ENTRYPOINT_SHA256,
    HEX40,
    MaterializeError,
    OPERATION,
    V2_SCENARIOS,
    _regular_files,
    closure_digest,
    git_blob_bytes,
    inventory,
    sha256_bytes,
    verify_frozen_source,
)
from materialize_entry import _entry_source
from materialize_scenario import patch_scheduler, scenario_names

def _copy_runtime(source: Path, destination: Path, replacement: bytes | None) -> None:
    if destination.exists():
        if destination.is_symlink() or not destination.is_dir() or any(destination.iterdir()):
            raise MaterializeError(f"output runtime must not preexist nonempty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    for path in _regular_files(source):
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        data = replacement if relative.as_posix() == "scheduler.py" and replacement is not None else path.read_bytes()
        with target.open("xb") as handle:
            handle.write(data)

def materialize(
    source: Path,
    output: Path,
    arm: str,
    receipt_path: Path,
    checkout_head: str,
) -> dict[str, Any]:
    source = Path(source)
    output = Path(output)
    receipt_path = Path(receipt_path)
    if arm not in {"control", "ablation"}:
        raise MaterializeError(f"unsupported arm: {arm}")
    if not HEX40.fullmatch(checkout_head):
        raise MaterializeError("checkout head must be a lowercase 40-hex commit")
    if output.exists() and (
        output.is_symlink() or not output.is_dir() or any(output.iterdir())
    ):
        raise MaterializeError(f"output must be absent or empty directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    before = verify_frozen_source(source)
    original_text = (source / "scheduler.py").read_text(encoding="utf-8")
    if scenario_names(original_text) != V2_SCENARIOS:
        raise MaterializeError("frozen source scenario sequence drift")
    patched_text = patch_scheduler(original_text) if arm == "ablation" else original_text
    replacement = patched_text.encode("utf-8") if arm == "ablation" else None

    runtime = output / "runtime"
    _copy_runtime(source, runtime, replacement)
    materialized_inventory = inventory(runtime)
    changed = [
        name
        for name in sorted(set(before["inventory"]) | set(materialized_inventory))
        if before["inventory"].get(name) != materialized_inventory.get(name)
    ]
    expected_changed = ["scheduler.py"] if arm == "ablation" else []
    if changed != expected_changed:
        raise MaterializeError(
            f"materialized changed paths {changed} != expected {expected_changed}"
        )
    after_names = scenario_names((runtime / "scheduler.py").read_text(encoding="utf-8"))
    expected_names = ABLATION_SCENARIOS if arm == "ablation" else V2_SCENARIOS
    if after_names != expected_names:
        raise MaterializeError(f"materialized scenarios {after_names} != {expected_names}")

    source_after = inventory(source)
    if source_after != before["inventory"]:
        raise MaterializeError("frozen source changed during materialization")

    entry_text = _entry_source(materialized_inventory, arm)
    entry_path = output / "entry.py"
    with entry_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(entry_text)
    compile(entry_text, str(entry_path), "exec")

    diff = "".join(
        difflib.unified_diff(
            original_text.splitlines(keepends=True),
            patched_text.splitlines(keepends=True),
            fromfile="frozen-v2/scheduler.py",
            tofile=f"{arm}/scheduler.py",
        )
    )
    runtime_closure = closure_digest(materialized_inventory)
    scheduler_bytes = (runtime / "scheduler.py").read_bytes()
    entry_bytes = entry_path.read_bytes()
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "operation": OPERATION,
        "arm": arm,
        "checkout_head": checkout_head,
        "source": {
            "freeze_git_blob": before["freeze_git_blob"],
            "scheduler_git_blob": before["scheduler_git_blob"],
            "scheduler_sha256": before["scheduler_sha256"],
            "entrypoint_sha256": ENTRYPOINT_SHA256,
            "runtime_inventory": before["inventory"],
            "runtime_closure_sha256": before["closure_sha256"],
            "scenario_names": list(V2_SCENARIOS),
        },
        "materialized": {
            "runtime_inventory": materialized_inventory,
            "runtime_closure_sha256": runtime_closure,
            "scheduler_git_blob": git_blob_bytes(scheduler_bytes),
            "scheduler_sha256": sha256_bytes(scheduler_bytes),
            "changed_paths": changed,
            "scenario_names": list(after_names),
        },
        "entry": {
            "path": "entry.py",
            "bytes": len(entry_bytes),
            "sha256": sha256_bytes(entry_bytes),
            "runtime_closure_sha256": runtime_closure,
        },
        "patch": {
            "unified_diff": diff,
            "sha256": sha256_bytes(diff.encode("utf-8")),
        },
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with receipt_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return receipt
