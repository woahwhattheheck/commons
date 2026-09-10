#!/usr/bin/env python3
"""Exact-source carrier for represented-horizon executable-prefix closure.

The carrier never edits the checkout. It authenticates the frozen SELL source
and pinned interpreter, applies two exact in-memory replacements, parses the
candidate, proves reversibility, and emits either a deterministic receipt or a
reviewable unified patch.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path
from typing import Any

BASE_COMMIT = "c51049d671b55d282e0fed5df37a0be7c513a838"
SOURCE_REL = Path("revenue/kaggriculture/cloud-execution-lab/frozen_selected.py")
ENGINE_REL = Path(
    "revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py"
)
EXPECTED_SOURCE_GIT_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
EXPECTED_ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"

OLD_CURRENT_STAGE = """    f,p=copy.deepcopy(farm),copy.deepcopy(private)
    size=len(f['tiles'])
    apply_represented_market(f,p,current_market,size)
    turns_per_day=int(config.get('turnsPerDay',24))
"""
NEW_CURRENT_STAGE = """    f,p=copy.deepcopy(farm),copy.deepcopy(private)
    size=len(f['tiles'])
    max_orders=max(1,int(config.get('maxMarketOrdersPerTurn',10)))
    def executable_market(orders):
        return list(orders)[:max_orders] if isinstance(orders,list) else []
    apply_represented_market(f,p,executable_market(current_market),size)
    turns_per_day=int(config.get('turnsPerDay',24))
"""

OLD_FUTURE_STAGE = """        apply_represented_market(f,p,action.get('market',[]),size)
"""
NEW_FUTURE_STAGE = """        apply_represented_market(
            f,p,executable_market(action.get('market',[])),size)
"""

REPLACEMENTS = (
    ("current_stage", OLD_CURRENT_STAGE, NEW_CURRENT_STAGE),
    ("future_stage", OLD_FUTURE_STAGE, NEW_FUTURE_STAGE),
)

ENGINE_ANCHORS = (
    'max_orders = max(1, int(get(env.configuration, "maxMarketOrdersPerTurn", 10)))',
    'q = list(m) if isinstance(m, list) else []',
    'queues.append(q[:max_orders])',
)
SOURCE_ANCHORS = (
    "def apply_represented_market(farm, private, orders, size):",
    "def represented_shed_event(now, baseline_end, hard_end, route, farm, private, config,",
    "unit_event=(represented_shed_event(",
    "horizon['unit_event']=unit_event",
)


class IntegrityError(RuntimeError):
    """Raised when exact source identity or the bounded patch drifts."""


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bound_read(repo: Path, relative: Path, expected_blob: str) -> bytes:
    root = repo.resolve()
    path = (root / relative).resolve()
    if path != root and root not in path.parents:
        raise IntegrityError(f"path escapes repository: {relative}")
    data = path.read_bytes()
    actual = git_blob_sha(data)
    if actual != expected_blob:
        raise IntegrityError(
            f"{relative}: expected Git blob {expected_blob}, observed {actual}"
        )
    return data


def apply_patch(source: str) -> str:
    candidate = source
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
    if restored != source:
        raise IntegrityError("candidate changes escape the two exact replacements")
    return candidate


def build(repo: Path) -> tuple[bytes, bytes, bytes, str]:
    source = _bound_read(repo, SOURCE_REL, EXPECTED_SOURCE_GIT_BLOB)
    engine = _bound_read(repo, ENGINE_REL, EXPECTED_ENGINE_GIT_BLOB)
    source_text = source.decode("utf-8")
    engine_text = engine.decode("utf-8")

    missing_engine = [a for a in ENGINE_ANCHORS if engine_text.count(a) != 1]
    if missing_engine:
        raise IntegrityError(
            f"engine executable-prefix anchors missing or duplicated: {missing_engine!r}"
        )
    missing_source = [a for a in SOURCE_ANCHORS if source_text.count(a) != 1]
    if missing_source:
        raise IntegrityError(
            f"represented-horizon anchors missing or duplicated: {missing_source!r}"
        )

    candidate_text = apply_patch(source_text)
    patch = "".join(
        difflib.unified_diff(
            source_text.splitlines(keepends=True),
            candidate_text.splitlines(keepends=True),
            fromfile=f"a/{SOURCE_REL.as_posix()}",
            tofile=f"b/{SOURCE_REL.as_posix()}",
        )
    )
    if not patch:
        raise IntegrityError("bounded repair unexpectedly produced an empty patch")
    return source, engine, candidate_text.encode("utf-8"), patch


def receipt(repo: Path) -> dict[str, Any]:
    source, engine, candidate, patch = build(repo)
    return {
        "schema": "titan-v3-represented-horizon-executable-prefix/v1",
        "base_commit": BASE_COMMIT,
        "source": {
            "path": SOURCE_REL.as_posix(),
            "git_blob": git_blob_sha(source),
            "sha256": sha256(source),
            "bytes": len(source),
        },
        "engine": {
            "path": ENGINE_REL.as_posix(),
            "git_blob": git_blob_sha(engine),
            "sha256": sha256(engine),
            "bytes": len(engine),
            "raw_prefix_contract": True,
        },
        "candidate": {
            "git_blob": git_blob_sha(candidate),
            "sha256": sha256(candidate),
            "bytes": len(candidate),
            "replacement_count": len(REPLACEMENTS),
        },
        "closure": {
            "current_represented_market": "active_raw_prefix",
            "future_represented_market": "active_raw_prefix",
            "limit_rule": "max(1,int(maxMarketOrdersPerTurn))",
            "nonlist_queue": "empty",
            "market_fill_model": "unchanged",
        },
        "causal_boundary": (
            "represented market state -> PICKUP/DROP or PLACE reachability -> "
            "unit_event -> product horizon -> active returned SELL quantity"
        ),
        "canonical_mutated": False,
        "strength_claim": "SOURCE_REAL_RETURNED_ACTION_WITNESS_ONLY",
        "patch_sha256": sha256(patch.encode("utf-8")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("json", "patch"), default="json")
    args = parser.parse_args()
    if args.format == "patch":
        print(build(args.repo)[3], end="")
    else:
        print(json.dumps(receipt(args.repo), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
