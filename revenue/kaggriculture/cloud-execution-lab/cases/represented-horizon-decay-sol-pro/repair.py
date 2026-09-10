#!/usr/bin/env python3
"""Exact-source carrier for represented-horizon per-step plant-decay closure.

This carrier stacks on the executable-prefix donor without editing the checkout.
It authenticates the prefix materializer, canonical frozen seller, mechanics,
official interpreter, and controller checkpoint tape; materializes the prefix
candidate in memory; inserts the two missing official decay transitions; proves
reversibility; and emits a deterministic receipt or reviewable patch.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

STACK_BASE_COMMIT = "5d1b376d33858dd827e7e20051cc49648d313034"
SOURCE_REL = Path("revenue/kaggriculture/cloud-execution-lab/frozen_selected.py")
MECHANICS_REL = Path("revenue/kaggriculture/cloud-execution-lab/mechanics.py")
ENGINE_REL = Path(
    "revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py"
)
ARLENE_REL = Path(
    "revenue/kaggriculture/cloud-execution-lab/reference/next-panel/vendor/arlene.py"
)
PREFIX_REPAIR_REL = Path(
    "revenue/kaggriculture/cloud-execution-lab/cases/"
    "represented-horizon-prefix-sol-pro/repair.py"
)

EXPECTED_SOURCE_GIT_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
EXPECTED_MECHANICS_GIT_BLOB = "044a4f9c0a4a44dde10ada57563238bcaf82075d"
EXPECTED_ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
EXPECTED_ARLENE_GIT_BLOB = "bdb9cf58148a3c7961c085f4902759537decabf6"
EXPECTED_PREFIX_REPAIR_GIT_BLOB = "f14341425ad6bf697702e0167c7c4ae3264d434b"

OLD_CURRENT_STAGE = """    apply_represented_market(f,p,executable_market(current_market),size)
    turns_per_day=int(config.get('turnsPerDay',24))
"""
NEW_CURRENT_STAGE = """    apply_represented_market(f,p,executable_market(current_market),size)
    # The supplied state is post-unit / pre-market.  The official interpreter
    # applies current market, town, then plant decay before the next unit stage.
    m._decay_plants(f,now)
    turns_per_day=int(config.get('turnsPerDay',24))
"""

OLD_FUTURE_STAGE = """        apply_represented_market(
            f,p,executable_market(action.get('market',[])),size)
"""
NEW_FUTURE_STAGE = """        apply_represented_market(
            f,p,executable_market(action.get('market',[])),size)
        # Match the official market -> town -> decay boundary before t+1.
        # Town changes only shared market state, which this physical witness
        # intentionally does not project; plant decay changes future unit legality.
        m._decay_plants(f,t)
"""

REPLACEMENTS = (
    ("current_decay_boundary", OLD_CURRENT_STAGE, NEW_CURRENT_STAGE),
    ("future_decay_boundary", OLD_FUTURE_STAGE, NEW_FUTURE_STAGE),
)

MECHANICS_ANCHORS = (
    "def _decay_plants(farm, step):",
    'if (step - mls) % 2 != 0:',
    'tile["yield_units"] -= 1',
    'if tile["yield_units"] <= 0:\n                '
    'farm["tiles"][y][x] = {"kind": "WEED"}',
)
ENGINE_CHRONOLOGY_ANCHOR = """    _process_market(state, env)
    _town_consume(env, state, step)
    for farm in obs0.farms:
        _decay_plants(farm, step)
