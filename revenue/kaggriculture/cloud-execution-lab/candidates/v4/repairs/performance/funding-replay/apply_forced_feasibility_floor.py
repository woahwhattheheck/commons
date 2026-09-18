# SPDX-License-Identifier: Apache-2.0
"""Source-bound current-ABI port of TITAN #12096's forced-feasibility floor.

This materializer is deliberately source-only. It reads the three current SELL
planning surfaces, verifies their exact Git blob identities, writes only caller-
chosen scratch outputs, and never mutates canonical runtime/config/COMPOSITION/
INTEGRATION/archive/Kaggle state.

The preserved theorem is narrow:
* a physically forced rescue must have nonnegative worst relative gain;
* it must also have nonnegative worst own-receipt gain;
* an ordinary accepted positive-gain candidate outranks a value-neutral forced
  rescue because ranking is gain-first, not forced-boolean-first.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXPECTED_BLOBS = {
    "scheduler": "fcfed4d59e17f211e6744e246e86167ea82a0b87",
    "selected_sell_core": "d460678b6504833e86e3f28ee30edc6dff13de83",
    "frozen_selected": "6a95505388ea1b5eba38bd1f927a2a2bf084490c",
}

# The missing historical scheduler postimages were independently reconstructed
# from the pinned V4 recipe before this current-ABI port was authored.
RECONSTRUCTED_SCHEDULER_EDGE = {
    "funding_capacity_output": "eb289f87adebb7dc7e90046bfbec31a307cb5aaa",
    "scoped_construction_output": "b29d1e9887f517506c5b3d858baa9bda5848e73f",
}


def git_blob(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one predecessor anchor, found {count}")
    if new in source:
        raise ValueError(f"{label}: successor already present")
    return source.replace(old, new, 1)


def _compile(source: str, label: str) -> str:
    compile(source, label, "exec")
    return source


def transform_scheduler(source: str) -> str:
    source = _replace_once(
        source,
        "    found_feasible=reference_feasible\n"
        "    candidates={tuple(reference)}\n",
        "    found_feasible=reference_feasible\n"
        "    physical_feasible_found=reference_feasible\n"
        "    economic_floor_rejections=0\n"
        "    candidates={tuple(reference)}\n",
        "scheduler state",
    )
    source = _replace_once(
        source,
        "        else:\n"
        "            if capacity_ok and not capacity_ok(plan):continue\n"
        "            scores=[model.score(plan,quantity,r,a,end==last) for _,r,a in scenarios]\n"
        "        deltas=[s[0]-b[0] for s,b in zip(scores,baseline)]\n"
        "        key=(round(min(deltas),8),round(sum(deltas),8),float(dict(plan).get(now,0)))\n"
        "        # Require improvement in every explicit scenario; ties preserve reference.\n"
        "        if (key[0]>0 or not reference_feasible) and key>best_key:\n"
        "            best_key,best_plan,best_scores=key,plan,scores\n"
        "            found_feasible=True\n",
        "        else:\n"
        "            if capacity_ok and not capacity_ok(plan):continue\n"
        "            physical_feasible_found=True\n"
        "            scores=[model.score(plan,quantity,r,a,end==last) for _,r,a in scenarios]\n"
        "        deltas=[s[0]-b[0] for s,b in zip(scores,baseline)]\n"
        "        own_deltas=[s[1]-b[1] for s,b in zip(scores,baseline)]\n"
        "        key=(round(min(deltas),8),round(sum(deltas),8),float(dict(plan).get(now,0)))\n"
        "        worst_own_gain=round(min(own_deltas),8)\n"
        "        economic_floor=(key[0]>0 if reference_feasible\n"
        "                        else key[0]>=0 and worst_own_gain>=0)\n"
        "        # Forced physical feasibility cannot waive the nonnegative own/relative floor.\n"
        "        if economic_floor and key>best_key:\n"
        "            best_key,best_plan,best_scores=key,plan,scores\n"
        "            found_feasible=True\n"
        "        elif not reference_feasible and not economic_floor:\n"
        "            economic_floor_rejections+=1\n",
        "scheduler economic floor",
    )
    source = _replace_once(
        source,
        "        'worst_relative_gain':best_key[0] if found_feasible else 0.0,'forced_feasibility':not reference_feasible and found_feasible,\n"
        "        'feasible':found_feasible,'plans_evaluated':len(candidates)}\n",
        "        'worst_relative_gain':best_key[0] if found_feasible else 0.0,\n"
        "        'worst_own_gain':round(min((s[1]-b[1] for s,b in zip(best_scores,baseline)),default=0.0),8) if found_feasible else 0.0,\n"
        "        'reference_feasible':reference_feasible,'physical_feasible_found':physical_feasible_found,\n"
        "        'economic_floor_rejections':economic_floor_rejections,\n"
        "        'forced_feasibility':not reference_feasible and found_feasible,\n"
        "        'feasible':found_feasible,'plans_evaluated':len(candidates)}\n",
        "scheduler receipt",
    )
    source = _replace_once(
        source,
        "            eligible=info['worst_relative_gain']>0 or info.get('forced_feasibility',False)\n"
        "            rank=(info.get('forced_feasibility',False),info['worst_relative_gain'])\n"
        "            if eligible and (best is None or rank>(best[2].get('forced_feasibility',False),best[2]['worst_relative_gain'])):best=(item,plan,info)\n",
        "            gain=float(info['worst_relative_gain'])\n"
        "            forced=bool(info.get('forced_feasibility',False))\n"
        "            own_gain=float(info.get('worst_own_gain',0.0))\n"
        "            eligible=((forced and gain>=0 and own_gain>=0) or (not forced and gain>0))\n"
        "            rank=(gain,forced)\n"
        "            prior=(-float('inf'),False) if best is None else (float(best[2]['worst_relative_gain']),bool(best[2].get('forced_feasibility',False)))\n"
        "            if eligible and rank>prior:best=(item,plan,info)\n",
        "scheduler caller rank",
    )
    return _compile(source, "titan_v4_forced_feasibility_scheduler")


def transform_selected_sell_core(source: str) -> str:
    source = _replace_once(
        source,
        "    found_feasible=reference_feasible\n"
        "    candidates={tuple(reference)}\n",
        "    found_feasible=reference_feasible\n"
        "    physical_feasible_found=reference_feasible\n"
        "    economic_floor_rejections=0\n"
        "    candidates={tuple(reference)}\n",
        "selected core state",
    )
    source = _replace_once(
        source,
        "            if capacity_ok and not capacity_ok(plan):continue\n"
        "            scores=[model.score(plan,quantity,r,a,end==last) for _,r,a in scenarios]\n"
        "            deltas=[s[0]-b[0] for s,b in zip(scores,baseline)]\n"
        "            key=(round(min(deltas),8),round(sum(deltas),8),float(dict(plan).get(now,0)))\n"
        "            if key>best_key:\n"
        "                best_key,best_plan,best_scores=key,plan,scores\n"
        "                found_feasible=True\n",
        "            if capacity_ok and not capacity_ok(plan):continue\n"
        "            physical_feasible_found=True\n"
        "            scores=[model.score(plan,quantity,r,a,end==last) for _,r,a in scenarios]\n"
        "            deltas=[s[0]-b[0] for s,b in zip(scores,baseline)]\n"
        "            own_deltas=[s[1]-b[1] for s,b in zip(scores,baseline)]\n"
        "            key=(round(min(deltas),8),round(sum(deltas),8),float(dict(plan).get(now,0)))\n"
        "            worst_own_gain=round(min(own_deltas),8)\n"
        "            if key[0]<0 or worst_own_gain<0:\n"
        "                economic_floor_rejections+=1\n"
        "                continue\n"
        "            if key>best_key:\n"
        "                best_key,best_plan,best_scores=key,plan,scores\n"
        "                found_feasible=True\n",
        "selected core forced floor",
    )
    source = _replace_once(
        source,
        "    forced=not reference_feasible and found_feasible\n"
        "    return best_plan,{'item':item,'quantity':quantity,'rival_scenario_quantity':rival_quantity,\n",
        "    chosen_own_deltas=[s[1]-b[1] for s,b in zip(best_scores,baseline)] if found_feasible else []\n"
        "    worst_own_gain=round(min(chosen_own_deltas),8) if chosen_own_deltas else 0.0\n"
        "    forced=not reference_feasible and found_feasible\n"
        "    return best_plan,{'item':item,'quantity':quantity,'rival_scenario_quantity':rival_quantity,\n",
        "selected core own receipt",
    )
    source = _replace_once(
        source,
        "        'worst_relative_gain':best_key[0] if found_feasible else 0.0,\n"
        "        'forced_feasibility':forced,'feasible':found_feasible,'plans_evaluated':len(candidates),\n",
        "        'worst_relative_gain':best_key[0] if found_feasible else 0.0,\n"
        "        'worst_own_gain':worst_own_gain,'reference_feasible':reference_feasible,\n"
        "        'physical_feasible_found':physical_feasible_found,\n"
        "        'economic_floor_rejections':economic_floor_rejections,\n"
        "        'forced_feasibility':forced,'feasible':found_feasible,'plans_evaluated':len(candidates),\n",
        "selected core receipt",
    )
    return _compile(source, "titan_v4_forced_feasibility_selected_core")


def transform_frozen_selected(source: str) -> str:
    source = _replace_once(
        source,
        "def seller_choice_rank(info):\n"
        "    \"\"\"Return active admission plus deterministic rank for one optimizer report.\"\"\"\n"
        "    forced=bool(info.get('forced_feasibility',False))\n"
        "    accepted=bool(info.get('accepted',float(info.get('worst_relative_gain',0.0))>0))\n"
        "    score=float(info.get('acceptance_score',info.get('worst_relative_gain',0.0)))\n"
        "    return forced or accepted,(forced,score)\n",
        "def seller_choice_rank(info):\n"
        "    \"\"\"Admit forced rescue only above its floor; rank economic gain first.\"\"\"\n"
        "    forced=bool(info.get('forced_feasibility',False))\n"
        "    gain=float(info.get('worst_relative_gain',0.0))\n"
        "    own_gain=float(info.get('worst_own_gain',0.0))\n"
        "    accepted=bool(info.get('accepted',gain>0))\n"
        "    score=float(info.get('acceptance_score',gain))\n"
        "    eligible=(forced and gain>=0 and own_gain>=0) or (not forced and accepted)\n"
        "    return eligible,(score,forced)\n",
        "frozen seller rank",
    )
    source = _replace_once(
        source,
        "                    rank=(False,independent)\n"
        "                    if best is None or rank>seller_choice_rank(best[2])[1]:\n",
        "                    rank=(independent,False)\n"
        "                    if best is None or rank>seller_choice_rank(best[2])[1]:\n",
        "frozen joint rank",
    )
    return _compile(source, "titan_v4_forced_feasibility_frozen")


TRANSFORMS = {
    "scheduler": transform_scheduler,
    "selected_sell_core": transform_selected_sell_core,
    "frozen_selected": transform_frozen_selected,
}


def materialize(kind: str, source_path: Path, output_path: Path) -> dict[str, str]:
    raw = source_path.read_bytes()
    observed = git_blob(raw)
    expected = EXPECTED_BLOBS[kind]
    if observed != expected:
        raise ValueError(f"{kind}: source Git blob drifted: {observed} != {expected}")
    source = raw.decode("utf-8")
    repaired = TRANSFORMS[kind](source)
    output = repaired.encode("utf-8")
    if output_path.exists():
        raise FileExistsError(str(output_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)
    reread = output_path.read_bytes()
    if reread != output:
        raise IOError(f"{kind}: scratch output readback mismatch")
    return {"input_git_blob": observed, "output_git_blob": git_blob(output)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--scheduler", type=Path, required=True)
    p.add_argument("--selected-core", type=Path, required=True)
    p.add_argument("--frozen", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args(argv)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError("output directory must be new or empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = {
        "scheduler": materialize("scheduler", args.scheduler, args.output_dir / "scheduler.py"),
        "selected_sell_core": materialize(
            "selected_sell_core", args.selected_core, args.output_dir / "selected_sell_core.py"
        ),
        "frozen_selected": materialize(
            "frozen_selected", args.frozen, args.output_dir / "frozen_selected.py"
        ),
    }
    for name, row in rows.items():
        print(name, row["input_git_blob"], "->", row["output_git_blob"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
