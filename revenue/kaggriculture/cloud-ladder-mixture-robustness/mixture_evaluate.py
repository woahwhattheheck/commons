"""Release verdict logic for the TITAN ladder-mixture gate."""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Any

from mixture_common import Cell, OUTCOME_RANK, RECEIPT_SCHEMA, _mean, _quantity, _sha256
from mixture_optimize import _worst_case_mixture
from mixture_parse import _parse_document

def evaluate(document: Any) -> dict[str, Any]:
    parsed = _parse_document(document)
    cells_by_family_seed: dict[str, dict[str, list[Cell]]] = defaultdict(lambda: defaultdict(list))
    for cell in parsed.cells:
        cells_by_family_seed[cell.family][cell.seed].append(cell)

    family_summaries: dict[str, dict[str, Any]] = {}
    family_own_effects: dict[str, Fraction] = {}
    family_margin_effects: dict[str, Fraction] = {}
    uncalibrated: list[str] = []
    insufficient: list[dict[str, Any]] = []
    evidence_failures: list[dict[str, Any]] = []
    outcome_regressions: list[dict[str, Any]] = []
    tail_failures: list[dict[str, Any]] = []
    any_action_change = False
    any_economic_change = False

    if parsed.normalized["panel"]["causality_status"] != "CAUSAL_PASS":
        evidence_failures.append(
            {
                "reason": "panel_causality_status_not_pass",
                "status": parsed.normalized["panel"]["causality_status"],
            }
        )

    for family in parsed.families:
        if parsed.calibration_status[family.name] != "CALIBRATION_PASS":
            uncalibrated.append(family.name)
        seed_rows: list[dict[str, Any]] = []
        seed_own_values: list[Fraction] = []
        seed_margin_values: list[Fraction] = []
        family_worsened = 0
        family_lost_wins = 0
        family_new_losses = 0
        for seed, cells in sorted(cells_by_family_seed[family.name].items()):
            own_delta = _mean([cell.own_delta for cell in cells])
            margin_delta = _mean([cell.margin_delta for cell in cells])
            seed_own_values.append(own_delta)
            seed_margin_values.append(margin_delta)
            worsened = 0
            lost_wins = 0
            new_losses = 0
            for cell in cells:
                any_action_change = any_action_change or cell.action_changed
                changed = any(value != 0 for value in (cell.own_delta, cell.margin_delta))
                any_economic_change = any_economic_change or changed
                if changed and not cell.action_changed:
                    evidence_failures.append(
                        {
                            "reason": "score_delta_without_action_change",
                            "opponent_family": family.name,
                            "seed": seed,
                            "candidate_seat": cell.seat,
                        }
                    )
                if changed and not cell.trace_changed:
                    evidence_failures.append(
                        {
                            "reason": "score_delta_without_trace_change",
                            "opponent_family": family.name,
                            "seed": seed,
                            "candidate_seat": cell.seat,
                        }
                    )
                if OUTCOME_RANK[cell.candidate_outcome] < OUTCOME_RANK[cell.incumbent_outcome]:
                    worsened += 1
                    outcome_regressions.append(
                        {
                            "opponent_family": family.name,
                            "seed": seed,
                            "candidate_seat": cell.seat,
                            "incumbent_outcome": cell.incumbent_outcome,
                            "candidate_outcome": cell.candidate_outcome,
                        }
                    )
                if cell.incumbent_outcome == "W" and cell.candidate_outcome != "W":
                    lost_wins += 1
                if cell.incumbent_outcome != "L" and cell.candidate_outcome == "L":
                    new_losses += 1
            family_worsened += worsened
            family_lost_wins += lost_wins
            family_new_losses += new_losses
            if own_delta < parsed.minimum_seed_own_delta:
                tail_failures.append(
                    {
                        "reason": "seed_own_below_floor",
                        "opponent_family": family.name,
                        "seed": seed,
                        "observed": _quantity(own_delta),
                        "floor": _quantity(parsed.minimum_seed_own_delta),
                    }
                )
            if margin_delta < parsed.minimum_seed_margin_delta:
                tail_failures.append(
                    {
                        "reason": "seed_margin_below_floor",
                        "opponent_family": family.name,
                        "seed": seed,
                        "observed": _quantity(margin_delta),
                        "floor": _quantity(parsed.minimum_seed_margin_delta),
                    }
                )
            seed_rows.append(
                {
                    "seed": seed,
                    "seat_count": len(cells),
                    "own_delta": _quantity(own_delta),
                    "margin_delta": _quantity(margin_delta),
                    "worsened_outcomes": worsened,
                    "lost_wins": lost_wins,
                    "new_losses": new_losses,
                    "action_changed": any(cell.action_changed for cell in cells),
                    "trace_changed": any(cell.trace_changed for cell in cells),
                }
            )
        seed_count = len(seed_rows)
        if seed_count < parsed.minimum_seed_clusters:
            insufficient.append(
                {
                    "opponent_family": family.name,
                    "observed_seed_clusters": seed_count,
                    "minimum_seed_clusters": parsed.minimum_seed_clusters,
                }
            )
        family_mean_own = _mean(seed_own_values)
        family_mean_margin = _mean(seed_margin_values)
        if seed_count >= 2:
            sum_own = sum(seed_own_values, Fraction(0))
            sum_margin = sum(seed_margin_values, Fraction(0))
            loo_own = [(sum_own - value) / (seed_count - 1) for value in seed_own_values]
            loo_margin = [(sum_margin - value) / (seed_count - 1) for value in seed_margin_values]
            own_floor = min(loo_own)
            margin_floor = min(loo_margin)
        else:
            own_floor = family_mean_own
            margin_floor = family_mean_margin
        family_own_effects[family.name] = own_floor
        family_margin_effects[family.name] = margin_floor
        family_summaries[family.name] = {
            "hosted_count": family.hosted_count,
            "nominal_weight": _quantity(family.nominal),
            "min_weight": _quantity(family.lower),
            "max_weight": _quantity(family.upper),
            "calibration_status": parsed.calibration_status[family.name],
            "seed_clusters": seed_rows,
            "seed_cluster_count": seed_count,
            "mean_own_delta": _quantity(family_mean_own),
            "mean_margin_delta": _quantity(family_mean_margin),
            "leave_one_seed_out_own_floor": _quantity(own_floor),
            "leave_one_seed_out_margin_floor": _quantity(margin_floor),
            "minimum_seed_own_delta": _quantity(min(seed_own_values)),
            "minimum_seed_margin_delta": _quantity(min(seed_margin_values)),
            "worsened_outcomes": family_worsened,
            "lost_wins": family_lost_wins,
            "new_losses": family_new_losses,
        }

    own_robustness = _worst_case_mixture(family_own_effects, parsed.families, parsed.total_variation_radius)
    margin_robustness = _worst_case_mixture(family_margin_effects, parsed.families, parsed.total_variation_radius)
    own_worst = Fraction(own_robustness["worst_case_value"]["fraction"])
    margin_worst = Fraction(margin_robustness["worst_case_value"]["fraction"])
    if parsed.strict_worst_case:
        own_pass = own_worst > 0
        margin_pass = margin_worst > 0
    else:
        own_pass = own_worst >= 0
        margin_pass = margin_worst >= 0

    reasons: list[dict[str, Any]] = []
    if uncalibrated:
        reasons.append({"reason": "uncalibrated_families", "families": sorted(uncalibrated)})
    reasons.extend({"reason": "insufficient_seed_clusters", **row} for row in insufficient)
    reasons.extend(evidence_failures)
    if outcome_regressions:
        reasons.append({"reason": "worsened_outcomes", "count": len(outcome_regressions)})
    reasons.extend(tail_failures)
    if not any_economic_change:
        reasons.append({
            "reason": "no_terminal_economic_change",
            "action_changed": any_action_change,
        })
    if not own_pass:
        reasons.append(
            {
                "reason": "worst_case_own_not_admissible",
                "observed": own_robustness["worst_case_value"],
                "strict": parsed.strict_worst_case,
            }
        )
    if not margin_pass:
        reasons.append(
            {
                "reason": "worst_case_margin_not_admissible",
                "observed": margin_robustness["worst_case_value"],
                "strict": parsed.strict_worst_case,
            }
        )

    if uncalibrated:
        verdict = "BLOCK_UNCALIBRATED"
    elif insufficient:
        verdict = "MORE_EVIDENCE_REQUIRED"
    elif evidence_failures:
        verdict = "BLOCK_EVIDENCE"
    elif not any_action_change and not any_economic_change:
        verdict = "INACTIVE"
    elif outcome_regressions or tail_failures or not any_economic_change or not own_pass or not margin_pass:
        verdict = "ROBUST_HOLD"
    else:
        verdict = "ROBUST_ADVANCE"

    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "verdict": verdict,
        "claim_id": "TITAN-V3-LADDER-MIXTURE-ROBUST-PROMOTION-20260910-01",
        "normalized_input_sha256": _sha256(parsed.normalized),
        "release_pair": parsed.normalized["release_pair"],
        "source_closure": {
            "panel_receipt_sha256": parsed.normalized["panel"]["panel_receipt_sha256"],
            "engine_sha256": parsed.normalized["panel"]["engine_sha256"],
            "evaluator_sha256": parsed.normalized["panel"]["evaluator_sha256"],
            "loader_sha256": parsed.normalized["panel"]["loader_sha256"],
            "causality_receipt_sha256": parsed.normalized["panel"]["causality_receipt_sha256"],
            "calibration_registry_receipt_sha256": parsed.normalized["calibration"]["registry_receipt_sha256"],
            "hosted_snapshot_sha256": parsed.normalized["mixture"]["snapshot_sha256"],
        },
        "evidence": {
            "cell_count": len(parsed.cells),
            "family_count": len(parsed.families),
            "expected_seats": list(parsed.expected_seats),
            "minimum_seed_clusters": parsed.minimum_seed_clusters,
            "minimum_seed_own_delta": _quantity(parsed.minimum_seed_own_delta),
            "minimum_seed_margin_delta": _quantity(parsed.minimum_seed_margin_delta),
            "family_summaries": family_summaries,
            "outcome_regressions": outcome_regressions,
            "evidence_failures": evidence_failures,
        },
        "mixture_robustness": {
            "total_variation_radius": _quantity(parsed.total_variation_radius),
            "own_cash": own_robustness,
            "margin": margin_robustness,
        },
        "reasons": reasons,
        "authority": {
            "policy_mutation": False,
            "game_execution": False,
            "provider_mutation": False,
            "kaggle_mutation": False,
            "promotion_authority": False,
            "consumer": "T08 one-tree integration / release authority",
        },
    }
    receipt["receipt_sha256"] = _sha256(receipt)
    return receipt
