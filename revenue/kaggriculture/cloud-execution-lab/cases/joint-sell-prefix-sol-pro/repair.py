#!/usr/bin/env python3
"""Exact-source carrier for TITAN's joint-SELL executable-prefix closure.

The carrier does not edit the repository. It authenticates the current frozen
SELL consumer and pinned interpreter, applies four exact in-memory replacements,
parses the result, and emits either a deterministic receipt or a reviewable patch.
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

OLD_HELPER_ANCHOR = """def joint_resource_bound(obs, config, base, farm, private, route, end):
"""
NEW_HELPER_ANCHOR = """def _joint_market_prefix(orders, config):
    \"\"\"Return the exact raw queue prefix executable by the official engine.\"\"\"
    max_orders=max(1,int(config.get('maxMarketOrdersPerTurn',10)))
    return list(orders)[:max_orders] if isinstance(orders,list) else []


def joint_resource_bound(obs, config, base, farm, private, route, end):
"""

OLD_BOUND_ORDERS = """    def orders_at(t):
        return base['market'] if t==now else route[t].get('market',[]) if t<len(route) else []
"""
NEW_BOUND_ORDERS = """    def orders_at(t):
        raw=base['market'] if t==now else route[t].get('market',[]) if t<len(route) else []
        return _joint_market_prefix(raw,config)
"""

OLD_TRANSFORM_ORDERS = """            def orders_at(step):
                return base['market'] if step==now else route[step].get('market',[]) if step<len(route) else []
"""
NEW_TRANSFORM_ORDERS = """            def orders_at(step):
                raw=base['market'] if step==now else route[step].get('market',[]) if step<len(route) else []
                return _joint_market_prefix(raw,config)
"""

OLD_LEDGER_CALL = """                    ledger=joint_queue_ledger(plans,current,self.planned,shed,bound,orders_at,
                                              now,bound['capital_end'],int(config.get('maxMarketOrdersPerTurn',10)))
"""
NEW_LEDGER_CALL = """                    ledger=joint_queue_ledger(plans,current,self.planned,shed,bound,orders_at,
                                              now,bound['capital_end'],
                                              max(1,int(config.get('maxMarketOrdersPerTurn',10))))
"""

REPLACEMENTS = (
    ("helper", OLD_HELPER_ANCHOR, NEW_HELPER_ANCHOR),
    ("bound_orders", OLD_BOUND_ORDERS, NEW_BOUND_ORDERS),
    ("transform_orders", OLD_TRANSFORM_ORDERS, NEW_TRANSFORM_ORDERS),
    ("ledger_limit", OLD_LEDGER_CALL, NEW_LEDGER_CALL),
)

ENGINE_ANCHORS = (
    'max_orders = max(1, int(get(env.configuration, "maxMarketOrdersPerTurn", 10)))',
    'q = list(m) if isinstance(m, list) else []',
    'queues.append(q[:max_orders])',
)
SOURCE_ANCHORS = (
    "bound=joint_resource_bound(obs,config,base,farm,private,route,end)",
    "ledger=joint_queue_ledger(plans,current,self.planned,shed,bound,orders_at,",
    "if len(market)>max_orders or any(actual.get(p,0)!=q",
)


class IntegrityError(RuntimeError):
    """Raised when source identity or the exact replacement boundary drifts."""


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
            raise IntegrityError(
                f"{name} preimage count must be 1, observed {count}"
            )
        candidate = candidate.replace(old, new, 1)

    ast.parse(candidate, filename=str(SOURCE_REL))

    restored = candidate
    for name, old, new in reversed(REPLACEMENTS):
        count = restored.count(new)
        if count != 1:
            raise IntegrityError(
                f"{name} postimage count must be 1, observed {count}"
            )
        restored = restored.replace(new, old, 1)
    if restored != source:
        raise IntegrityError("candidate changes escape the four exact replacements")
    return candidate


def build(repo: Path) -> tuple[bytes, bytes, bytes, str]:
    source = _bound_read(repo, SOURCE_REL, EXPECTED_SOURCE_GIT_BLOB)
    engine = _bound_read(repo, ENGINE_REL, EXPECTED_ENGINE_GIT_BLOB)
    source_text = source.decode("utf-8")
    engine_text = engine.decode("utf-8")

    missing_engine = [
        anchor for anchor in ENGINE_ANCHORS if engine_text.count(anchor) != 1
    ]
    if missing_engine:
        raise IntegrityError(
            f"engine executable-prefix anchors missing or duplicated: {missing_engine!r}"
        )
    missing_source = [
        anchor for anchor in SOURCE_ANCHORS if source_text.count(anchor) != 1
    ]
    if missing_source:
        raise IntegrityError(
            f"joint-consumer anchors missing or duplicated: {missing_source!r}"
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
    hunk_count = patch.count("@@") // 2
    if hunk_count != 2:
        raise IntegrityError(
            f"repair must remain two unified-diff hunks, observed {hunk_count}"
        )
    return source, engine, candidate_text.encode("utf-8"), patch


def receipt(repo: Path) -> dict[str, Any]:
    source, engine, candidate, patch = build(repo)
    return {
        "schema": "titan-v3-joint-sell-executable-prefix/v1",
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
            "unified_diff_hunks": 2,
        },
        "closure": {
            "resource_bound_queue": "active_raw_prefix",
            "slot_ledger_queue": "active_raw_prefix",
            "limit_rule": "max(1,int(maxMarketOrdersPerTurn))",
            "nonlist_queue": "empty",
        },
        "causal_boundary": (
            "joint options -> joint_resource_bound -> joint_queue_ledger "
            "-> joint versus single selected plan"
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
