# SPDX-License-Identifier: Apache-2.0
"""Classify a frozen-V2 SELL target-domain product attribution panel."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable

OPERATION = "titan-v2-target-product-attribution-20260909-sol-archimedes-01"
EXPECTED_V2_SCHEDULER_BLOB = "7c068b7078c3d7c09bb3836590ad42b0af934cdf"
PRODUCT_ARMS = (
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
)
ALL_ARMS = ("CONTROL", "CORE") + PRODUCT_ARMS
EXPECTED_OPPONENTS = ("arlene", "v1")


class CompareError(ValueError):
    """The panel or its provenance is incomplete, malformed, or non-comparable."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CompareError(f"cannot read {path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise CompareError(f"{path} is not a JSON object")
    return value


def finite(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CompareError(f"{field} is not numeric: {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise CompareError(f"{field} is not finite: {value!r}")
    return number


def game_key(game: dict[str, Any]) -> tuple[str, int, int]:
    try:
        opponent = str(game["opponent"])
        seed = int(game["seed"])
        seat = int(game["candidate_seat"])
    except Exception as exc:
        raise CompareError(f"malformed game identity: {game!r}") from exc
    if seat not in (0, 1):
        raise CompareError(f"invalid candidate seat {seat}")
    return opponent, seed, seat


def index_panel(
    document: dict[str, Any],
    *,
    arm: str,
    expected_seeds: tuple[int, ...],
) -> dict[tuple[str, int, int], dict[str, Any]]:
    seeds = document.get("seeds")
    if seeds != list(expected_seeds):
        raise CompareError(f"{arm} seeds differ: {seeds!r}")
    opponents = document.get("opponents")
    if not isinstance(opponents, dict) or tuple(sorted(opponents)) != tuple(sorted(EXPECTED_OPPONENTS)):
        raise CompareError(f"{arm} opponents differ: {opponents!r}")
    games = document.get("games")
    if not isinstance(games, list):
        raise CompareError(f"{arm} games is not a list")
    indexed: dict[tuple[str, int, int], dict[str, Any]] = {}
    for game in games:
        if not isinstance(game, dict):
            raise CompareError(f"{arm} contains a non-object game")
        key = game_key(game)
        if key in indexed:
            raise CompareError(f"{arm} contains duplicate game {key!r}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise CompareError(f"{arm} game {key!r} is not complete")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise CompareError(f"{arm} game {key!r} has invalid scores")
        finite(scores[0], field=f"{arm}.{key}.scores[0]")
        finite(scores[1], field=f"{arm}.{key}.scores[1]")
        trace = game.get("trace_sha256")
        if not isinstance(trace, str) or len(trace) != 64:
            raise CompareError(f"{arm} game {key!r} has invalid trace_sha256")
        indexed[key] = game
    expected = {
        (opponent, seed, seat)
        for opponent in EXPECTED_OPPONENTS
        for seed in expected_seeds
        for seat in (0, 1)
    }
    missing = sorted(expected - set(indexed))
    extra = sorted(set(indexed) - expected)
    if missing or extra:
        raise CompareError(f"{arm} panel mismatch: missing={missing!r} extra={extra!r}")
    return indexed


def comparable_provenance(document: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "schema_version",
        "engine_ref",
        "engine_sha256",
        "loader_sha256",
        "evaluator_sha256",
        "opponents",
        "seeds",
        "agent_rng_seed",
        "limits",
        "method",
    )
    return {key: document.get(key) for key in keys}


def own_and_rival(game: dict[str, Any]) -> tuple[float, float]:
    seat = int(game["candidate_seat"])
    scores = game["scores"]
    return float(scores[seat]), float(scores[1 - seat])


def scalar_stats(values: Iterable[float]) -> dict[str, float]:
    materialized = [float(value) for value in values]
    if not materialized:
        raise CompareError("cannot summarize an empty vector")
    return {
        "sum": float(sum(materialized)),
        "mean": float(statistics.fmean(materialized)),
        "median": float(statistics.median(materialized)),
        "min": float(min(materialized)),
        "max": float(max(materialized)),
    }


def classify_marginal(
    own_delta: list[float],
    trace_changes: int,
    by_opponent: dict[str, dict[str, Any]],
) -> str:
    if trace_changes == 0:
        return "NO_EFFECT"
    stats = scalar_stats(own_delta)
    positives = sum(value > 0 for value in own_delta)
    negatives = sum(value < 0 for value in own_delta)
    strata = [by_opponent[name]["own_delta"]["mean"] for name in EXPECTED_OPPONENTS]
    if (
        stats["mean"] > 0
        and stats["median"] >= 0
        and positives >= negatives
        and all(value >= 0 for value in strata)
    ):
        return "MARGINAL_UPSIDE"
    if (
        stats["mean"] < 0
        and stats["median"] <= 0
        and negatives >= positives
        and all(value <= 0 for value in strata)
    ):
        return "MARGINAL_DOWNSIDE"
    return "MIXED"


def compare_arm(
    baseline: dict[tuple[str, int, int], dict[str, Any]],
    candidate: dict[tuple[str, int, int], dict[str, Any]],
) -> dict[str, Any]:
    if set(baseline) != set(candidate):
        raise CompareError("paired panels have unequal key sets")
    rows: list[dict[str, Any]] = []
    own_delta: list[float] = []
    rival_delta: list[float] = []
    margin_delta: list[float] = []
    trace_changes = 0
    by_opponent_vectors: dict[str, dict[str, list[float]]] = {
        name: {"own": [], "rival": [], "margin": []} for name in EXPECTED_OPPONENTS
    }
    for key in sorted(baseline):
        base_game = baseline[key]
        candidate_game = candidate[key]
        base_own, base_rival = own_and_rival(base_game)
        arm_own, arm_rival = own_and_rival(candidate_game)
        own = arm_own - base_own
        rival = arm_rival - base_rival
        margin = own - rival
        changed = base_game["trace_sha256"] != candidate_game["trace_sha256"]
        trace_changes += int(changed)
        own_delta.append(own)
        rival_delta.append(rival)
        margin_delta.append(margin)
        opponent, seed, seat = key
        by_opponent_vectors[opponent]["own"].append(own)
        by_opponent_vectors[opponent]["rival"].append(rival)
        by_opponent_vectors[opponent]["margin"].append(margin)
        if changed or own != 0 or rival != 0:
            rows.append(
                {
                    "opponent": opponent,
                    "seed": seed,
                    "candidate_seat": seat,
                    "baseline_own": base_own,
                    "candidate_own": arm_own,
                    "baseline_rival": base_rival,
                    "candidate_rival": arm_rival,
                    "own_delta": own,
                    "rival_delta": rival,
                    "margin_delta": margin,
                    "trace_changed": changed,
                    "baseline_trace_sha256": base_game["trace_sha256"],
                    "candidate_trace_sha256": candidate_game["trace_sha256"],
                }
            )
    by_opponent: dict[str, dict[str, Any]] = {}
    for opponent in EXPECTED_OPPONENTS:
        vectors = by_opponent_vectors[opponent]
        by_opponent[opponent] = {
            "cells": len(vectors["own"]),
            "own_delta": scalar_stats(vectors["own"]),
            "rival_delta": scalar_stats(vectors["rival"]),
            "margin_delta": scalar_stats(vectors["margin"]),
            "positive_own_cells": sum(value > 0 for value in vectors["own"]),
            "negative_own_cells": sum(value < 0 for value in vectors["own"]),
        }
    result = {
        "cells": len(own_delta),
        "trace_changes": trace_changes,
        "positive_own_cells": sum(value > 0 for value in own_delta),
        "negative_own_cells": sum(value < 0 for value in own_delta),
        "zero_own_cells": sum(value == 0 for value in own_delta),
        "own_delta": scalar_stats(own_delta),
        "rival_delta": scalar_stats(rival_delta),
        "margin_delta": scalar_stats(margin_delta),
        "by_opponent": by_opponent,
        "changed_cells": rows,
    }
    result["classification"] = classify_marginal(
        own_delta, trace_changes, by_opponent
    )
    return result


def validate_receipts(receipts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source_closures: set[str] = set()
    candidate_closures: set[str] = set()
    scheduler_blobs: set[str] = set()
    for arm in ("CORE",) + PRODUCT_ARMS:
        receipt = receipts.get(arm)
        if not isinstance(receipt, dict):
            raise CompareError(f"missing receipt for {arm}")
        if receipt.get("schema_version") != 1 or receipt.get("operation") != OPERATION:
            raise CompareError(f"{arm} receipt identity mismatch")
        if receipt.get("arm") != arm:
            raise CompareError(f"{arm} receipt arm mismatch")
        source = receipt.get("source")
        candidate = receipt.get("candidate")
        if not isinstance(source, dict) or not isinstance(candidate, dict):
            raise CompareError(f"{arm} receipt is malformed")
        if source.get("scheduler_git_blob_sha1") != EXPECTED_V2_SCHEDULER_BLOB:
            raise CompareError(f"{arm} source scheduler blob mismatch")
        if candidate.get("changed_files") != ["scheduler.py"]:
            raise CompareError(f"{arm} changed-files boundary mismatch")
        source_closures.add(str(source.get("closure_sha256")))
        candidate_closures.add(str(candidate.get("closure_sha256")))
        scheduler_blobs.add(str(candidate.get("scheduler_git_blob_sha1")))
    if len(source_closures) != 1:
        raise CompareError(f"source closures differ: {sorted(source_closures)!r}")
    if len(candidate_closures) != 1 + len(PRODUCT_ARMS):
        raise CompareError("candidate closures are not unique across arms")
    if len(scheduler_blobs) != 1 + len(PRODUCT_ARMS):
        raise CompareError("scheduler blobs are not unique across arms")
    if next(iter(source_closures)) in candidate_closures:
        raise CompareError("an attribution arm closure equals the V2 source closure")
    return {
        "source_closure_sha256": next(iter(source_closures)),
        "candidate_closure_sha256": {
            arm: receipts[arm]["candidate"]["closure_sha256"]
            for arm in ("CORE",) + PRODUCT_ARMS
        },
        "candidate_scheduler_git_blob_sha1": {
            arm: receipts[arm]["candidate"]["scheduler_git_blob_sha1"]
            for arm in ("CORE",) + PRODUCT_ARMS
        },
    }


def build_report(
    documents: dict[str, dict[str, Any]],
    receipts: dict[str, dict[str, Any]],
    *,
    expected_seeds: tuple[int, ...],
    git_head: str,
) -> dict[str, Any]:
    if tuple(documents) != ALL_ARMS:
        raise CompareError(f"document arm order mismatch: {tuple(documents)!r}")
    provenance = comparable_provenance(documents["CONTROL"])
    for arm in ALL_ARMS[1:]:
        if comparable_provenance(documents[arm]) != provenance:
            raise CompareError(f"{arm} evaluator provenance differs from CONTROL")
    indexed = {
        arm: index_panel(document, arm=arm, expected_seeds=expected_seeds)
        for arm, document in documents.items()
    }
    receipt_summary = validate_receipts(receipts)
    control_vs_core = compare_arm(indexed["CORE"], indexed["CONTROL"])
    if control_vs_core["trace_changes"] == 0:
        raise CompareError("CONTROL and CORE have identical action traces on the panel")
    products = {
        arm: compare_arm(indexed["CORE"], indexed[arm]) for arm in PRODUCT_ARMS
    }
    recommended = [
        arm for arm in PRODUCT_ARMS if products[arm]["classification"] == "MARGINAL_UPSIDE"
    ]
    excluded = [
        arm for arm in PRODUCT_ARMS if products[arm]["classification"] == "MARGINAL_DOWNSIDE"
    ]
    unresolved = [
        arm for arm in PRODUCT_ARMS if products[arm]["classification"] == "MIXED"
    ]
    no_effect = [
        arm for arm in PRODUCT_ARMS if products[arm]["classification"] == "NO_EFFECT"
    ]
    sum_individual_own = sum(products[arm]["own_delta"]["sum"] for arm in PRODUCT_ARMS)
    full_policy_own = control_vs_core["own_delta"]["sum"]
    rank = sorted(
        PRODUCT_ARMS,
        key=lambda arm: (
            products[arm]["own_delta"]["mean"],
            products[arm]["margin_delta"]["mean"],
            products[arm]["trace_changes"],
            arm,
        ),
        reverse=True,
    )
    return {
        "schema_version": 1,
        "operation": OPERATION,
        "verdict": "ATTRIBUTION_COMPLETE",
        "exit_code": 0,
        "git_head": git_head,
        "expected_seeds": list(expected_seeds),
        "opponents": list(EXPECTED_OPPONENTS),
        "cells_per_arm": len(expected_seeds) * 2 * len(EXPECTED_OPPONENTS),
        "provenance_sha256": hashlib.sha256(
            json.dumps(provenance, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "receipts": receipt_summary,
        "control_all_shed_vs_core": control_vs_core,
        "products_vs_core": products,
        "ranking_by_mean_own_delta": rank,
        "conservative_whitelist": {
            "core_policy": "inherited baseline SELL plus pending scheduler intent",
            "recommended_expansions": recommended,
            "exclude_on_this_panel": excluded,
            "unresolved": unresolved,
            "no_observed_effect": no_effect,
        },
        "interaction_diagnostic": {
            "all_shed_own_delta_sum_vs_core": full_policy_own,
            "sum_of_one_product_own_delta_sums_vs_core": sum_individual_own,
            "non_additivity_residual": full_policy_own - sum_individual_own,
            "note": "One-product marginals are causal arms, not an assumption of additivity.",
        },
        "scope": {
            "promotion_authorized": False,
            "leaderboard_submission_authorized": False,
            "canonical_or_runtime_mutation": False,
        },
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Titan V2 SELL target-domain product attribution",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Exact head: `{report['git_head']}`",
        f"- Cells per arm: `{report['cells_per_arm']}`",
        f"- Provenance SHA-256: `{report['provenance_sha256']}`",
        "- Scope: causal attribution only; no promotion or leaderboard submission.",
        "",
        "## Full-policy anchor",
        "",
    ]
    anchor = report["control_all_shed_vs_core"]
    lines.extend(
        [
            f"Frozen V2 all-shed relative to V1-core: mean own `{anchor['own_delta']['mean']:+.6f}`, "
            f"median `{anchor['own_delta']['median']:+.6f}`, margin mean `{anchor['margin_delta']['mean']:+.6f}`, "
            f"trace changes `{anchor['trace_changes']}/{anchor['cells']}`.",
            "",
            "## One-product marginals relative to core",
            "",
            "| Rank | Product | Classification | Mean own | Median own | Mean margin | Trace changes | + / - / 0 |",
            "|---:|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for index, arm in enumerate(report["ranking_by_mean_own_delta"], start=1):
        result = report["products_vs_core"][arm]
        lines.append(
            f"| {index} | `{arm}` | `{result['classification']}` | "
            f"{result['own_delta']['mean']:+.6f} | {result['own_delta']['median']:+.6f} | "
            f"{result['margin_delta']['mean']:+.6f} | {result['trace_changes']}/{result['cells']} | "
            f"{result['positive_own_cells']} / {result['negative_own_cells']} / {result['zero_own_cells']} |"
        )
    whitelist = report["conservative_whitelist"]
    lines.extend(
        [
            "",
            "## Conservative V3 handoff",
            "",
            f"- Recommended expansions: `{whitelist['recommended_expansions']}`",
            f"- Exclude on this panel: `{whitelist['exclude_on_this_panel']}`",
            f"- Unresolved: `{whitelist['unresolved']}`",
            f"- No observed effect: `{whitelist['no_observed_effect']}`",
            "",
            "The product marginals are exact one-factor arms. Their sum is not treated as additive; "
            "the report retains the measured non-additivity residual.",
            "",
        ]
    )
    return "\n".join(lines)


def invalid_report(reason: str, *, git_head: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "operation": OPERATION,
        "verdict": "INVALID",
        "exit_code": 2,
        "git_head": git_head,
        "reason": reason,
        "scope": {
            "promotion_authorized": False,
            "leaderboard_submission_authorized": False,
            "canonical_or_runtime_mutation": False,
        },
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--expected-seeds", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    try:
        expected_seeds = tuple(
            int(piece.strip()) for piece in args.expected_seeds.split(",") if piece.strip()
        )
        if not expected_seeds or len(set(expected_seeds)) != len(expected_seeds):
            raise CompareError("expected seeds must be non-empty and unique")
        documents = {
            arm: read_json(args.results / f"{arm}.json") for arm in ALL_ARMS
        }
        receipts = {
            arm: read_json(args.receipts / f"{arm}.json")
            for arm in ("CORE",) + PRODUCT_ARMS
        }
        report = build_report(
            documents, receipts, expected_seeds=expected_seeds, git_head=args.head
        )
        write_json(args.output, report)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(report), encoding="utf-8")
        print(json.dumps({
            "verdict": report["verdict"],
            "ranking": report["ranking_by_mean_own_delta"],
            "whitelist": report["conservative_whitelist"],
        }, sort_keys=True))
        return 0
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        report = invalid_report(reason, git_head=args.head)
        write_json(args.output, report)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(
            "# Titan V2 SELL target-domain product attribution\n\n"
            f"- Verdict: `INVALID`\n- Reason: `{reason}`\n",
            encoding="utf-8",
        )
        print(json.dumps(report, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
