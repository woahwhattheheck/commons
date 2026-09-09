# SPDX-License-Identifier: Apache-2.0
"""Pair complete control/ablation games and derive candidate-causal cell deltas."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from compare_common import CompareError
from compare_reports import _score, validate_games


def paired_cells(control_report: dict[str, Any], ablation_report: dict[str, Any]):
    controls = validate_games(control_report, "control")
    ablations = validate_games(ablation_report, "ablation")
    cells: list[dict[str, Any]] = []
    strata: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for key in sorted(controls):
        opponent, seed, seat = key
        control = controls[key]
        ablation = ablations[key]
        if control["steps"] != ablation["steps"]:
            raise CompareError(f"paired cell {key} completed different step counts")
        c_own, c_rival, c_margin = _score(control, seat)
        a_own, a_rival, a_margin = _score(ablation, seat)
        activated = control["candidate_action_sha256"] != ablation["candidate_action_sha256"]
        if not activated:
            if control["scores"] != ablation["scores"] or control["trace_sha256"] != ablation["trace_sha256"]:
                raise CompareError(
                    f"paired cell {key} changed outcome without a candidate-action change"
                )
        row = {
            "opponent": opponent,
            "seed": seed,
            "candidate_seat": seat,
            "candidate_action_changed": activated,
            "control_candidate_action_sha256": control["candidate_action_sha256"],
            "ablation_candidate_action_sha256": ablation["candidate_action_sha256"],
            "control_trace_sha256": control["trace_sha256"],
            "ablation_trace_sha256": ablation["trace_sha256"],
            "control_own": c_own,
            "ablation_own": a_own,
            "own_delta": a_own - c_own,
            "control_rival": c_rival,
            "ablation_rival": a_rival,
            "rival_delta": a_rival - c_rival,
            "control_margin": c_margin,
            "ablation_margin": a_margin,
            "margin_delta": a_margin - c_margin,
        }
        cells.append(row)
        strata[(opponent, seat)].append(row)

    return controls, ablations, cells, strata
