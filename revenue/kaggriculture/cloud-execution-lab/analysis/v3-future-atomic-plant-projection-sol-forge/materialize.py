#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize the current TITAN scheduler with official future PLANT semantics.

This tool is deliberately disconnected from the canonical runtime.  It verifies the
exact current scheduler and engine Git blobs, replaces two source-local preimages,
and writes a candidate scheduler plus a deterministic receipt.  The source file is
never edited in place.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
DEFAULT_SOURCE = LAB / "scheduler.py"
DEFAULT_ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"

BASE_MAIN = "3854f1cc46340f5099ade910e2cfc7b36606425e"
BASE_SCHEDULER_GIT_BLOB = "a483b24dd72b580d7d8811636b54d2d44f391575"
OFFICIAL_ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
SCHEMA = "titan-v3-future-atomic-plant-projection-materializer-v1"

OLD_POST_UNITS = '''def post_units(obs, action, config, *, shed_capacity=None):
    """Exact deterministic engine unit stage on the player's observed farm."""
    farm = detached_json_value(obs['farms'][obs['player']])
    private = detached_json_value(obs['private'])
    acts = [action.get('farmer',['PASS']), *action.get('hands',[])]
    demand = {}
    for a in acts:
        if a and a[0]=='PLANT' and len(a)>1:
            demand[a[1]]=demand.get(a[1],0)+1
    blocked={p for p,n in demand.items() if n>private['seeds'].get(p,0)}
    capacity=int(config.get('shedCapacity',100)) if shed_capacity is None else int(shed_capacity)
    for i,a in enumerate(acts):
        if a and a[0]=='PLANT' and a[1] in blocked:a=['PASS']
        m._apply_unit_action(farm,private,i,a,len(farm['tiles']),int(obs['step'])//int(config.get('turnsPerDay',24)),int(config.get('turnsPerDay',24)),capacity)
    return farm, private
'''

NEW_POST_UNITS = '''def _apply_unit_packet(farm, private, action, *, board_size, day,
                       turns_per_day, shed_capacity):
    """Apply one farmer+hands packet with official atomic PLANT admission.

    The interpreter counts every same-crop PLANT request before any actor moves.
    If demand exceeds the packet's starting seed stock, every request for that
    crop becomes PASS.  Other actions retain their original actor order.
    """
    packet=action if isinstance(action,dict) else {}
    farmer_action=packet.get('farmer',['PASS'])
    hands_actions=packet.get('hands',[])
    if not isinstance(hands_actions,list):hands_actions=[]
    acts=[farmer_action,*hands_actions]
    demand={}
    for a in acts:
        if isinstance(a,list) and len(a)>=2 and a[0]=='PLANT':
            demand[a[1]]=demand.get(a[1],0)+1
    seeds=private.get('seeds',{}) if hasattr(private,'get') else {}
    blocked={crop for crop,n in demand.items() if n>seeds.get(crop,0)}
    for i,a in enumerate(acts):
        if isinstance(a,list) and len(a)>=2 and a[0]=='PLANT' and a[1] in blocked:
            a=['PASS']
        m._apply_unit_action(farm,private,i,a,board_size,day,turns_per_day,shed_capacity)
    return blocked


def post_units(obs, action, config, *, shed_capacity=None):
    """Exact deterministic engine unit stage on the player's observed farm."""
    farm = detached_json_value(obs['farms'][obs['player']])
    private = detached_json_value(obs['private'])
    turns_per_day=max(1,int(config.get('turnsPerDay',24)))
    capacity=int(config.get('shedCapacity',100)) if shed_capacity is None else int(shed_capacity)
    _apply_unit_packet(farm,private,action,
        board_size=len(farm['tiles']),day=int(obs['step'])//turns_per_day,
        turns_per_day=turns_per_day,shed_capacity=capacity)
    return farm, private
'''

OLD_FUTURE_PACKET = '''            if t>now:
                act=route[t] if t<len(route) else parent.PASS
                acts=[act.get('farmer',['PASS']),*act.get('hands',[])]
                for i,a in enumerate(acts):
                    m._apply_unit_action(f,p,i,a,len(f['tiles']),t//24,24,10**6)
'''

NEW_FUTURE_PACKET = '''            if t>now:
                act=route[t] if t<len(route) else parent.PASS
                _apply_unit_packet(f,p,act,
                    board_size=len(f['tiles']),day=t//24,turns_per_day=24,
                    shed_capacity=10**6)
'''


def git_blob(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} preimage count is {count}, expected exactly 1")
    return text.replace(old, new, 1)


def materialize(
    source: Path,
    engine: Path,
    output: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    source_bytes = source.read_bytes()
    engine_bytes = engine.read_bytes()
    if git_blob(source_bytes) != BASE_SCHEDULER_GIT_BLOB:
        raise RuntimeError(
            "scheduler source drift: "
            f"expected {BASE_SCHEDULER_GIT_BLOB}, got {git_blob(source_bytes)}"
        )
    if git_blob(engine_bytes) != OFFICIAL_ENGINE_GIT_BLOB:
        raise RuntimeError(
            "official engine drift: "
            f"expected {OFFICIAL_ENGINE_GIT_BLOB}, got {git_blob(engine_bytes)}"
        )

    try:
        source_text = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("scheduler is not UTF-8") from exc

    candidate = replace_once(
        source_text,
        OLD_POST_UNITS,
        NEW_POST_UNITS,
        label="current-unit atomic primitive",
    )
    candidate = replace_once(
        candidate,
        OLD_FUTURE_PACKET,
        NEW_FUTURE_PACKET,
        label="future route packet",
    )
    if candidate == source_text:
        raise RuntimeError("candidate unexpectedly equals source")
    compile(candidate, str(output), "exec")

    candidate_bytes = candidate.encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(candidate_bytes)

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "base_main": BASE_MAIN,
        "source": {
            "path": str(source),
            "bytes": len(source_bytes),
            "git_blob": git_blob(source_bytes),
            "sha256": sha256(source_bytes),
        },
        "official_engine": {
            "path": str(engine),
            "bytes": len(engine_bytes),
            "git_blob": git_blob(engine_bytes),
            "sha256": sha256(engine_bytes),
        },
        "candidate": {
            "path": str(output),
            "bytes": len(candidate_bytes),
            "git_blob": git_blob(candidate_bytes),
            "sha256": sha256(candidate_bytes),
        },
        "replacements": {
            "shared_atomic_unit_packet": 1,
            "future_receipt_profile_callsite": 1,
        },
        "canonical_source_mutated": False,
        "score_claim": False,
        "disposition": "SOURCE_REAL_ACTION_UNMEASURED",
    }
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(rendered, encoding="utf-8")

    if source.read_bytes() != source_bytes:
        raise RuntimeError("canonical scheduler changed during materialization")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--engine", type=Path, default=DEFAULT_ENGINE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize(args.source, args.engine, args.output, args.receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
