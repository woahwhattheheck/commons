#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Apply the reviewed own-value admission gate to one precommitted holdout."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
PARENT_PATH = (
    LAB
    / "analysis"
    / "titan-v3-own-value-bound-panel-sol-closure"
    / "action_admission.py"
)

SEED_DERIVATION_LABEL = (
    "titan-v3-own-value-disjoint-holdout-sol-pro-20260910-01"
)
HOLDOUT_SEEDS = (
    1201189346,
    2053792019,
    684357706,
    572159600,
    1619590821,
    1748784700,
    2100322278,
    1851971276,
)
DEVELOPMENT_SEEDS = frozenset(
    {
        539131249,
        1834999074,
        2609097301,
        2609097302,
        2609097303,
        2609097304,
        2611092201,
        2611092207,
    }
)
HOLDOUT_OPPONENTS = (
    "apex",
    "kaito_v43",
    "cok_v10",
    "public_bt12",
    "v1",
    "v2",
)
OPERATION = "titan-v3-own-value-disjoint-holdout-sol-pro-20260910-01"


def derive_seeds(label: str = SEED_DERIVATION_LABEL, count: int = 8) -> tuple[int, ...]:
    """Derive an immutable, reviewable seed bank before any game result exists."""
    if not label or type(count) is not int or count <= 0:
        raise ValueError("seed derivation requires a non-empty label and positive count")
    return tuple(
        int.from_bytes(
            hashlib.sha256(f"{label}:{index}".encode("utf-8")).digest()[:4],
            "big",
        )
        & 0x7FFFFFFF
        for index in range(count)
    )


def load_parent() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "_titan_v3_own_value_parent_admission", PARENT_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load parent admission module: {PARENT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.OPPONENTS = HOLDOUT_OPPONENTS
    module.SEEDS = HOLDOUT_SEEDS
    return module


def holdout_metadata() -> dict[str, Any]:
    derived = derive_seeds()
    if derived != HOLDOUT_SEEDS:
        raise RuntimeError("hard-coded holdout bank differs from its derivation")
    overlap = sorted(DEVELOPMENT_SEEDS.intersection(HOLDOUT_SEEDS))
    if overlap:
        raise RuntimeError(f"holdout bank reuses development seeds: {overlap}")
    return {
        "kind": "one-shot-disjoint-confirmation",
        "seed_derivation": {
            "algorithm": "uint31(first4bytes(sha256(label + ':' + index)))",
            "label": SEED_DERIVATION_LABEL,
            "count": len(HOLDOUT_SEEDS),
        },
        "seeds": list(HOLDOUT_SEEDS),
        "development_seed_overlap": overlap,
        "opponents": list(HOLDOUT_OPPONENTS),
        "both_candidate_seats": True,
        "paired_cells_per_arm": (
            len(HOLDOUT_SEEDS) * len(HOLDOUT_OPPONENTS) * 2
        ),
        "candidate_hypotheses_spent": 1,
        "economic_result_may_not_be_tuned_on_this_bank": True,
    }


def assess(
    control: dict[str, Any],
    candidate: dict[str, Any],
    paired: dict[str, Any],
    evaluator_receipt: dict[str, Any],
    *,
    parent: ModuleType | None = None,
) -> dict[str, Any]:
    parent = parent or load_parent()
    result = parent.assess(control, candidate, paired, evaluator_receipt)
    result["operation"] = OPERATION
    result["holdout"] = holdout_metadata()
    result["development_parent"] = {
        "pr": 11965,
        "head": "b6b9a8a4ca26152bbfe1a3833380ca885e5c4cae",
        "run": 34521455981,
        "artifact": 10170277744,
        "verdict": "ADMIT",
        "mean_own_cash_delta": 159.25,
        "mean_margin_delta": 530.96875,
    }
    result["promotion_authorized"] = False
    result["hosted_leaderboard_claim"] = False
    return result


def markdown(parent: ModuleType, report: dict[str, Any]) -> str:
    text = parent.markdown(report).replace(
        "# TITAN V3 own-value action-bound admission",
        "# TITAN V3 own-value one-shot disjoint holdout",
        1,
    )
    meta = report["holdout"]
    custody = [
        "",
        "## Holdout custody",
        "",
        f"- Seed derivation label: `{meta['seed_derivation']['label']}`",
        f"- Disjoint seeds: **{len(meta['seeds'])}**",
        f"- Opponents: **{', '.join(meta['opponents'])}**",
        f"- Paired cells per arm: **{meta['paired_cells_per_arm']}**",
        "- Candidate hypotheses spent on this bank: **1**",
        "- Economic results from this bank are terminal evidence; do not tune and rerun.",
        "- This holdout does not authorize Kaggle submission or release promotion.",
        "",
    ]
    return text + "\n".join(custody)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--paired", type=Path, required=True)
    parser.add_argument("--evaluator-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)

    parent = load_parent()
    try:
        result = assess(
            parent.strict_load(args.control, "control report"),
            parent.strict_load(args.candidate, "candidate report"),
            parent.strict_load(args.paired, "paired report"),
            parent.strict_load(args.evaluator_receipt, "evaluator receipt"),
            parent=parent,
        )
    except parent.EvidenceError as exc:
        print(f"holdout evidence error: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown(parent, result), encoding="utf-8")
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "gates": result["gates"],
                **result["overall"],
            },
            sort_keys=True,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
