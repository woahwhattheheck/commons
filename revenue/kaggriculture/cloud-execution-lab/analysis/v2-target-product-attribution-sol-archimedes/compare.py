# SPDX-License-Identifier: Apache-2.0
"""Classify an exact frozen-V2 SELL target-domain product attribution panel."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import tempfile
from typing import Any, Iterable, Mapping

OPERATION = "titan-v2-target-product-attribution-20260909-sol-archimedes-01"
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
V2_ENTRY_SHA256 = "2e4897fb3aa8b0bee3e97709808c3aa25fa5055bcf5ce7d433b493eb334870f2"
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
MATERIALIZED_ARMS = ("CORE",) + PRODUCT_ARMS
ALL_ARMS = ("CONTROL",) + MATERIALIZED_ARMS
RECEIPT_ARMS = ALL_ARMS
EXPECTED_OPPONENTS = ("arlene", "v1")


class CompareError(ValueError):
    """The panel or its provenance is incomplete, malformed, or non-comparable."""


def strict_object(path: Path) -> dict[str, Any]:
    """Read one strict JSON object, rejecting duplicate keys and non-finite tokens."""

    def reject_pairs(pairs):
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise CompareError(f"duplicate JSON key {key!r} in {path}")
            output[key] = value
        return output

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                CompareError(f"non-finite JSON token {token} in {path}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CompareError(f"cannot read {path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise CompareError(f"{path} must contain one JSON object")
    return value


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def finite(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CompareError(f"{field} is not numeric: {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise CompareError(f"{field} is not finite: {value!r}")
    return number


def lowercase_hex(value: Any, *, length: int, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise CompareError(f"{field} is not a lowercase {length}-hex digest")
    return value


def sha256_text(value: Any, *, field: str) -> str:
    return lowercase_hex(value, length=64, field=field)


def git_sha1(value: Any, *, field: str) -> str:
    return lowercase_hex(value, length=40, field=field)


def exact_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CompareError(f"{field} is not an integer: {value!r}")
    return value


def daily_map(game: Mapping[str, Any], *, field: str) -> dict[int, tuple[float, float]]:
    rows = game.get("daily_bank")
    if not isinstance(rows, list) or not rows:
        raise CompareError(f"{field}.daily_bank must be a non-empty list")
    output: dict[int, tuple[float, float]] = {}
    previous = -1
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise CompareError(f"{field}.daily_bank[{index}] is not an object")
        step = exact_int(row.get("step"), field=f"{field}.daily_bank[{index}].step")
        bank = row.get("bank")
        if step <= previous or step in output:
            raise CompareError(f"{field}.daily_bank steps are not strictly increasing")
        if not isinstance(bank, list) or len(bank) != 2:
            raise CompareError(f"{field}.daily_bank[{index}].bank is invalid")
        output[step] = (
            finite(bank[0], field=f"{field}.daily_bank[{index}].bank[0]"),
            finite(bank[1], field=f"{field}.daily_bank[{index}].bank[1]"),
        )
        previous = step
    return output


def validate_document_identity(
    document: Mapping[str, Any], *, arm: str, expected_seeds: tuple[int, ...]
) -> None:
    if document.get("schema_version") != 1:
        raise CompareError(f"{arm} schema mismatch")
    if document.get("engine_ref") != ENGINE_REF:
        raise CompareError(f"{arm} engine ref mismatch")
    candidate = document.get("candidate")
    if not isinstance(candidate, Mapping):
        raise CompareError(f"{arm} candidate identity missing")
    if (
        candidate.get("entry") != "candidate.py"
        or candidate.get("callable") != "agent"
        or candidate.get("sha256") != V2_ENTRY_SHA256
    ):
        raise CompareError(f"{arm} candidate entry bytes or callable drifted")
    seeds = document.get("seeds")
    if seeds != list(expected_seeds):
        raise CompareError(f"{arm} seeds differ: {seeds!r}")
    opponents = document.get("opponents")
    if not isinstance(opponents, Mapping) or set(opponents) != set(EXPECTED_OPPONENTS):
        raise CompareError(f"{arm} opponents differ: {opponents!r}")
    for name in EXPECTED_OPPONENTS:
        identity = opponents[name]
        if not isinstance(identity, Mapping):
            raise CompareError(f"{arm} opponent {name!r} identity is malformed")
        sha256_text(identity.get("sha256"), field=f"{arm}.opponents.{name}.sha256")
    sha256_text(document.get("loader_sha256"), field=f"{arm}.loader_sha256")
    sha256_text(document.get("evaluator_sha256"), field=f"{arm}.evaluator_sha256")
    engine_sha = document.get("engine_sha256")
    if not isinstance(engine_sha, Mapping) or not engine_sha:
        raise CompareError(f"{arm}.engine_sha256 is malformed")
    for path, digest in engine_sha.items():
        if not isinstance(path, str) or not path:
            raise CompareError(f"{arm}.engine_sha256 has invalid path")
        sha256_text(digest, field=f"{arm}.engine_sha256[{path!r}]")
    exact_int(document.get("agent_rng_seed"), field=f"{arm}.agent_rng_seed")
    if not isinstance(document.get("limits"), Mapping):
        raise CompareError(f"{arm}.limits is malformed")
    if not isinstance(document.get("method"), str) or not document.get("method"):
        raise CompareError(f"{arm}.method is malformed")
    if not isinstance(document.get("python"), str) or not document.get("python"):
        raise CompareError(f"{arm}.python is malformed")
    if not isinstance(document.get("platform"), str) or not document.get("platform"):
        raise CompareError(f"{arm}.platform is malformed")


def game_key(game: Mapping[str, Any], *, field: str) -> tuple[str, int, int]:
    opponent = game.get("opponent")
    if not isinstance(opponent, str) or opponent not in EXPECTED_OPPONENTS:
        raise CompareError(f"{field}.opponent is invalid: {opponent!r}")
    seed = exact_int(game.get("seed"), field=f"{field}.seed")
    seat = exact_int(game.get("candidate_seat"), field=f"{field}.candidate_seat")
    if seat not in (0, 1):
        raise CompareError(f"{field}.candidate_seat is invalid: {seat!r}")
    return opponent, seed, seat


def index_panel(
    document: dict[str, Any],
    *,
    arm: str,
    expected_seeds: tuple[int, ...],
) -> dict[tuple[str, int, int], dict[str, Any]]:
    validate_document_identity(document, arm=arm, expected_seeds=expected_seeds)
    games = document.get("games")
    if not isinstance(games, list):
        raise CompareError(f"{arm}.games is not a list")
    indexed: dict[tuple[str, int, int], dict[str, Any]] = {}
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise CompareError(f"{arm}.games[{index}] is not an object")
        field = f"{arm}.games[{index}]"
        key = game_key(game, field=field)
        if key in indexed:
            raise CompareError(f"{arm} contains duplicate game {key!r}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise CompareError(f"{arm} game {key!r} is not complete")
        steps = exact_int(game.get("steps"), field=f"{field}.steps")
        episode_steps = exact_int(
            game.get("episode_steps"), field=f"{field}.episode_steps"
        )
        if episode_steps <= 1 or steps != episode_steps - 1:
            raise CompareError(f"{arm} game {key!r} has incomplete step coverage")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise CompareError(f"{arm} game {key!r} has invalid scores")
        normalized = dict(game)
        normalized["scores"] = [
            finite(scores[0], field=f"{field}.scores[0]"),
            finite(scores[1], field=f"{field}.scores[1]"),
        ]
        normalized["trace_sha256"] = sha256_text(
            game.get("trace_sha256"), field=f"{field}.trace_sha256"
        )
        normalized["_daily"] = daily_map(game, field=field)
        if max(normalized["_daily"]) != episode_steps - 2:
            raise CompareError(f"{arm} game {key!r} lacks terminal bank checkpoint")
        indexed[key] = normalized
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


def comparable_provenance(document: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "schema_version",
        "engine_ref",
        "engine_sha256",
        "loader_sha256",
        "evaluator_sha256",
        "candidate",
        "opponents",
        "seeds",
        "agent_rng_seed",
        "limits",
        "method",
        "python",
        "platform",
    )
    return {key: document.get(key) for key in keys}


def first_bank_divergence(
    baseline: Mapping[str, Any], candidate: Mapping[str, Any]
) -> int | None:
    left = baseline["_daily"]
    right = candidate["_daily"]
    if set(left) != set(right):
        raise CompareError("paired daily bank checkpoint grids differ")
    for step in sorted(left):
        if left[step] != right[step]:
            return step
    return None


def own_and_rival(game: Mapping[str, Any]) -> tuple[float, float]:
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
    by_opponent: Mapping[str, Mapping[str, Any]],
    by_seat: Mapping[str, Mapping[str, Any]],
) -> str:
    if trace_changes == 0:
        return "NO_EFFECT"
    stats = scalar_stats(own_delta)
    positives = sum(value > 0 for value in own_delta)
    negatives = sum(value < 0 for value in own_delta)
    strata = [
        *[by_opponent[name]["own_delta"]["mean"] for name in EXPECTED_OPPONENTS],
        *[by_seat[str(seat)]["own_delta"]["mean"] for seat in (0, 1)],
    ]
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


def summarize_strata(
    vectors: Mapping[str, Mapping[str, list[float]]]
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name, group in vectors.items():
        result[name] = {
            "cells": len(group["own"]),
            "own_delta": scalar_stats(group["own"]),
            "rival_delta": scalar_stats(group["rival"]),
            "margin_delta": scalar_stats(group["margin"]),
            "positive_own_cells": sum(value > 0 for value in group["own"]),
            "negative_own_cells": sum(value < 0 for value in group["own"]),
            "zero_own_cells": sum(value == 0 for value in group["own"]),
        }
    return result


def compare_arm(
    baseline: Mapping[tuple[str, int, int], Mapping[str, Any]],
    candidate: Mapping[tuple[str, int, int], Mapping[str, Any]],
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
    by_seat_vectors: dict[str, dict[str, list[float]]] = {
        str(seat): {"own": [], "rival": [], "margin": []} for seat in (0, 1)
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
        if (own != 0 or rival != 0) and not changed:
            raise CompareError(f"score changed without action-trace change for {key!r}")
        bank_divergence = first_bank_divergence(base_game, candidate_game)
        if (own != 0 or rival != 0) and bank_divergence is None:
            raise CompareError(f"score changed without bank-checkpoint change for {key!r}")
        trace_changes += int(changed)
        own_delta.append(own)
        rival_delta.append(rival)
        margin_delta.append(margin)
        opponent, seed, seat = key
        for vectors in (by_opponent_vectors[opponent], by_seat_vectors[str(seat)]):
            vectors["own"].append(own)
            vectors["rival"].append(rival)
            vectors["margin"].append(margin)
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
                    "first_daily_bank_divergence_step": bank_divergence,
                    "baseline_trace_sha256": base_game["trace_sha256"],
                    "candidate_trace_sha256": candidate_game["trace_sha256"],
                }
            )
    by_opponent = summarize_strata(by_opponent_vectors)
    by_seat = summarize_strata(by_seat_vectors)
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
        "by_seat": by_seat,
        "changed_cells": rows,
    }
    result["classification"] = classify_marginal(
        own_delta, trace_changes, by_opponent, by_seat
    )
    return result


def validate_receipts(receipts: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    source_closures: set[str] = set()
    candidate_closures: set[str] = set()
    scheduler_blobs: set[str] = set()
    for arm in RECEIPT_ARMS:
        receipt = receipts.get(arm)
        if not isinstance(receipt, Mapping):
            raise CompareError(f"missing receipt for {arm}")
        if receipt.get("schema_version") != 1 or receipt.get("operation") != OPERATION:
            raise CompareError(f"{arm} receipt identity mismatch")
        if receipt.get("arm") != arm or receipt.get("product_arms") != list(PRODUCT_ARMS):
            raise CompareError(f"{arm} receipt arm inventory mismatch")
        source = receipt.get("source")
        candidate = receipt.get("candidate")
        if not isinstance(source, Mapping) or not isinstance(candidate, Mapping):
            raise CompareError(f"{arm} receipt is malformed")
        if source.get("scheduler_git_blob_sha1") != EXPECTED_V2_SCHEDULER_BLOB:
            raise CompareError(f"{arm} source scheduler blob mismatch")
        expected_changed = [] if arm == "CONTROL" else ["scheduler.py"]
        expected_old_after = 1 if arm == "CONTROL" else 0
        expected_core_after = 0 if arm == "CONTROL" else 1
        if candidate.get("changed_files") != expected_changed:
            raise CompareError(f"{arm} changed-files boundary mismatch")
        if (
            candidate.get("old_occurrences_before") != 1
            or candidate.get("old_occurrences_after") != expected_old_after
            or candidate.get("core_occurrences_before") != 0
            or candidate.get("core_occurrences_after") != expected_core_after
        ):
            raise CompareError(f"{arm} target-expression cardinality mismatch")
        files = exact_int(source.get("files"), field=f"{arm}.source.files")
        if files <= 0:
            raise CompareError(f"{arm}.source.files must be positive")
        source_closures.add(
            sha256_text(source.get("closure_sha256"), field=f"{arm}.source.closure")
        )
        candidate_closures.add(
            sha256_text(
                candidate.get("closure_sha256"), field=f"{arm}.candidate.closure"
            )
        )
        scheduler_blobs.add(
            git_sha1(
                candidate.get("scheduler_git_blob_sha1"),
                field=f"{arm}.candidate.scheduler_blob",
            )
        )
    if len(source_closures) != 1:
        raise CompareError(f"source closures differ: {sorted(source_closures)!r}")
    if len(candidate_closures) != len(RECEIPT_ARMS):
        raise CompareError("candidate closures are not unique across arms")
    if len(scheduler_blobs) != len(RECEIPT_ARMS):
        raise CompareError("scheduler blobs are not unique across arms")
    source_closure = next(iter(source_closures))
    if receipts["CONTROL"]["candidate"]["closure_sha256"] != source_closure:
        raise CompareError("CONTROL candidate closure differs from frozen V2 source")
    if receipts["CONTROL"]["candidate"]["scheduler_git_blob_sha1"] != EXPECTED_V2_SCHEDULER_BLOB:
        raise CompareError("CONTROL scheduler blob differs from frozen V2 source")
    if sum(closure == source_closure for closure in candidate_closures) != 1:
        raise CompareError("source closure must occur exactly once as CONTROL")
    return {
        "source_closure_sha256": source_closure,
        "candidate_closure_sha256": {
            arm: receipts[arm]["candidate"]["closure_sha256"]
            for arm in RECEIPT_ARMS
        },
        "candidate_scheduler_git_blob_sha1": {
            arm: receipts[arm]["candidate"]["scheduler_git_blob_sha1"]
            for arm in RECEIPT_ARMS
        },
    }


def build_report(
    documents: dict[str, dict[str, Any]],
    receipts: dict[str, dict[str, Any]],
    *,
    expected_seeds: tuple[int, ...],
    git_head: str,
) -> dict[str, Any]:
    git_sha1(git_head, field="git_head")
    if tuple(documents) != ALL_ARMS:
        raise CompareError(f"document arm order mismatch: {tuple(documents)!r}")
    indexed = {
        arm: index_panel(document, arm=arm, expected_seeds=expected_seeds)
        for arm, document in documents.items()
    }
    provenance = comparable_provenance(documents["CONTROL"])
    for arm in ALL_ARMS[1:]:
        if comparable_provenance(documents[arm]) != provenance:
            raise CompareError(f"{arm} evaluator provenance differs from CONTROL")
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
    provenance_text = json.dumps(
        provenance, sort_keys=True, separators=(",", ":"), allow_nan=False
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
        "provenance": provenance,
        "provenance_sha256": hashlib.sha256(provenance_text.encode("utf-8")).hexdigest(),
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


def markdown(report: Mapping[str, Any]) -> str:
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
            f"Frozen V2 all-shed relative to V1-core: classification `{anchor['classification']}`, "
            f"mean own `{anchor['own_delta']['mean']:+.6f}`, median `{anchor['own_delta']['median']:+.6f}`, "
            f"margin mean `{anchor['margin_delta']['mean']:+.6f}`, "
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
    interaction = report["interaction_diagnostic"]
    lines.extend(
        [
            "",
            "## Conservative V3 handoff",
            "",
            f"- Recommended expansions: `{whitelist['recommended_expansions']}`",
            f"- Exclude on this panel: `{whitelist['exclude_on_this_panel']}`",
            f"- Unresolved: `{whitelist['unresolved']}`",
            f"- No observed effect: `{whitelist['no_observed_effect']}`",
            f"- Non-additivity residual: `{interaction['non_additivity_residual']:+.6f}` own-score points.",
            "",
            "Each product marginal is an exact one-factor arm. Classification requires non-regression "
            "in both opponent and both seat strata; the sum is not treated as additive.",
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


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    atomic_write(
        path,
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
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
        if (
            not expected_seeds
            or len(set(expected_seeds)) != len(expected_seeds)
            or any(isinstance(seed, bool) for seed in expected_seeds)
        ):
            raise CompareError("expected seeds must be non-empty and unique")
        documents = {
            arm: strict_object(args.results / f"{arm}.json") for arm in ALL_ARMS
        }
        receipts = {
            arm: strict_object(args.receipts / f"{arm}.json")
            for arm in RECEIPT_ARMS
        }
        report = build_report(
            documents, receipts, expected_seeds=expected_seeds, git_head=args.head
        )
        write_json(args.output, report)
        atomic_write(args.markdown, markdown(report))
        print(
            json.dumps(
                {
                    "verdict": report["verdict"],
                    "ranking": report["ranking_by_mean_own_delta"],
                    "whitelist": report["conservative_whitelist"],
                },
                sort_keys=True,
                allow_nan=False,
            )
        )
        return 0
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        report = invalid_report(reason, git_head=args.head)
        write_json(args.output, report)
        atomic_write(
            args.markdown,
            "# Titan V2 SELL target-domain product attribution\n\n"
            f"- Verdict: `INVALID`\n- Reason: `{reason}`\n",
        )
        print(json.dumps(report, sort_keys=True, allow_nan=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
