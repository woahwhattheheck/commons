# SPDX-License-Identifier: Apache-2.0
"""Matched-cell audit engine for TITAN's promotion gate."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from statistics import median
from typing import Any

from promotion_model import (
    SCHEMA,
    CellKey,
    PromotionData,
    PromotionPolicy,
    _key_json,
    _name,
    coverage_report,
    index_contestant,
)


def audit_promotion(
    rows: Sequence[Mapping[str, Any]], reference: str, challenger: str, *,
    expected_keys: set[CellKey] | None = None,
    policy: PromotionPolicy | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare a challenger to canonical on identical cells; reject on any unsafe gap."""
    reference, challenger = _name(reference, "reference"), _name(challenger, "challenger")
    if reference == challenger:
        raise PromotionData("reference and challenger must differ")
    policy = policy.normalized() if isinstance(policy, PromotionPolicy) else PromotionPolicy.from_mapping(policy)
    ref, chal = index_contestant(rows, reference), index_contestant(rows, challenger)
    coverage = coverage_report(ref, chal, expected_keys)
    target = set(expected_keys) if expected_keys is not None else set(ref) | set(chal)
    deltas, grouped = [], defaultdict(list)
    for key in sorted(set(ref) & set(chal) & target):
        item = {
            **_key_json(key),
            "reference_own_cash": ref[key]["own_cash"], "challenger_own_cash": chal[key]["own_cash"],
            "own_cash_delta": chal[key]["own_cash"] - ref[key]["own_cash"],
            "reference_margin": ref[key]["margin"], "challenger_margin": chal[key]["margin"],
            "margin_delta": chal[key]["margin"] - ref[key]["margin"],
        }
        deltas.append(item)
        grouped[(key[0], key[2])].append(item)

    reasons: list[dict[str, Any]] = []
    if not coverage["complete"]:
        reasons.append({
            "kind": "incomplete_coverage",
            "expected_cells": coverage["expected_cells"],
            "paired_cells": coverage["paired_cells"],
        })
    metrics = None
    strata = []
    if deltas:
        own = [row["own_cash_delta"] for row in deltas]
        margins = [row["margin_delta"] for row in deltas]
        worst = min(
            deltas,
            key=lambda row: (row["own_cash_delta"], row["opponent"], row["seed"], row["candidate_seat"]),
        )
        metrics = {
            "cells": len(deltas), "sum_own_cash_delta": sum(own),
            "mean_own_cash_delta": sum(own) / len(own), "median_own_cash_delta": median(own),
            "min_own_cash_delta": min(own), "max_own_cash_delta": max(own),
            "positive_cells": sum(value > 0 for value in own),
            "tie_cells": sum(value == 0 for value in own),
            "negative_cells": sum(value < 0 for value in own),
            "sum_margin_delta": sum(margins), "mean_margin_delta": sum(margins) / len(margins),
            "min_margin_delta": min(margins), "max_margin_delta": max(margins),
            "worst_own_cash_cell": worst,
        }
        for (opponent, seat), values in sorted(grouped.items()):
            cash = [row["own_cash_delta"] for row in values]
            margin = [row["margin_delta"] for row in values]
            strata.append({
                "opponent": opponent, "candidate_seat": seat, "cells": len(values),
                "mean_own_cash_delta": sum(cash) / len(cash), "min_own_cash_delta": min(cash),
                "mean_margin_delta": sum(margin) / len(margin),
                "negative_cells": sum(value < 0 for value in cash),
            })

        bad_cells = [row for row in deltas if row["own_cash_delta"] < -policy.max_cell_own_cash_drop]
        if bad_cells:
            bad_cells.sort(
                key=lambda row: (row["own_cash_delta"], row["opponent"], row["seed"], row["candidate_seat"])
            )
            reasons.append({
                "kind": "cell_own_cash_regression", "cells": len(bad_cells),
                "tolerated_drop": policy.max_cell_own_cash_drop, "worst": bad_cells[0],
            })
        bad_strata = [
            row for row in strata
            if row["mean_own_cash_delta"] < -policy.max_stratum_mean_own_cash_drop
        ]
        if bad_strata:
            reasons.append({
                "kind": "stratum_mean_own_cash_regression", "strata": bad_strata,
                "tolerated_drop": policy.max_stratum_mean_own_cash_drop,
            })
        checks = (
            ("insufficient_mean_own_cash_delta", metrics["mean_own_cash_delta"], policy.min_mean_own_cash_delta),
            ("insufficient_mean_margin_delta", metrics["mean_margin_delta"], policy.min_mean_margin_delta),
            ("insufficient_positive_cells", metrics["positive_cells"], policy.min_positive_cells),
        )
        reasons.extend(
            {"kind": kind, "actual": actual, "required": required}
            for kind, actual, required in checks if actual < required
        )
    else:
        reasons.append({"kind": "no_paired_cells"})

    eligible = coverage["complete"] and not reasons
    return {
        "schema": SCHEMA, "reference": reference, "challenger": challenger,
        "policy": policy.to_json(), "coverage": coverage, "metrics": metrics,
        "cell_deltas": deltas, "strata": strata, "reasons": reasons,
        "eligible": eligible, "verdict": "PROMOTE" if eligible else "REJECT",
    }
