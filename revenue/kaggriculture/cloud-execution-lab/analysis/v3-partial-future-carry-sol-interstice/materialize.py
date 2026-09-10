# SPDX-License-Identifier: Apache-2.0
"""Materialize a bounded minimum-capacity liquidation successor over frozen V2.

The frozen runtime is copied byte-for-byte, then exact scheduler blocks are
replaced in the temporary copy.  The source tree is never mutated.  The repair
adds one missing policy representation: when capacity makes the reference plan
infeasible, sell the least feasible future quantity and retain the remainder as
continuation inventory.  Scheduled rows are consumed exactly once.
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

OPERATION = "titan-v3-partial-future-carry-20260909-sol-interstice-01"
EXPECTED_V2_SCHEDULER_BLOB = "7c068b7078c3d7c09bb3836590ad42b0af934cdf"
EXPECTED_V2_SCHEDULER_SHA256 = (
    "72865b83e66d0c1ed27ddc35e5ab428f8212872e8e8e918f2826eb7665fbe7f8"
)
EXPECTED_V1_SCHEDULER_BLOB = "cbc502a92fe9d790cfaf763f6990d1057bc9b82d"
EXPECTED_CANDIDATE_ENTRY_SHA256 = (
    "2e4897fb3aa8b0bee3e97709808c3aa25fa5055bcf5ce7d433b493eb334870f2"
)
EXPECTED_PATCHED_SCHEDULER_BLOB = "e487c208fd9ca12bb34d79936d3cc3f0643c71d5"
EXPECTED_PATCHED_SCHEDULER_SHA256 = (
    "70c1d3aae2ff3d27123621a233bdaf3306ffb0b758c7922e7f28b7c385d67780"
)

HELPERS_OLD = (
    "        return own_cash+carry-other_cash, own_cash,other_cash,remaining\n"
    "\n\n"
    "def optimize_lot(*,item,quantity,inventory,params,shops,config,now,dates,\n"
    "                 reference,rival_quantity,minimum_now=0,capacity_ok=None,last=718):\n"
)
HELPERS_NEW = '''        return own_cash+carry-other_cash, own_cash,other_cash,remaining


def _minimum_partial_future_plan(*, now, first, date, remaining, capacity_ok):
    """Return the least later sale that repairs feasibility while retaining carry.

    The supplied predicate includes both shed-capacity and executable-market-slot
    constraints, so it is intentionally treated as an arbitrary predicate rather
    than assumed monotone.  A bounded linear scan is exact for the game-wide
    quantity limit (shed capacity is at most 100 in the pinned configuration).
    The full-liquidation plan is already in the legacy candidate family; this
    helper contributes only a genuinely partial future sale.
    """
    if capacity_ok is None or remaining <= 1:
        return None
    carry_plan=((now,first),)
    if capacity_ok(carry_plan):
        return None
    for later in range(1,remaining):
        plan=((now,first),(date,later))
        if capacity_ok(plan):
            return plan
    return None


def _consume_due_plans(planned, now):
    """Return one-shot quantities due now and only strictly future rows."""
    due={}
    future={}
    for item,rows in planned.items():
        due[item]=sum(q for t,q in rows if t<=now)
        later=[(t,q) for t,q in rows if t>now]
        if later:
            future[item]=later
    return due,future


def optimize_lot(*,item,quantity,inventory,params,shops,config,now,dates,
                 reference,rival_quantity,minimum_now=0,capacity_ok=None,last=718):
'''

FAMILY_OLD = '''    candidates={tuple(reference)}
    future=dates[1:]
    for first in range(minimum_now,quantity+1):
        remaining=quantity-first
        candidates.add(((now,first),))  # Explicit carry beyond short horizon.
        for date in future:
            candidates.add(((now,first),(date,remaining)))
        if len(future)>=2:
            for share in (1,2,3):
                a=remaining*share//4
                candidates.add(((now,first),(future[0],a),(future[-1],remaining-a)))
    # Enumerates every legal first quantity and a bounded later-tranche family.
'''
FAMILY_NEW = '''    candidates={tuple(reference)}
    future=dates[1:]
    boundary_plans=[]
    for first in range(minimum_now,quantity+1):
        remaining=quantity-first
        candidates.add(((now,first),))  # Explicit carry beyond short horizon.
        for date in future:
            candidates.add(((now,first),(date,remaining)))
            # The predecessor had no representation for "sell only enough later
            # to make room, then retain the rest".  Add at most one exact
            # capacity-boundary plan per future date, and only when the reference
            # itself is infeasible.  Keeping first at minimum_now bounds the
            # family while preserving any required immediate cash sale.
            if not reference_feasible and first==minimum_now:
                boundary=_minimum_partial_future_plan(
                    now=now,first=first,date=date,remaining=remaining,
                    capacity_ok=capacity_ok)
                if boundary is not None:
                    candidates.add(boundary);boundary_plans.append(boundary)
        if len(future)>=2:
            for share in (1,2,3):
                a=remaining*share//4
                candidates.add(((now,first),(future[0],a),(future[-1],remaining-a)))
    # Enumerates every legal first quantity and a bounded later-tranche family.
'''

RANK_OLD = '''        # Require improvement in every explicit scenario; ties preserve reference.
        if (key[0]>0 or not reference_feasible) and key>best_key:
            best_key,best_plan,best_scores=key,plan,scores
            found_feasible=True
    return best_plan,{'item':item,'quantity':quantity,'rival_scenario_quantity':rival_quantity,
'''
RANK_NEW = '''        # Require improvement in every explicit scenario; ties preserve reference.
        # When the reference is infeasible, equal-value repairs choose the least
        # liquidation explicitly instead of inheriting the all-or-carry basis.
        better=key>best_key
        if not better and not reference_feasible and key==best_key:
            better=sum(q for _,q in plan)<sum(q for _,q in best_plan)
        if (key[0]>0 or not reference_feasible) and better:
            best_key,best_plan,best_scores=key,plan,scores
            found_feasible=True
    selected_sold=sum(q for _,q in best_plan)
    return best_plan,{'item':item,'quantity':quantity,'rival_scenario_quantity':rival_quantity,
'''

DIAGNOSTICS_OLD = '''        'worst_relative_gain':best_key[0] if found_feasible else 0.0,'forced_feasibility':not reference_feasible and found_feasible,
        'feasible':found_feasible,'plans_evaluated':len(candidates)}
'''
DIAGNOSTICS_NEW = '''        'worst_relative_gain':best_key[0] if found_feasible else 0.0,'forced_feasibility':not reference_feasible and found_feasible,
        'feasible':found_feasible,'plans_evaluated':len(candidates),
        'capacity_boundary_plans':[list(plan) for plan in boundary_plans],
        'selected_units_sold':selected_sold,'selected_units_carried':quantity-selected_sold}
'''

PLANNED_OLD = '''        targets={p:max(0,int(shed.get(p,0))) for p in PRODUCTS if shed.get(p,0)>0}
        current={p:min(targets[p],baseline_q.get(p,0)+sum(q for t,q in self.planned.get(p,[]) if t<=now)) for p in targets}
        budget=self.cash_reserve(obs,config,base,end)
'''
PLANNED_NEW = '''        targets={p:max(0,int(shed.get(p,0))) for p in PRODUCTS if shed.get(p,0)>0}
        # Scheduled tranches are one-shot obligations.  Snapshot quantities due
        # now, then retire every past/due row before replanning so an intentional
        # carried remainder cannot replay yesterday's tranche on the next turn.
        due_planned,self.planned=_consume_due_plans(self.planned,now)
        current={p:min(targets[p],baseline_q.get(p,0)+due_planned.get(p,0)) for p in targets}
        budget=self.cash_reserve(obs,config,base,end)
'''

PATCHES = (
    ("minimum-partial-future-and-one-shot-helpers", HELPERS_OLD, HELPERS_NEW),
    ("capacity-boundary-candidate-family", FAMILY_OLD, FAMILY_NEW),
    ("least-liquidation-forced-tie-break", RANK_OLD, RANK_NEW),
    ("selected-carry-diagnostics", DIAGNOSTICS_OLD, DIAGNOSTICS_NEW),
    ("consume-scheduled-tranches-once", PLANNED_OLD, PLANNED_NEW),
)

PRESERVED_MARKERS = {
    "forced_feasibility_admission": (
        "            eligible=info['worst_relative_gain']>0 or "
        "info.get('forced_feasibility',False)\n"
    ),
    "forced_feasibility_priority": (
        "            rank=(info.get('forced_feasibility',False),"
        "info['worst_relative_gain'])\n"
    ),
    "all_shed_target_domain": (
        "        targets={p:max(0,int(shed.get(p,0))) for p in PRODUCTS "
        "if shed.get(p,0)>0}\n"
    ),
    "next_turn_rival_scenario": (
        "        scenarios.append(('observed_next_turn',"
        "((now+1,rival_quantity),),'paired'))\n"
    ),
    "delayed_rival_scenario": (
        "        scenarios.append(('observed_before_delayed_batch',"
        "((end-1,rival_quantity),),'paired'))\n"
    ),
    "full_continuation_value": (
        "            carry=float(self.single(inv,remaining)[0])\n"
    ),
    "per_index_queue_rewrite": "        for raw in out['market']:\n",
}


class MaterializeError(ValueError):
    """Frozen-source custody or an exact patch contract failed."""


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
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            raise MaterializeError(f"generated Python cache is forbidden: {relative}")
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


def _marker_counts(data: bytes) -> dict[str, int]:
    return {
        name: data.count(marker.encode("utf-8"))
        for name, marker in PRESERVED_MARKERS.items()
    }


def _require_markers(data: bytes, *, label: str) -> dict[str, int]:
    counts = _marker_counts(data)
    wrong = {name: count for name, count in counts.items() if count != 1}
    if wrong:
        raise MaterializeError(
            f"{label} does not retain each named V2 feature exactly once: {wrong}"
        )
    return counts


def _apply_exact_patches(original: bytes) -> tuple[bytes, list[dict[str, Any]]]:
    current = original
    records: list[dict[str, Any]] = []
    for label, old_text, new_text in PATCHES:
        old = old_text.encode("utf-8")
        new = new_text.encode("utf-8")
        old_before = current.count(old)
        new_before = current.count(new)
        if old_before != 1:
            raise MaterializeError(
                f"{label}: expected one old block, found {old_before}"
            )
        if new_before != 0:
            raise MaterializeError(f"{label}: replacement already present")
        current = current.replace(old, new, 1)
        old_after = current.count(old)
        new_after = current.count(new)
        if old_after != 0 or new_after != 1:
            raise MaterializeError(
                f"{label}: replacement cardinality invalid: "
                f"old_after={old_after}, new_after={new_after}"
            )
        records.append(
            {
                "label": label,
                "old_occurrences_before": old_before,
                "old_occurrences_after": old_after,
                "new_occurrences_before": new_before,
                "new_occurrences_after": new_after,
                "old_sha256": sha256(old),
                "new_sha256": sha256(new),
            }
        )
    return current, records


def materialize(source: Path, output: Path) -> dict[str, Any]:
    source = Path(source).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise MaterializeError(f"output already exists: {output}")
    try:
        output.relative_to(source)
    except ValueError:
        pass
    else:
        raise MaterializeError("output may not be nested inside source")

    before = inventory(source)
    if "scheduler.py" not in before or "candidate.py" not in before:
        raise MaterializeError("source is missing scheduler.py or candidate.py")
    original = (source / "scheduler.py").read_bytes()
    if git_blob_sha1(original) != EXPECTED_V2_SCHEDULER_BLOB:
        raise MaterializeError(
            "frozen V2 scheduler blob mismatch: "
            f"expected {EXPECTED_V2_SCHEDULER_BLOB}, got {git_blob_sha1(original)}"
        )
    if sha256(original) != EXPECTED_V2_SCHEDULER_SHA256:
        raise MaterializeError("frozen V2 scheduler SHA-256 mismatch")
    if before["candidate.py"]["sha256"] != EXPECTED_CANDIDATE_ENTRY_SHA256:
        raise MaterializeError("frozen V2 candidate entry drift")
    source_markers = _require_markers(original, label="frozen V2")

    patched, patch_records = _apply_exact_patches(original)
    try:
        compile(patched.decode("utf-8"), str(output / "scheduler.py"), "exec")
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise MaterializeError(f"patched scheduler does not compile: {exc}") from exc
    if git_blob_sha1(patched) != EXPECTED_PATCHED_SCHEDULER_BLOB:
        raise MaterializeError(
            "patched scheduler blob mismatch: "
            f"expected {EXPECTED_PATCHED_SCHEDULER_BLOB}, got {git_blob_sha1(patched)}"
        )
    if sha256(patched) != EXPECTED_PATCHED_SCHEDULER_SHA256:
        raise MaterializeError("patched scheduler SHA-256 mismatch")

    shutil.copytree(source, output, symlinks=False)
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
        raise MaterializeError(f"scheduler-only boundary violated: changed={changed!r}")
    if inventory(source) != before:
        raise MaterializeError("frozen source tree changed during materialization")
    patched_markers = _require_markers(patched, label="materialized successor")
    if patched_markers != source_markers:
        raise MaterializeError("a preserved V2 marker changed cardinality")

    diff = "".join(
        difflib.unified_diff(
            original.decode("utf-8").splitlines(keepends=True),
            patched.decode("utf-8").splitlines(keepends=True),
            fromfile="v2/scheduler.py",
            tofile="v3-partial-future-carry/scheduler.py",
            n=3,
        )
    )
    return {
        "schema_version": 1,
        "operation": OPERATION,
        "source": {
            "scheduler_git_blob_sha1": EXPECTED_V2_SCHEDULER_BLOB,
            "scheduler_sha256": EXPECTED_V2_SCHEDULER_SHA256,
            "candidate_entry_sha256": EXPECTED_CANDIDATE_ENTRY_SHA256,
            "closure_sha256": closure_sha256(before),
            "files": len(before),
        },
        "candidate": {
            "kind": "minimum_partial_future_capacity_repair",
            "changed_files": changed,
            "scheduler_git_blob_sha1": git_blob_sha1(patched),
            "scheduler_sha256": sha256(patched),
            "closure_sha256": closure_sha256(after),
            "patches": patch_records,
            "preserved_v2_markers": {
                name: True for name in PRESERVED_MARKERS
            },
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
                "operation": OPERATION,
                "source_blob": receipt["source"]["scheduler_git_blob_sha1"],
                "candidate_blob": receipt["candidate"]["scheduler_git_blob_sha1"],
                "changed_files": receipt["candidate"]["changed_files"],
                "source_closure": receipt["source"]["closure_sha256"],
                "candidate_closure": receipt["candidate"]["closure_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
