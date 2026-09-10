#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Seed-clustered, tail-bounded economics for TITAN promotion evidence."""
from __future__ import annotations

from promotion_core import *
from promotion_seed import *
from promotion_manifest import *
from promotion_trajectory import *

POLICY_KEYS = {
    "schema_version",
    "min_global_mean_own_delta",
    "min_global_mean_margin_delta",
    "min_opponent_seat_mean_own_delta",
    "min_opponent_seat_mean_margin_delta",
    "min_cell_own_delta",
    "min_cell_margin_delta",
    "lower_quantile",
    "min_lower_quantile_own_delta",
    "min_lower_quantile_margin_delta",
    "min_seed_mean_own_delta",
    "min_seed_mean_margin_delta",
    "min_positive_seed_clusters",
    "max_negative_seed_clusters",
    "max_seed_sign_tail",
    "require_zero_new_losses",
    "require_zero_lost_wins",
    "require_zero_outcome_regressions",
}


def validate_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, Mapping):
        raise PromotionClosureError("promotion policy must be an object")
    require_keys(policy, POLICY_KEYS, "promotion policy")
    if policy["schema_version"] != POLICY_SCHEMA:
        raise PromotionClosureError("unsupported promotion policy schema")
    normalized = {"schema_version": POLICY_SCHEMA}
    for key in (
        "min_global_mean_own_delta",
        "min_global_mean_margin_delta",
        "min_opponent_seat_mean_own_delta",
        "min_opponent_seat_mean_margin_delta",
        "min_cell_own_delta",
        "min_cell_margin_delta",
        "min_lower_quantile_own_delta",
        "min_lower_quantile_margin_delta",
        "min_seed_mean_own_delta",
        "min_seed_mean_margin_delta",
        "max_seed_sign_tail",
    ):
        normalized[key] = finite(policy[key], f"promotion policy {key}")
    q = finite(policy["lower_quantile"], "promotion policy lower_quantile")
    if not 0 < q <= 0.5:
        raise PromotionClosureError("lower_quantile must be in (0, 0.5]")
    normalized["lower_quantile"] = q
    normalized["min_positive_seed_clusters"] = true_int(
        policy["min_positive_seed_clusters"], "min_positive_seed_clusters", minimum=1
    )
    normalized["max_negative_seed_clusters"] = true_int(
        policy["max_negative_seed_clusters"], "max_negative_seed_clusters", minimum=0
    )
    if not 0 <= normalized["max_seed_sign_tail"] <= 1:
        raise PromotionClosureError("max_seed_sign_tail must be in [0, 1]")
    for key in (
        "require_zero_new_losses",
        "require_zero_lost_wins",
        "require_zero_outcome_regressions",
    ):
        if type(policy[key]) is not bool:
            raise PromotionClosureError(f"promotion policy {key} must be boolean")
        normalized[key] = policy[key]
    return normalized


def _mean(values: Sequence[float]) -> float:
    return statistics.fmean(values)


def _lower_quantile(values: Sequence[float], q: float) -> float:
    if not values:
        raise PromotionClosureError("cannot compute quantile of empty values")
    ordered = sorted(float(value) for value in values)
    # Conservative nearest-rank lower quantile.  q=0.10 with n=96 selects rank 10.
    rank = max(1, math.ceil(q * len(ordered)))
    return ordered[rank - 1]


def _validate_panel_header(
    panel: Mapping[str, Any], policy: Mapping[str, Any], prior_ledger: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], list[int], list[str]]:
    if not isinstance(panel, Mapping):
        raise PromotionClosureError("trajectory panel must be an object")
    require_keys(panel, PANEL_KEYS, "trajectory panel")
    if panel["schema_version"] != TRAJECTORY_SCHEMA:
        raise PromotionClosureError("unsupported trajectory panel schema")
    operation = nonempty_string(panel["operation"], "panel operation")
    hypothesis = nonempty_string(panel["hypothesis"], "panel hypothesis")
    head = sha40(panel["head"], "panel head")
    normalized_policy = validate_policy(policy)
    policy_sha = json_sha256(normalized_policy)
    if sha64(panel["policy_sha256"], "panel policy SHA-256") != policy_sha:
        raise PromotionClosureError("panel policy digest differs from precommitted policy")
    for key in ("engine_sha256", "evaluator_sha256", "loader_sha256"):
        sha64(panel[key], f"panel {key}")

    raw_seeds = panel["seeds"]
    if not isinstance(raw_seeds, list) or not raw_seeds:
        raise PromotionClosureError("panel seeds must be a nonempty list")
    seeds = [true_int(seed, "panel seed", minimum=0) for seed in raw_seeds]
    if len(seeds) != len(set(seeds)):
        raise PromotionClosureError("panel seeds contain duplicates")

    raw_opponents = panel["opponents"]
    if not isinstance(raw_opponents, Mapping) or not raw_opponents:
        raise PromotionClosureError("panel opponents must be a nonempty object")
    opponents: list[str] = []
    for label, raw_manifest in raw_opponents.items():
        label = nonempty_string(label, "opponent label")
        opponents.append(label)
        validate_closure_receipt(raw_manifest, f"opponent closure {label}")
    if len(opponents) != len(set(opponents)):
        raise PromotionClosureError("panel opponent labels are duplicated")

    closures = panel["closures"]
    if not isinstance(closures, Mapping):
        raise PromotionClosureError("panel closures must be an object")
    require_keys(closures, {"control", "candidate"}, "panel closures")
    control_closure = validate_closure_receipt(closures["control"], "control closure")
    candidate_closure = validate_closure_receipt(closures["candidate"], "candidate closure")
    if control_closure["closure_sha256"] == candidate_closure["closure_sha256"]:
        raise PromotionClosureError("control and candidate closure manifests are identical")

    run = assert_fresh_spend(prior_ledger, panel["run"])
    if run["operation"] != operation or run["hypothesis"] != hypothesis:
        raise PromotionClosureError("run receipt operation/hypothesis differs from panel")
    if run["head"] != head or run["policy_sha256"] != policy_sha:
        raise PromotionClosureError("run receipt head/policy differs from panel")
    if run["seeds"] != seeds:
        raise PromotionClosureError("run receipt seeds differ from panel")
    return normalized_policy, run, seeds, sorted(opponents)