"""
ARLENE_DECISIONS_ANCHOR = """DECISIONS = (
    (226, "shop_YARN_STORE", 1, YARN),
    (360, "px_CARROT", 42, YARN_CARROT),
    (433, "inv_MILK", 10067, MILK_GLUT),
)"""
PREFIX_SOURCE_ANCHORS = (
    "def represented_shed_event(now, baseline_end, hard_end, route, farm, private, config,",
    "apply_represented_market(f,p,executable_market(current_market),size)",
    "f,p,executable_market(action.get('market',[])),size)",
)


class IntegrityError(RuntimeError):
    """Raised when exact source identity or the bounded patch drifts."""


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolved(repo: Path, relative: Path) -> Path:
    root = repo.resolve()
    path = (root / relative).resolve()
    if path != root and root not in path.parents:
        raise IntegrityError(f"path escapes repository: {relative}")
    return path


def _bound_read(repo: Path, relative: Path, expected_blob: str) -> bytes:
    path = _resolved(repo, relative)
    if not path.is_file():
        raise IntegrityError(f"required regular file missing: {relative}")
    data = path.read_bytes()
    actual = git_blob_sha(data)
    if actual != expected_blob:
        raise IntegrityError(
            f"{relative}: expected Git blob {expected_blob}, observed {actual}"
        )
    return data


def _load_prefix_repair(repo: Path) -> tuple[ModuleType, bytes]:
    source = _bound_read(
        repo, PREFIX_REPAIR_REL, EXPECTED_PREFIX_REPAIR_GIT_BLOB
    )
    path = _resolved(repo, PREFIX_REPAIR_REL)
    name = "_titan_bound_represented_horizon_prefix_repair"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise IntegrityError("cannot load exact prefix materializer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if getattr(module, "EXPECTED_SOURCE_GIT_BLOB", None) != EXPECTED_SOURCE_GIT_BLOB:
        raise IntegrityError("prefix materializer source binding drift")
    if getattr(module, "EXPECTED_ENGINE_GIT_BLOB", None) != EXPECTED_ENGINE_GIT_BLOB:
        raise IntegrityError("prefix materializer engine binding drift")
    return module, source


def apply_patch(prefix_candidate: str) -> str:
    candidate = prefix_candidate
    for name, old, new in REPLACEMENTS:
        count = candidate.count(old)
        if count != 1:
            raise IntegrityError(f"{name} preimage count must be 1, observed {count}")
        candidate = candidate.replace(old, new, 1)

    ast.parse(candidate, filename=str(SOURCE_REL))

    restored = candidate
    for name, old, new in reversed(REPLACEMENTS):
        count = restored.count(new)
        if count != 1:
            raise IntegrityError(f"{name} postimage count must be 1, observed {count}")
        restored = restored.replace(new, old, 1)
    if restored != prefix_candidate:
        raise IntegrityError("candidate changes escape the two exact decay insertions")
    return candidate


def build(
    repo: Path,
) -> tuple[bytes, bytes, bytes, bytes, bytes, bytes, str]:
    prefix, prefix_repair_source = _load_prefix_repair(repo)
    source, engine, prefix_candidate, _prefix_patch = prefix.build(repo)
    mechanics = _bound_read(repo, MECHANICS_REL, EXPECTED_MECHANICS_GIT_BLOB)
    arlene = _bound_read(repo, ARLENE_REL, EXPECTED_ARLENE_GIT_BLOB)

    if git_blob_sha(source) != EXPECTED_SOURCE_GIT_BLOB:
        raise IntegrityError("prefix build returned a different canonical source")
    if git_blob_sha(engine) != EXPECTED_ENGINE_GIT_BLOB:
        raise IntegrityError("prefix build returned a different official interpreter")

    mechanics_text = mechanics.decode("utf-8")
    missing_mechanics = [
        anchor for anchor in MECHANICS_ANCHORS if mechanics_text.count(anchor) != 1
    ]
    if missing_mechanics:
        raise IntegrityError(
            f"mechanics decay anchors missing or duplicated: {missing_mechanics!r}"
        )
    engine_text = engine.decode("utf-8")
    if engine_text.count(ENGINE_CHRONOLOGY_ANCHOR) != 1:
        raise IntegrityError("official market -> town -> decay chronology drift")
    arlene_text = arlene.decode("utf-8")
    if arlene_text.count(ARLENE_DECISIONS_ANCHOR) != 1:
        raise IntegrityError("Arlene decision checkpoint tape drift")
    prefix_text = prefix_candidate.decode("utf-8")
    missing_prefix = [
        anchor for anchor in PREFIX_SOURCE_ANCHORS if prefix_text.count(anchor) != 1
    ]
    if missing_prefix:
        raise IntegrityError(
            f"prefix candidate anchors missing or duplicated: {missing_prefix!r}"
        )

    candidate_text = apply_patch(prefix_text)
    patch = "".join(
        difflib.unified_diff(
            prefix_text.splitlines(keepends=True),
            candidate_text.splitlines(keepends=True),
            fromfile=f"a/{SOURCE_REL.as_posix()}@prefix-candidate",
            tofile=f"b/{SOURCE_REL.as_posix()}@prefix+decay-candidate",
        )
    )
    if not patch:
        raise IntegrityError("bounded decay repair unexpectedly produced an empty patch")
    return (
        source,
        engine,
        mechanics,
        prefix_repair_source,
        prefix_candidate,
        candidate_text.encode("utf-8"),
        patch,
    )


def receipt(repo: Path) -> dict[str, Any]:
    (
        source,
        engine,
        mechanics,
        prefix_repair_source,
        prefix_candidate,
        candidate,
        patch,
    ) = build(repo)
    arlene = _bound_read(repo, ARLENE_REL, EXPECTED_ARLENE_GIT_BLOB)
    return {
        "schema": "titan-v3-represented-horizon-plant-decay/v1",
        "stack_base_commit": STACK_BASE_COMMIT,
        "source": {
            "path": SOURCE_REL.as_posix(),
            "git_blob": git_blob_sha(source),
            "sha256": sha256(source),
            "bytes": len(source),
        },
        "prefix_materializer": {
            "path": PREFIX_REPAIR_REL.as_posix(),
            "git_blob": git_blob_sha(prefix_repair_source),
            "sha256": sha256(prefix_repair_source),
            "bytes": len(prefix_repair_source),
        },
        "prefix_candidate": {
            "git_blob": git_blob_sha(prefix_candidate),
            "sha256": sha256(prefix_candidate),
            "bytes": len(prefix_candidate),
            "executable_market_prefix": True,
        },
        "mechanics": {
            "path": MECHANICS_REL.as_posix(),
            "git_blob": git_blob_sha(mechanics),
            "sha256": sha256(mechanics),
            "bytes": len(mechanics),
            "decay_bound": True,
        },
        "engine": {
            "path": ENGINE_REL.as_posix(),
            "git_blob": git_blob_sha(engine),
            "sha256": sha256(engine),
            "bytes": len(engine),
            "chronology": "unit -> market -> town -> decay",
        },
        "controller": {
            "path": ARLENE_REL.as_posix(),
            "git_blob": git_blob_sha(arlene),
            "sha256": sha256(arlene),
            "bytes": len(arlene),
            "decision_steps": [226, 360, 433],
        },
        "candidate": {
            "git_blob": git_blob_sha(candidate),
            "sha256": sha256(candidate),
            "bytes": len(candidate),
            "replacement_count": len(REPLACEMENTS),
            "current_decay_boundary": True,
            "future_decay_boundary": True,
        },
        "witness": {
            "now": 120,
            "baseline_end": 128,
            "hard_end": 143,
            "initial_horizon_end": 128,
            "next_checkpoint": 226,
            "service_dates": {},
            "crop": "CARROT",
            "planted_day": 1,
            "yield_units": 3,
            "max_lifespan_step": 120,
            "decay_steps": [120, 122, 124],
            "represented_actions": [[129, "HARVEST"], [130, "DROP"]],
            "predecessor_unit_event": 130,
            "candidate_unit_event": None,
            "horizon_helpers_unmocked": True,
            "returned_action_discriminator": "SELL MILK 1 -> SELL MILK 2",
        },
        "composition": {
            "consumes_prefix_donor": True,
            "purchase_executability": "separate owner",
            "hire_executability": "separate owner",
            "canonical_source_mutated": False,
        },
        "strength_claim": "SOURCE_REAL_RETURNED_ACTION_WITNESS_ONLY",
        "patch_sha256": sha256(patch.encode("utf-8")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("json", "patch"), default="json")
    args = parser.parse_args()
    if args.format == "patch":
        print(build(args.repo)[-1], end="")
    else:
        print(json.dumps(receipt(args.repo), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
