# SPDX-License-Identifier: Apache-2.0
"""Materialize a safety-preserving profit-first forced-feasibility selector.

Frozen V2 admits a non-positive plan when the reference is infeasible, but its
Boolean-first rank lets that forced repair outrank every profitable ordinary
candidate.  This adapter changes only the ranking key: positive-gain plans rank
ahead of non-positive forced plans; forced plans remain eligible as a last
resort when no profitable plan exists.

The exact frozen source tree is copied through the merged closure materializer.
No frozen, canonical, runtime, configuration, archive, pointer, provider, or
Kaggle path is mutated.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
BASE_MATERIALIZER = (
    HERE.parent / "v2-target-domain-ablation-sol-bulwark" / "materialize.py"
)

OPERATION = "titan-v2-profit-first-forced-fallback-20260909-sol-forge-01"
EXPECTED_BASE_MATERIALIZER_BLOB = "e7740bbd2f5ad71f565073445535d6941184288c"
EXPECTED_V2_SCHEDULER_BLOB = "7c068b7078c3d7c09bb3836590ad42b0af934cdf"
EXPECTED_V1_SCHEDULER_BLOB = "cbc502a92fe9d790cfaf763f6990d1057bc9b82d"

OLD = (
    "            eligible=info['worst_relative_gain']>0 or "
    "info.get('forced_feasibility',False)\n"
    "            rank=(info.get('forced_feasibility',False),"
    "info['worst_relative_gain'])\n"
    "            if eligible and (best is None or "
    "rank>(best[2].get('forced_feasibility',False),"
    "best[2]['worst_relative_gain'])):best=(item,plan,info)\n"
)
NEW = (
    "            eligible=info['worst_relative_gain']>0 or "
    "info.get('forced_feasibility',False)\n"
    "            rank=(info['worst_relative_gain']>0,"
    "info['worst_relative_gain'])\n"
    "            if eligible and (best is None or "
    "rank>(best[2]['worst_relative_gain']>0,"
    "best[2]['worst_relative_gain'])):best=(item,plan,info)\n"
)

PRESERVED_V2_MARKERS = {
    "forced_feasibility_admission": (
        "            eligible=info['worst_relative_gain']>0 or "
        "info.get('forced_feasibility',False)\n"
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

# Parent bind/comparison helpers intentionally retain this broad compatibility
# label.  The additional variant field below distinguishes the narrower policy.
COMPATIBLE_KIND = "forced_feasibility_admission_and_rank"
VARIANT = "profit_first_rank_with_forced_fallback"


class MaterializeError(ValueError):
    """The helper, frozen source, or requested priority transform is not exact."""


def git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _load_base() -> ModuleType:
    try:
        data = BASE_MATERIALIZER.read_bytes()
    except OSError as exc:
        raise MaterializeError(
            f"merged base materializer is unavailable: {BASE_MATERIALIZER}: {exc}"
        ) from exc
    actual = git_blob_sha1(data)
    if actual != EXPECTED_BASE_MATERIALIZER_BLOB:
        raise MaterializeError(
            "merged base materializer drift: "
            f"expected {EXPECTED_BASE_MATERIALIZER_BLOB}, got {actual}"
        )
    spec = importlib.util.spec_from_file_location(
        "_sol_forge_profit_first_base_materializer", BASE_MATERIALIZER
    )
    if spec is None or spec.loader is None:
        raise MaterializeError("cannot construct base materializer import")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _marker_counts(data: bytes) -> dict[str, int]:
    return {
        name: data.count(marker.encode("utf-8"))
        for name, marker in PRESERVED_V2_MARKERS.items()
    }


def _require_preserved_markers(data: bytes, *, label: str) -> dict[str, int]:
    counts = _marker_counts(data)
    wrong = {name: count for name, count in counts.items() if count != 1}
    if wrong:
        raise MaterializeError(
            f"{label} does not retain each named V2 feature exactly once: {wrong}"
        )
    return counts


def materialize(
    source: Path,
    output: Path,
    *,
    expected_scheduler_blob: str = EXPECTED_V2_SCHEDULER_BLOB,
) -> dict[str, Any]:
    """Copy frozen V2 and replace only the cross-product priority key."""
    source = Path(source)
    output = Path(output)
    scheduler = source / "scheduler.py"
    try:
        original = scheduler.read_bytes()
    except OSError as exc:
        raise MaterializeError(f"cannot read frozen V2 scheduler: {exc}") from exc

    if original.count(OLD.encode("utf-8")) != 1:
        raise MaterializeError("frozen V2 priority block cardinality is not one")
    if original.count(NEW.encode("utf-8")) != 0:
        raise MaterializeError("profit-first priority block already exists")
    source_marker_counts = _require_preserved_markers(original, label="frozen V2")

    base = _load_base()
    base.OLD = OLD
    base.NEW = NEW
    try:
        receipt = base.materialize(
            source,
            output,
            expected_scheduler_blob=expected_scheduler_blob,
        )
    except base.MaterializeError as exc:
        raise MaterializeError(str(exc)) from exc

    try:
        patched = (output / "scheduler.py").read_bytes()
    except OSError as exc:
        raise MaterializeError(f"cannot read materialized scheduler: {exc}") from exc
    patched_marker_counts = _require_preserved_markers(
        patched, label="materialized profit-first V2"
    )
    if source_marker_counts != patched_marker_counts:
        raise MaterializeError("a preserved V2 feature changed cardinality")
    if patched.count(OLD.encode("utf-8")) != 0:
        raise MaterializeError("frozen Boolean-first priority survived")
    if patched.count(NEW.encode("utf-8")) != 1:
        raise MaterializeError("profit-first priority cardinality is not one")

    diff = "".join(
        difflib.unified_diff(
            original.decode("utf-8").splitlines(keepends=True),
            patched.decode("utf-8").splitlines(keepends=True),
            fromfile="v2/scheduler.py",
            tofile="v2-profit-first-forced-fallback/scheduler.py",
            n=3,
        )
    )
    receipt["operation"] = OPERATION
    receipt["ablation"]["kind"] = COMPATIBLE_KIND
    receipt["ablation"]["variant"] = VARIANT
    receipt["ablation"]["preserved_v2_markers"] = {
        name: True for name in PRESERVED_V2_MARKERS
    }
    receipt["ablation"]["unified_diff"] = diff
    receipt["ablation"]["policy"] = {
        "eligible": "positive_gain or forced_feasibility",
        "rank": ["positive_gain", "worst_relative_gain"],
        "fallback": "highest-valued forced plan only when no positive plan exists",
    }
    receipt["base_materializer"] = {
        "path": BASE_MATERIALIZER.relative_to(HERE.parents[2]).as_posix(),
        "git_blob_sha1": EXPECTED_BASE_MATERIALIZER_BLOB,
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize(args.source, args.output)
    base = _load_base()
    base.atomic_write(
        args.receipt,
        (
            json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
        ).encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "operation": OPERATION,
                "variant": VARIANT,
                "source_blob": receipt["source"]["scheduler_git_blob_sha1"],
                "patched_blob": receipt["ablation"]["scheduler_git_blob_sha1"],
                "changed_files": receipt["ablation"]["changed_files"],
                "source_closure": receipt["source"]["closure_sha256"],
                "patched_closure": receipt["ablation"]["closure_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
