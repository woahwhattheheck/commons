#!/usr/bin/env python3
"""Pre-registered low-complexity selector fitter for the TITAN V5 P04 route matrix.

The fitting procedure is intentionally frozen before R00-R12 outcome inspection.
It can choose only an incumbent-preserving global override or one equality
predicate over the public step-144 feature signature already defined by #13478.
The discovery matrix can nominate a rule; only fresh held-out native games can
make that nominated rule policy-ready.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable

from p04_route_ranker import (
    ALL_PLANS,
    FINAL_PLAN_STEP,
    NATURAL_STEP144_PLANS,
    PRODUCTION_ARCHIVE_SHA256,
    ROUTER_SOURCE_SHA256,
    ROUTE_STEP,
    SCHEMA as RANKER_SCHEMA,
    SOURCE_CENSUS_COMMIT,
    canonical_public_snapshot,
    expected_incumbent_plan,
    public_feature_signature,
)

SCHEMA = "titan-v5-p04-preregistered-selector/v1"
ALLOWED_FEATURES = (
    "shop_pair",
    "first_two_yarn_count",
    "wool_vs_milk_price",
    "wool_vs_milk_inventory",
    "wheat_vs_carrot_price",
    "rival_livestock_leader",
    "rival_crop_leader",
)
OVERRIDE_PLANS = tuple(NATURAL_STEP144_PLANS)

SPEC = {
    "schema": "titan-v5-p04-selector-preregistration-spec/v1",
    "input": {
        "ranker_schema": RANKER_SCHEMA,
        "production_archive_sha256": PRODUCTION_ARCHIVE_SHA256,
        "router_source_sha256": ROUTER_SOURCE_SHA256,
        "route_step": ROUTE_STEP,
        "forced_terminal_plan_step": FINAL_PLAN_STEP,
        "allowed_features": list(ALLOWED_FEATURES),
        "forbidden_identifiers": ["seed", "opponent", "seat", "snapshot_sha256"],
    },
    "rule_class": {
        "fallback": "source_recomputed_incumbent_plan",
        "forms": [
            "always_override_with_one_natural_plan",
            "one_allowed_feature_equals_one_training_observed_value_then_override_with_one_natural_plan",
        ],
        "override_plans": list(OVERRIDE_PLANS),
        "max_predicates": 1,
        "plan_2_allowed": False,
    },
    "discovery_qualification": {
        "minimum_engaged_groups": 2,
        "require_two_distinct_seeds_when_available": True,
        "require_two_distinct_opponents_when_available": True,
        "require_both_seats_when_available": True,
        "failure_groups": 0,
        "minimum_delta_margin_vs_incumbent": 0.0,
        "minimum_delta_own_vs_incumbent": 0.0,
        "strictly_positive_total_margin_delta": True,
    },
    "selection_order": [
        "max_min_delta_margin",
        "max_min_delta_own",
        "max_mean_delta_margin",
        "max_mean_delta_own",
        "max_engaged_groups",
        "prefer_global_over_conditional",
        "lowest_lexicographic_predicate",
        "lowest_plan_id",
    ],
    "activation": {
        "discovery_can_only_nominate": True,
        "fresh_heldout_native_required": True,
        "heldout_rule_must_be_byte_identical": True,
        "default_off_until_separate_promotion": True,
    },
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


PREREGISTERED_SPEC_SHA256 = "c0d57d3b20aba4ce8ecca7cc07ac3cf56bd7f7aeb9260efe1f6519d62aa8719e"
if _sha256(SPEC) != PREREGISTERED_SPEC_SHA256:
    raise RuntimeError("preregistered selector SPEC drift")
SPEC_SHA256 = PREREGISTERED_SPEC_SHA256


def preregistration() -> dict[str, Any]:
    return {"spec": SPEC, "spec_sha256": SPEC_SHA256}


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{label} must be finite")
    return out


def _feature_value(value: Any, label: str) -> str | int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must not be bool")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"{label} must be a nonempty string or integer")


def _validate_authority(report: dict[str, Any]) -> None:
    if report.get("schema") != RANKER_SCHEMA:
        raise ValueError("route-ranker schema mismatch")
    authority = report.get("authority")
    expected = {
        "production_archive_sha256": PRODUCTION_ARCHIVE_SHA256,
        "router_source_sha256": ROUTER_SOURCE_SHA256,
        "source_census_commit": SOURCE_CENSUS_COMMIT,
        "route_step": ROUTE_STEP,
        "forced_terminal_plan_step": FINAL_PLAN_STEP,
    }
    if authority != expected:
        raise ValueError("route-ranker authority mismatch")
    if report.get("policy_ready") is not False:
        raise ValueError("discovery report must remain policy_ready=false")


def _normalize_group(group: Any) -> dict[str, Any]:
    if not isinstance(group, dict):
        raise ValueError("route-ranker group must be an object")
    for name in ("seed", "opponent", "seat", "features", "incumbent_plan", "plans"):
        if name not in group:
            raise ValueError(f"route-ranker group missing {name}")
    seed = group["seed"]
    seat = group["seat"]
    opponent = group["opponent"]
    incumbent = group["incumbent_plan"]
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be integer")
    if not isinstance(opponent, str) or not opponent:
        raise ValueError("opponent must be nonempty string")
    if isinstance(seat, bool) or seat not in (0, 1):
        raise ValueError("seat must be 0 or 1")
    if isinstance(incumbent, bool) or incumbent not in ALL_PLANS:
        raise ValueError("incumbent_plan must be 0..12")

    features = group["features"]
    if not isinstance(features, dict) or set(features) != set(ALLOWED_FEATURES):
        raise ValueError("feature signature does not match preregistered public surface")
    clean_features = {name: _feature_value(features[name], f"features.{name}") for name in ALLOWED_FEATURES}

    plans = group["plans"]
    if not isinstance(plans, list) or len(plans) != len(ALL_PLANS):
        raise ValueError("each discovery group must contain exactly 13 plan rows")
    by_plan: dict[int, dict[str, Any]] = {}
    for row in plans:
        if not isinstance(row, dict):
            raise ValueError("plan row must be object")
        plan = row.get("plan")
        if isinstance(plan, bool) or plan not in ALL_PLANS or plan in by_plan:
            raise ValueError("plan rows must contain each plan exactly once")
        failures = row.get("failures", [])
        if not isinstance(failures, list) or not all(isinstance(x, str) for x in failures):
            raise ValueError("plan failures must be a list of strings")
        by_plan[plan] = {
            "plan": plan,
            "delta_margin_vs_incumbent": _finite(row.get("delta_margin_vs_incumbent"), "delta_margin_vs_incumbent"),
            "delta_own_vs_incumbent": _finite(row.get("delta_own_vs_incumbent"), "delta_own_vs_incumbent"),
            "failures": list(failures),
        }
    if set(by_plan) != set(ALL_PLANS):
        raise ValueError("plan rows do not cover 0..12")
    base = by_plan[incumbent]
    if base["delta_margin_vs_incumbent"] != 0 or base["delta_own_vs_incumbent"] != 0:
        raise ValueError("incumbent deltas must be zero")
    return {
        "seed": seed,
        "opponent": opponent,
        "seat": seat,
        "features": clean_features,
        "incumbent_plan": incumbent,
        "plans": by_plan,
    }


def validate_discovery_report(report: Any) -> list[dict[str, Any]]:
    if not isinstance(report, dict):
        raise ValueError("discovery report must be an object")
    _validate_authority(report)
    groups_raw = report.get("groups")
    if not isinstance(groups_raw, list) or not groups_raw:
        raise ValueError("discovery report groups must be a nonempty list")
    groups = [_normalize_group(group) for group in groups_raw]
    keys = [(g["seed"], g["opponent"], g["seat"]) for g in groups]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate seed/opponent/seat discovery group")
    if report.get("complete_snapshot_groups") != len(groups):
        raise ValueError("complete_snapshot_groups mismatch")
    return groups


def _rule_key(rule: dict[str, Any]) -> tuple[Any, ...]:
    pred = rule.get("predicate")
    if pred is None:
        return (0, "", "", rule["override_plan"])
    return (1, pred["feature"], json.dumps(pred["value"], sort_keys=True), rule["override_plan"])


def enumerate_rules(groups: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = list(groups)
    values: dict[str, set[str | int]] = {name: set() for name in ALLOWED_FEATURES}
    for group in groups:
        for name in ALLOWED_FEATURES:
            values[name].add(group["features"][name])
    rules = []
    for plan in OVERRIDE_PLANS:
        rules.append({"predicate": None, "override_plan": plan})
    for feature in ALLOWED_FEATURES:
        for value in sorted(values[feature], key=lambda x: (type(x).__name__, repr(x))):
            for plan in OVERRIDE_PLANS:
                rules.append({"predicate": {"feature": feature, "value": value}, "override_plan": plan})
    return sorted(rules, key=_rule_key)


def selected_plan_for_features(features: dict[str, Any], incumbent_plan: int, rule: dict[str, Any]) -> int:
    plan = rule.get("override_plan")
    if isinstance(plan, bool) or plan not in OVERRIDE_PLANS:
        raise ValueError("override plan is outside preregistered natural-plan set")
    pred = rule.get("predicate")
    if pred is None:
        return plan
    if not isinstance(pred, dict) or set(pred) != {"feature", "value"}:
        raise ValueError("predicate must be null or one feature equality")
    feature = pred["feature"]
    if feature not in ALLOWED_FEATURES:
        raise ValueError("predicate uses non-preregistered feature")
    return plan if features[feature] == pred["value"] else incumbent_plan


def select_plan(snapshot: Any, rule: dict[str, Any]) -> int:
    canonical = canonical_public_snapshot(snapshot)
    incumbent = expected_incumbent_plan(canonical["first_two_shops"])
    if canonical["incumbent_plan"] != incumbent:
        raise ValueError("snapshot incumbent does not match source mapping")
    return selected_plan_for_features(public_feature_signature(canonical), incumbent, rule)


def _coverage_floor(total_distinct: int) -> int:
    return min(2, total_distinct)


def evaluate_rule(groups: Iterable[dict[str, Any]], rule: dict[str, Any]) -> dict[str, Any]:
    groups = list(groups)
    engaged = []
    for group in groups:
        selected = selected_plan_for_features(group["features"], group["incumbent_plan"], rule)
        if selected == group["incumbent_plan"]:
            continue
        row = group["plans"][selected]
        engaged.append({
            "seed": group["seed"],
            "opponent": group["opponent"],
            "seat": group["seat"],
            "delta_margin": row["delta_margin_vs_incumbent"],
            "delta_own": row["delta_own_vs_incumbent"],
            "failures": row["failures"],
        })

    seeds = {g["seed"] for g in groups}
    opponents = {g["opponent"] for g in groups}
    seats = {g["seat"] for g in groups}
    engaged_seeds = {g["seed"] for g in engaged}
    engaged_opponents = {g["opponent"] for g in engaged}
    engaged_seats = {g["seat"] for g in engaged}
    dm = [g["delta_margin"] for g in engaged]
    do = [g["delta_own"] for g in engaged]
    failures = sum(bool(g["failures"]) for g in engaged)
    qualified = bool(engaged)
    qualified = qualified and len(engaged) >= SPEC["discovery_qualification"]["minimum_engaged_groups"]
    qualified = qualified and len(engaged_seeds) >= _coverage_floor(len(seeds))
    qualified = qualified and len(engaged_opponents) >= _coverage_floor(len(opponents))
    qualified = qualified and len(engaged_seats) >= _coverage_floor(len(seats))
    qualified = qualified and failures == 0
    qualified = qualified and min(dm, default=float("-inf")) >= 0
    qualified = qualified and min(do, default=float("-inf")) >= 0
    qualified = qualified and sum(dm) > 0
    return {
        "rule": rule,
        "qualified": qualified,
        "engaged_groups": len(engaged),
        "engaged_distinct_seeds": len(engaged_seeds),
        "engaged_distinct_opponents": len(engaged_opponents),
        "engaged_distinct_seats": len(engaged_seats),
        "failure_groups": failures,
        "min_delta_margin": min(dm) if dm else None,
        "min_delta_own": min(do) if do else None,
        "mean_delta_margin": statistics.fmean(dm) if dm else None,
        "mean_delta_own": statistics.fmean(do) if do else None,
        "total_delta_margin": sum(dm),
        "total_delta_own": sum(do),
    }


def _selection_key(result: dict[str, Any]) -> tuple[Any, ...]:
    rule = result["rule"]
    pred = rule.get("predicate")
    # min() uses this key: negate performance terms, then prefer simpler/lower lexical rules.
    return (
        -result["min_delta_margin"],
        -result["min_delta_own"],
        -result["mean_delta_margin"],
        -result["mean_delta_own"],
        -result["engaged_groups"],
        0 if pred is None else 1,
        "" if pred is None else pred["feature"],
        "" if pred is None else json.dumps(pred["value"], sort_keys=True),
        rule["override_plan"],
    )


def fit_selector(report: Any) -> dict[str, Any]:
    groups = validate_discovery_report(report)
    evaluated = [evaluate_rule(groups, rule) for rule in enumerate_rules(groups)]
    qualified = [item for item in evaluated if item["qualified"]]
    selected = min(qualified, key=_selection_key) if qualified else None
    result = {
        "schema": SCHEMA,
        "preregistration_spec_sha256": SPEC_SHA256,
        "discovery_report_sha256": _sha256(report),
        "authority": SPEC["input"],
        "discovery_groups": len(groups),
        "candidate_rules_evaluated": len(evaluated),
        "qualified_rules": len(qualified),
        "selected": selected,
        "policy_ready": False,
        "composer_ready": False,
        "heldout_required": selected is not None,
        "hold_reason": (
            "Discovery may nominate only the byte-frozen preregistered rule. Fresh held-out native games "
            "must validate that exact rule before any runtime component or promotion decision."
            if selected is not None else
            "No preregistered low-complexity rule met the discovery non-regression and coverage gate."
        ),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, nargs="?", help="Completed #13478 p04-report.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--print-preregistration", action="store_true")
    args = parser.parse_args()
    if args.print_preregistration:
        payload = preregistration()
    else:
        if args.report is None:
            parser.error("report is required unless --print-preregistration is used")
        payload = fit_selector(json.loads(args.report.read_text(encoding="utf-8")))
    encoded = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(encoded)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
