# SPDX-License-Identifier: Apache-2.0
"""Compute the own-cash-first paired causal verdict."""
from __future__ import annotations

import statistics
from typing import Any

from compare_cells import paired_cells
from compare_common import (
    CORE_EVALUATOR_GIT_BLOB,
    CompareError,
    ENGINE_REF,
    EXPECTED_CELLS,
    EXPECTED_OPPONENTS,
    EXPECTED_SEEDS,
    OPERATION,
    require_hex,
)
from compare_receipts import validate_receipt
from compare_reports import _paired_identity, validate_top_level

def analyze(
    control_report: dict[str, Any],
    ablation_report: dict[str, Any],
    control_receipt: dict[str, Any],
    ablation_receipt: dict[str, Any],
    head: str,
) -> dict[str, Any]:
    require_hex(head, 40, "checkout head")
    validate_receipt(control_receipt, "control", head)
    validate_receipt(ablation_receipt, "ablation", head)
    if control_receipt["source"] != ablation_receipt["source"]:
        raise CompareError("control and ablation do not share one frozen source receipt")
    if control_receipt["materialized"]["runtime_closure_sha256"] == ablation_receipt["materialized"]["runtime_closure_sha256"]:
        raise CompareError("control and ablation runtime closures are aliased")
    if control_receipt["entry"]["sha256"] == ablation_receipt["entry"]["sha256"]:
        raise CompareError("control and ablation generated entries are aliased")

    validate_top_level(control_report, "control")
    validate_top_level(ablation_report, "ablation")
    _paired_identity(control_report, ablation_report)
    if control_report["candidate"]["sha256"] != control_receipt["entry"]["sha256"]:
        raise CompareError("control evaluator entry is detached from materialization receipt")
    if ablation_report["candidate"]["sha256"] != ablation_receipt["entry"]["sha256"]:
        raise CompareError("ablation evaluator entry is detached from materialization receipt")

    controls, ablations, cells, strata = paired_cells(control_report, ablation_report)
    own_deltas = [row["own_delta"] for row in cells]
    margin_deltas = [row["margin_delta"] for row in cells]
    changed = sum(row["candidate_action_changed"] for row in cells)
    positive = sum(delta > 0 for delta in own_deltas)
    negative = sum(delta < 0 for delta in own_deltas)
    stratum_rows = []
    for (opponent, seat), rows in sorted(strata.items()):
        stratum_rows.append(
            {
                "opponent": opponent,
                "candidate_seat": seat,
                "cells": len(rows),
                "changed_actions": sum(row["candidate_action_changed"] for row in rows),
                "mean_own_delta": statistics.mean(row["own_delta"] for row in rows),
                "mean_margin_delta": statistics.mean(row["margin_delta"] for row in rows),
            }
        )
    mean_own = statistics.mean(own_deltas)
    median_own = statistics.median(own_deltas)
    mean_margin = statistics.mean(margin_deltas)
    all_strata_nonnegative = all(row["mean_own_delta"] >= 0 for row in stratum_rows)
    criteria = {
        "candidate_action_activation": changed > 0,
        "positive_mean_own_cash": mean_own > 0,
        "nonnegative_median_own_cash": median_own >= 0,
        "positive_cells_at_least_negative_cells": positive >= negative,
        "positive_mean_margin": mean_margin > 0,
        "nonnegative_own_cash_in_every_opponent_seat_stratum": all_strata_nonnegative,
    }
    if not criteria["candidate_action_activation"]:
        verdict = "NO_ACTIVATION"
    elif all(criteria.values()):
        verdict = "UPSIDE_SCREEN"
    else:
        verdict = "REGRESSION"

    return {
        "schema_version": 1,
        "operation": OPERATION,
        "checkout_head": head,
        "verdict": verdict,
        "boundary": "development_causal_screen_not_promotion_or_leaderboard_evidence",
        "identities": {
            "source_runtime_closure_sha256": control_receipt["source"]["runtime_closure_sha256"],
            "control_runtime_closure_sha256": control_receipt["materialized"]["runtime_closure_sha256"],
            "ablation_runtime_closure_sha256": ablation_receipt["materialized"]["runtime_closure_sha256"],
            "control_entry_sha256": control_receipt["entry"]["sha256"],
            "ablation_entry_sha256": ablation_receipt["entry"]["sha256"],
            "control_invocation_id": control_report["invocation_id"],
            "ablation_invocation_id": ablation_report["invocation_id"],
            "engine_ref": ENGINE_REF,
            "core_evaluator_git_blob": CORE_EVALUATOR_GIT_BLOB,
            "activation_overlay_sha256": control_report["activation_overlay"]["sha256"],
        },
        "grid": {
            "seeds": list(EXPECTED_SEEDS),
            "opponents": list(EXPECTED_OPPONENTS),
            "seats": [0, 1],
            "paired_cells": EXPECTED_CELLS,
            "complete_control_games": len(controls),
            "complete_ablation_games": len(ablations),
        },
        "summary": {
            "candidate_action_changed_cells": changed,
            "positive_own_cells": positive,
            "zero_own_cells": len(cells) - positive - negative,
            "negative_own_cells": negative,
            "mean_own_delta": mean_own,
            "median_own_delta": median_own,
            "minimum_own_delta": min(own_deltas),
            "maximum_own_delta": max(own_deltas),
            "mean_margin_delta": mean_margin,
        },
        "criteria": criteria,
        "strata": stratum_rows,
        "cells": cells,
    }
