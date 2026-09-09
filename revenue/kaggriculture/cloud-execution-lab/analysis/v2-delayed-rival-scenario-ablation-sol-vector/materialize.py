# SPDX-License-Identifier: Apache-2.0
"""Materialize a one-factor V2 delayed-rival-scenario ablation.

The frozen V2 tree is copied byte-for-byte. Exactly the two delayed rival
timing stress scenarios are removed from scheduler.py; every other behavior
and source byte remains bound and audited.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Any

EXPECTED_V2_SCHEDULER_BLOB = "7c068b7078c3d7c09bb3836590ad42b0af934cdf"
EXPECTED_V1_SCHEDULER_BLOB = "cbc502a92fe9d790cfaf763f6990d1057bc9b82d"
OPERATION = "titan-v2-delayed-rival-scenario-ablation-20260909-sol-vector-01"

BASE_SCENARIOS = (
    "    scenarios=[('no_rival',0,'paired'),('observed_paired',rival_quantity,'paired'),"
    "('observed_later_order',rival_quantity,'after')]\n"
)
OLD = (
    "    if end>now:\n"
    "        scenarios.append(('observed_next_turn',((now+1,rival_quantity),),'paired'))\n"
    "    if end>now+2:\n"
    "        scenarios.append(('observed_before_delayed_batch',((end-1,rival_quantity),),'paired'))\n"
)
NEW = (
    "    # SOL-VECTOR one-factor ablation: V1 timing scenarios only; all other V2 semantics retained.\n"
)

CARRY_SENTINEL = "            carry=float(self.single(inv,remaining)[0])\n"
RIVAL_MAPPING_SENTINEL = (
    "            r=(dict(rival).get(step,0) if isinstance(rival,tuple) "
    "else rival if step==self.now else 0)\n"
)
TARGET_SENTINEL = (
    "        targets={p:max(0,int(shed.get(p,0))) for p in PRODUCTS "
    "if shed.get(p,0)>0}\n"
)
FORCED_SENTINELS = (
    "    reference_feasible=(capacity_ok(reference) if capacity_ok else True) "
    "and dict(reference).get(now,0)>=minimum_now\n",
    "        if (key[0]>0 or not reference_feasible) and key>best_key:\n",
    "        'worst_relative_gain':best_key[0] if found_feasible else 0.0,"
    "'forced_feasibility':not reference_feasible and found_feasible,\n",
)


class MaterializeError(ValueError):
    """The frozen source or requested materialization is not exact."""


def git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def inventory(root: Path) -> dict[str, dict[str, Any]]:
    """Return a deterministic regular-file inventory and reject link tricks."""
    if not root.is_dir():
        raise MaterializeError(f"source is not a directory: {root}")
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise MaterializeError(f"non-regular member is forbidden: {relative}")
        data = path.read_bytes()
        result[relative] = {
            "bytes": len(data),
            "sha256": sha256(data),
            "git_blob_sha1": git_blob_sha1(data),
        }
    if not result:
        raise MaterializeError("source inventory is empty")
    return result


def closure_sha256(items: dict[str, dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for relative, record in sorted(items.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(record["sha256"]).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _count_exact(data: bytes, text: str, label: str, expected: int) -> None:
    actual = data.count(text.encode("utf-8"))
    if actual != expected:
        raise MaterializeError(
            f"{label} cardinality mismatch: expected {expected}, got {actual}"
        )


def verify_v2_semantics(data: bytes, *, patched: bool) -> dict[str, bool]:
    """Fail closed unless all non-ablated V2 policy factors are still exact."""
    _count_exact(data, BASE_SCENARIOS, "base scenario set", 1)
    _count_exact(data, OLD, "delayed-rival scenario bundle", 0 if patched else 1)
    _count_exact(data, NEW, "ablation marker", 1 if patched else 0)
    _count_exact(data, CARRY_SENTINEL, "V2 full continuation value", 1)
    _count_exact(data, RIVAL_MAPPING_SENTINEL, "V2 delayed-rival map support", 1)
    _count_exact(data, TARGET_SENTINEL, "V2 all-shed target domain", 1)
    for index, sentinel in enumerate(FORCED_SENTINELS):
        _count_exact(data, sentinel, f"V2 forced-feasibility sentinel {index}", 1)

    for scenario in ("observed_next_turn", "observed_before_delayed_batch"):
        _count_exact(
            data,
            scenario,
            f"{scenario} name",
            0 if patched else 1,
        )
    if b"carry=.95*self.single(inv,remaining)[0]" in data:
        raise MaterializeError("V1 0.95 continuation factor leaked into the arm")
    return {
        "v2_full_continuation_value": True,
        "v2_all_shed_target_domain": True,
        "v2_forced_feasibility": True,
        "v2_rival_mapping_support": True,
        "v2_base_scenarios": True,
    }


def materialize(
    source: Path,
    output: Path,
    *,
    expected_scheduler_blob: str = EXPECTED_V2_SCHEDULER_BLOB,
) -> dict[str, Any]:
    """Copy *source* and remove only V2's two delayed-rival scenarios."""
    source = source.resolve()
    output = output.resolve()
    if output.exists():
        raise MaterializeError(f"output already exists: {output}")
    try:
        output.relative_to(source)
    except ValueError:
        pass
    else:
        raise MaterializeError("output may not be nested inside source")

    before = inventory(source)
    scheduler = source / "scheduler.py"
    if "scheduler.py" not in before or "candidate.py" not in before:
        raise MaterializeError("source is missing scheduler.py or candidate.py")

    original = scheduler.read_bytes()
    actual_blob = git_blob_sha1(original)
    if actual_blob != expected_scheduler_blob:
        raise MaterializeError(
            "frozen V2 scheduler blob mismatch: "
            f"expected {expected_scheduler_blob}, got {actual_blob}"
        )
    invariants = verify_v2_semantics(original, patched=False)

    shutil.copytree(source, output, symlinks=False)
    patched = original.replace(OLD.encode("utf-8"), NEW.encode("utf-8"), 1)
    verify_v2_semantics(patched, patched=True)
    try:
        compile(patched.decode("utf-8"), str(output / "scheduler.py"), "exec")
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise MaterializeError(f"patched scheduler does not compile: {exc}") from exc
    atomic_write(output / "scheduler.py", patched)

    after = inventory(output)
    if set(before) != set(after):
        raise MaterializeError("materialized file inventory differs from frozen V2")
    changed = [
        relative
        for relative in sorted(before)
        if before[relative]["sha256"] != after[relative]["sha256"]
    ]
    if changed != ["scheduler.py"]:
        raise MaterializeError(f"one-factor boundary violated: changed={changed!r}")
    if scheduler.read_bytes() != original:
        raise MaterializeError("source scheduler changed during materialization")
    if inventory(source) != before:
        raise MaterializeError("frozen source tree changed during materialization")

    diff = "".join(
        difflib.unified_diff(
            original.decode("utf-8").splitlines(keepends=True),
            patched.decode("utf-8").splitlines(keepends=True),
            fromfile="v2/scheduler.py",
            tofile="v2-no-delayed-rival-scenarios/scheduler.py",
            n=3,
        )
    )
    return {
        "schema_version": 1,
        "operation": OPERATION,
        "source": {
            "scheduler_git_blob_sha1": actual_blob,
            "scheduler_sha256": sha256(original),
            "closure_sha256": closure_sha256(before),
            "files": len(before),
        },
        "ablation": {
            "factor": "delayed_rival_timing_stress_scenarios",
            "changed_files": changed,
            "scheduler_git_blob_sha1": git_blob_sha1(patched),
            "scheduler_sha256": sha256(patched),
            "closure_sha256": closure_sha256(after),
            "removed_scenarios": [
                "observed_next_turn",
                "observed_before_delayed_batch",
            ],
            "retained_scenarios": [
                "no_rival",
                "observed_paired",
                "observed_later_order",
            ],
            "retained_invariants": invariants,
            "old_occurrences_before": original.count(OLD.encode("utf-8")),
            "old_occurrences_after": patched.count(OLD.encode("utf-8")),
            "new_occurrences_before": original.count(NEW.encode("utf-8")),
            "new_occurrences_after": patched.count(NEW.encode("utf-8")),
            "unified_diff": diff,
        },
        "frozen_v1_scheduler_git_blob_sha1": EXPECTED_V1_SCHEDULER_BLOB,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize(args.source, args.output)
    atomic_write(
        args.receipt,
        (json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
            "utf-8"
        ),
    )
    print(
        json.dumps(
            {
                "source_blob": receipt["source"]["scheduler_git_blob_sha1"],
                "patched_blob": receipt["ablation"]["scheduler_git_blob_sha1"],
                "changed_files": receipt["ablation"]["changed_files"],
                "removed_scenarios": receipt["ablation"]["removed_scenarios"],
                "source_closure": receipt["source"]["closure_sha256"],
                "patched_closure": receipt["ablation"]["closure_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
