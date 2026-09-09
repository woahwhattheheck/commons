# SPDX-License-Identifier: Apache-2.0
"""Materialize an executable-prefix capacity repair over frozen Titan V2.

The source tree is copied twice: one byte-exact control and one scheduler-only
candidate. Each copy receives a generated entrypoint that verifies every
underlying source byte before importing the agent. Frozen inputs are never
modified.
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
from typing import Any, Mapping

OPERATION = "titan-v2-market-hole-capacity-20260909-sol-parapet-01"
EXPECTED_V2_SCHEDULER_BLOB = "7c068b7078c3d7c09bb3836590ad42b0af934cdf"
EXPECTED_V2_SCHEDULER_SHA256 = (
    "72865b83e66d0c1ed27ddc35e5ab428f8212872e8e8e918f2826eb7665fbe7f8"
)
EXPECTED_V1_SCHEDULER_BLOB = "cbc502a92fe9d790cfaf763f6990d1057bc9b82d"
ENTRYPOINT = "sol_parapet_entry.py"

OLD_FEASIBILITY = (
    "                    if len(orders)>=int(config.get('maxMarketOrdersPerTurn',10)):\n"
    "                        offered=sum(max(0,int(o[2])) for o in orders if o and o[0]=='SELL' and o[1]==item)\n"
    "                        if q>offered:return False\n"
)
NEW_FEASIBILITY = (
    "                    limit=int(config.get('maxMarketOrdersPerTurn',10))\n"
    "                    executable=orders[:limit]\n"
    "                    offered=sum(max(0,int(o[2])) for o in executable if o and o[0]=='SELL' and o[1]==item)\n"
    "                    if q>offered and len(orders)>=limit and not any(not o for o in executable):return False\n"
)

OLD_REWRITE = (
    "        out=copy.deepcopy(base);market=[];remaining=dict(current)\n"
    "        available=dict(shed)\n"
    "        # Preserve every original order index, including withheld SELL positions.\n"
    "        # Extra stock is offered only after inherited orders: never consolidate a\n"
    "        # later SELL ahead of a cash-dependent purchase or shift its rival pairing.\n"
    "        for raw in out['market']:\n"
    "            o=list(raw)\n"
    "            if o and o[0]=='SELL' and len(o)>2 and o[1] in targets:\n"
    "                item=o[1]\n"
    "                q=min(max(0,int(o[2])),remaining.get(item,0),max(0,available.get(item,0)))\n"
    "                remaining[item]=remaining.get(item,0)-q;available[item]=available.get(item,0)-q\n"
    "                market.append(['SELL',item,q] if q else [])\n"
    "            else:market.append(o)\n"
    "        for item in sorted(targets):\n"
    "            q=min(remaining.get(item,0),max(0,available.get(item,0)))\n"
    "            if q>0 and len(market)<int(config.get('maxMarketOrdersPerTurn',10)):\n"
    "                market.append(['SELL',item,q]);available[item]=available.get(item,0)-q\n"
    "        out['market']=market\n"
)
NEW_REWRITE = (
    "        out=copy.deepcopy(base);market=[];remaining=dict(current)\n"
    "        available=dict(shed);limit=int(config.get('maxMarketOrdersPerTurn',10))\n"
    "        # Preserve every live inherited row at its original index. Only rows in\n"
    "        # the official executable prefix can consume planned stock. A falsy\n"
    "        # executable row is reusable capacity; inactive suffix rows stay inert.\n"
    "        for index,raw in enumerate(out['market']):\n"
    "            o=list(raw)\n"
    "            if index<limit and o and o[0]=='SELL' and len(o)>2 and o[1] in targets:\n"
    "                item=o[1]\n"
    "                q=min(max(0,int(o[2])),remaining.get(item,0),max(0,available.get(item,0)))\n"
    "                remaining[item]=remaining.get(item,0)-q;available[item]=available.get(item,0)-q\n"
    "                market.append(['SELL',item,q] if q else [])\n"
    "            else:market.append(o)\n"
    "        for item in sorted(targets):\n"
    "            q=min(remaining.get(item,0),max(0,available.get(item,0)))\n"
    "            if q>0:\n"
    "                hole=next((index for index,o in enumerate(market[:limit]) if not o),None)\n"
    "                if hole is not None:\n"
    "                    market[hole]=['SELL',item,q];available[item]=available.get(item,0)-q\n"
    "                elif len(market)<limit:\n"
    "                    market.append(['SELL',item,q]);available[item]=available.get(item,0)-q\n"
    "        out['market']=market\n"
)

OLD_PENDING = (
    "            sold=sum(o[2] for o in out['market'] if o and o[0]=='SELL' and o[1]==item)\n"
)
NEW_PENDING = (
    "            sold=sum(o[2] for o in out['market'][:limit] if o and o[0]=='SELL' and o[1]==item)\n"
)

REPLACEMENTS = {
    "capacity_admission": (OLD_FEASIBILITY, NEW_FEASIBILITY),
    "prefix_allocation_and_hole_reuse": (OLD_REWRITE, NEW_REWRITE),
    "pending_from_executable_prefix": (OLD_PENDING, NEW_PENDING),
}

PRESERVED_V2_MARKERS = {
    "all_shed_target_domain": (
        "        targets={p:max(0,int(shed.get(p,0))) for p in PRODUCTS if shed.get(p,0)>0}\n"
    ),
    "next_turn_rival_scenario": (
        "        scenarios.append(('observed_next_turn',((now+1,rival_quantity),),'paired'))\n"
    ),
    "delayed_rival_scenario": (
        "        scenarios.append(('observed_before_delayed_batch',((end-1,rival_quantity),),'paired'))\n"
    ),
    "full_continuation_value": "            carry=float(self.single(inv,remaining)[0])\n",
    "forced_feasibility_rank": (
        "            rank=(info.get('forced_feasibility',False),info['worst_relative_gain'])\n"
    ),
}


class MaterializeError(ValueError):
    """The source closure or requested one-factor rewrite is not exact."""


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


def inventory(root: Path, *, exclude_entrypoint: bool = False) -> dict[str, dict[str, Any]]:
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
        if exclude_entrypoint and relative == ENTRYPOINT:
            continue
        data = path.read_bytes()
        result[relative] = {
            "bytes": len(data),
            "sha256": sha256(data),
            "git_blob_sha1": git_blob_sha1(data),
        }
    if not result:
        raise MaterializeError("source inventory is empty")
    return result


def closure_sha256(items: Mapping[str, Mapping[str, Any]]) -> str:
    digest_value = hashlib.sha256()
    for relative, record in sorted(items.items()):
        digest_value.update(relative.encode("utf-8"))
        digest_value.update(b"\0")
        digest_value.update(str(record["bytes"]).encode("ascii"))
        digest_value.update(b"\0")
        digest_value.update(str(record["sha256"]).encode("ascii"))
        digest_value.update(b"\0")
    return digest_value.hexdigest()


def _require_markers(data: bytes, label: str) -> dict[str, int]:
    counts = {
        name: data.count(marker.encode("utf-8"))
        for name, marker in PRESERVED_V2_MARKERS.items()
    }
    wrong = {name: count for name, count in counts.items() if count != 1}
    if wrong:
        raise MaterializeError(f"{label} preserved-marker cardinality drift: {wrong}")
    return counts


def patch_scheduler(original: bytes) -> tuple[bytes, dict[str, dict[str, int]]]:
    patched = original
    counts: dict[str, dict[str, int]] = {}
    for name, (old_text, new_text) in REPLACEMENTS.items():
        old = old_text.encode("utf-8")
        new = new_text.encode("utf-8")
        before_old = patched.count(old)
        before_new = patched.count(new)
        if before_old != 1 or before_new != 0:
            raise MaterializeError(
                f"{name} anchor mismatch: old={before_old}, new={before_new}"
            )
        patched = patched.replace(old, new, 1)
        counts[name] = {
            "old_before": before_old,
            "old_after": patched.count(old),
            "new_before": before_new,
            "new_after": patched.count(new),
        }
    try:
        compile(patched.decode("utf-8"), "scheduler.py", "exec")
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise MaterializeError(f"patched scheduler does not compile: {exc}") from exc
    return patched, counts


def render_entrypoint(files: Mapping[str, Mapping[str, Any]], label: str) -> bytes:
    expected = {name: record["sha256"] for name, record in sorted(files.items())}
    module_name = "_sol_parapet_" + label + "_" + closure_sha256(files)[:16]
    source = f'''# SPDX-License-Identifier: Apache-2.0
"""Generated closure-verifying entrypoint; do not edit."""
from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path
import sys

EXPECTED_FILES = {json.dumps(expected, indent=4, sort_keys=True)}
MODULE_NAME = {module_name!r}
_ROOT = Path(__file__).resolve().parent
_AGENT = None


def _load():
    for relative, expected in EXPECTED_FILES.items():
        path = (_ROOT / relative).resolve()
        try:
            path.relative_to(_ROOT)
        except ValueError as exc:
            raise RuntimeError(f"closure path escaped root: {{relative}}") from exc
        if not path.is_file():
            raise RuntimeError(f"closure file missing: {{relative}}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(
                f"closure digest mismatch: {{relative}}: expected {{expected}}, got {{actual}}"
            )
    sys.path.insert(0, str(_ROOT))
    spec = importlib.util.spec_from_file_location(MODULE_NAME, _ROOT / "candidate.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot construct candidate import")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    function = getattr(module, "agent")
    if not callable(function):
        raise RuntimeError("candidate agent is not callable")
    return function


def agent(observation, configuration=None):
    global _AGENT
    if _AGENT is None:
        _AGENT = _load()
    return _AGENT(observation, configuration)
'''
    return source.encode("utf-8")


def _copy_closure(source: Path, output: Path) -> None:
    if output.exists():
        raise MaterializeError(f"output already exists: {output}")
    try:
        output.resolve().relative_to(source.resolve())
    except ValueError:
        pass
    else:
        raise MaterializeError("output may not be nested inside source")
    shutil.copytree(source, output, symlinks=False)


def materialize(
    source: Path,
    control_output: Path,
    candidate_output: Path,
    *,
    expected_scheduler_blob: str = EXPECTED_V2_SCHEDULER_BLOB,
    expected_scheduler_sha256: str | None = EXPECTED_V2_SCHEDULER_SHA256,
) -> dict[str, Any]:
    source = Path(source).resolve()
    control_output = Path(control_output).resolve()
    candidate_output = Path(candidate_output).resolve()
    if control_output == candidate_output:
        raise MaterializeError("control and candidate outputs must differ")

    before = inventory(source)
    scheduler = source / "scheduler.py"
    if "scheduler.py" not in before or "candidate.py" not in before:
        raise MaterializeError("source is missing scheduler.py or candidate.py")
    original = scheduler.read_bytes()
    actual_blob = git_blob_sha1(original)
    actual_sha256 = sha256(original)
    if actual_blob != expected_scheduler_blob:
        raise MaterializeError(
            f"frozen V2 scheduler blob mismatch: expected {expected_scheduler_blob}, got {actual_blob}"
        )
    if expected_scheduler_sha256 is not None and actual_sha256 != expected_scheduler_sha256:
        raise MaterializeError(
            "frozen V2 scheduler SHA-256 mismatch: "
            f"expected {expected_scheduler_sha256}, got {actual_sha256}"
        )
    source_markers = _require_markers(original, "frozen V2")
    patched, replacements = patch_scheduler(original)
    if _require_markers(patched, "patched V2") != source_markers:
        raise MaterializeError("a preserved V2 marker changed cardinality")

    _copy_closure(source, control_output)
    _copy_closure(source, candidate_output)
    atomic_write(candidate_output / "scheduler.py", patched)

    control_core = inventory(control_output)
    candidate_core = inventory(candidate_output)
    if set(control_core) != set(before) or set(candidate_core) != set(before):
        raise MaterializeError("copied closure file set drifted")
    changed = [
        name
        for name in sorted(before)
        if before[name]["sha256"] != candidate_core[name]["sha256"]
    ]
    if changed != ["scheduler.py"]:
        raise MaterializeError(f"one-factor boundary violated: changed={changed!r}")
    if control_core != before:
        raise MaterializeError("control closure is not byte-exact frozen V2")
    if inventory(source) != before or scheduler.read_bytes() != original:
        raise MaterializeError("frozen source changed during materialization")

    control_entry = render_entrypoint(control_core, "control")
    candidate_entry = render_entrypoint(candidate_core, "candidate")
    if control_entry == candidate_entry:
        raise MaterializeError("control and candidate entrypoints are not distinct")
    atomic_write(control_output / ENTRYPOINT, control_entry)
    atomic_write(candidate_output / ENTRYPOINT, candidate_entry)

    control_execution = inventory(control_output)
    candidate_execution = inventory(candidate_output)
    diff = "".join(
        difflib.unified_diff(
            original.decode("utf-8").splitlines(keepends=True),
            patched.decode("utf-8").splitlines(keepends=True),
            fromfile="frozen-v2/scheduler.py",
            tofile="market-hole-capacity/scheduler.py",
            n=3,
        )
    )
    return {
        "schema_version": 1,
        "operation": OPERATION,
        "kind": "executable_market_prefix_capacity",
        "source": {
            "scheduler_git_blob_sha1": actual_blob,
            "scheduler_sha256": actual_sha256,
            "closure_sha256": closure_sha256(before),
            "files": len(before),
        },
        "control": {
            "core_closure_sha256": closure_sha256(control_core),
            "execution_closure_sha256": closure_sha256(control_execution),
            "entrypoint": ENTRYPOINT,
            "entrypoint_sha256": sha256(control_entry),
            "entrypoint_git_blob_sha1": git_blob_sha1(control_entry),
        },
        "candidate": {
            "core_closure_sha256": closure_sha256(candidate_core),
            "execution_closure_sha256": closure_sha256(candidate_execution),
            "scheduler_sha256": sha256(patched),
            "scheduler_git_blob_sha1": git_blob_sha1(patched),
            "entrypoint": ENTRYPOINT,
            "entrypoint_sha256": sha256(candidate_entry),
            "entrypoint_git_blob_sha1": git_blob_sha1(candidate_entry),
        },
        "ablation": {
            "changed_files": changed,
            "replacements": replacements,
            "preserved_v2_markers": {name: True for name in PRESERVED_V2_MARKERS},
            "unified_diff": diff,
        },
        "frozen_v1_scheduler_git_blob_sha1": EXPECTED_V1_SCHEDULER_BLOB,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--control-output", type=Path, required=True)
    parser.add_argument("--candidate-output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize(args.source, args.control_output, args.candidate_output)
    atomic_write(
        args.receipt,
        (json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
            "utf-8"
        ),
    )
    print(
        json.dumps(
            {
                "operation": OPERATION,
                "source_scheduler_blob": receipt["source"]["scheduler_git_blob_sha1"],
                "candidate_scheduler_blob": receipt["candidate"]["scheduler_git_blob_sha1"],
                "control_entrypoint_sha256": receipt["control"]["entrypoint_sha256"],
                "candidate_entrypoint_sha256": receipt["candidate"]["entrypoint_sha256"],
                "changed_files": receipt["ablation"]["changed_files"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
