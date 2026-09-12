# SPDX-License-Identifier: Apache-2.0
"""Evidence-only current-ABI H3/S420 sale-timing experiment for TITAN V5.

This module does not define a second seller. It temporarily narrows the
already-selected ``frozen_selected`` seller's baseline lookahead from the
current inherited horizon to three turns and, for the combined H3+S420 arm,
vetoes only optional temporal sale advances at/after an absolute step.

The adapter deliberately preserves the current seller's:
* producer route, public event extensions and feasibility checks;
* inherited/reference sale schedule;
* minimum-now funding floor;
* forced-feasibility rescue;
* sale materializer and every non-sale action.

Production defaults/configuration are never changed by this research helper.
"""

from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any

BASELINE_HORIZON = 3
SUPPRESS_AFTER_STEP = 420


def _plain_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _normalized_plan(plan: Any) -> tuple[tuple[int, int], ...]:
    """Normalize one exact dated quantity schedule or raise ValueError."""
    if not isinstance(plan, Sequence) or isinstance(plan, (str, bytes, bytearray)):
        raise ValueError("plan must be a sequence")
    merged: dict[int, int] = {}
    for row in plan:
        if (not isinstance(row, Sequence)
                or isinstance(row, (str, bytes, bytearray))
                or len(row) != 2):
            raise ValueError("plan row must be (step, quantity)")
        step, quantity = row
        if (_plain_int(step) is None or _plain_int(quantity) is None
                or step < 0 or quantity < 0):
            raise ValueError("plan values must be nonnegative plain integers")
        merged[step] = merged.get(step, 0) + quantity
    return tuple((step, merged[step]) for step in sorted(merged) if merged[step])


def cumulative_advance(reference: Any, candidate: Any) -> dict[str, int] | None:
    """Return the first prefix where candidate moves equal total units earlier.

    A total-quantity mismatch is deliberately non-comparable (``None``): this
    experiment must not redefine the current seller's quantity/feasibility
    semantics. This is the same cumulative-prefix notion used by EXEC-PACE,
    but without EXEC-PACE's price-trend predicate.
    """
    ref = _normalized_plan(reference)
    cand = _normalized_plan(candidate)
    if sum(q for _t, q in ref) != sum(q for _t, q in cand):
        return None
    ref_map = dict(ref)
    cand_map = dict(cand)
    ref_seen = 0
    cand_seen = 0
    for step in sorted(set(ref_map) | set(cand_map)):
        ref_seen += ref_map.get(step, 0)
        cand_seen += cand_map.get(step, 0)
        if cand_seen > ref_seen:
            return {
                "step": step,
                "candidate_cumulative": cand_seen,
                "reference_cumulative": ref_seen,
                "delta": cand_seen - ref_seen,
            }
    return None


def suppress_optional_late_advance(
    step: Any,
    reference: Any,
    candidate: Any,
    info: Any,
    *,
    threshold: int = SUPPRESS_AFTER_STEP,
) -> tuple[Any, dict]:
    """Veto one optional current-seller temporal advance at/after ``threshold``.

    Forced-feasibility is never touched. Malformed/non-comparable schedules
    fail open to the current seller. On a veto the exact reference schedule is
    returned and ``accepted=False`` makes the existing ``seller_choice_rank``
    path ineligible instead of creating a no-op winning candidate.
    """
    current_info = copy.deepcopy(info) if isinstance(info, dict) else {}
    report = {
        "enabled": True,
        "threshold": threshold,
        "blocked": False,
        "reason": "before-threshold",
        "advance": None,
    }
    current_info["microstack_s420"] = report

    plain_step = _plain_int(step)
    plain_threshold = _plain_int(threshold)
    if plain_step is None or plain_threshold is None or plain_threshold < 0:
        report["reason"] = "invalid-clock-or-threshold"
        return candidate, current_info
    if plain_step < plain_threshold:
        return candidate, current_info
    if current_info.get("forced_feasibility") is True:
        report["reason"] = "forced-feasibility-bypass"
        return candidate, current_info
    try:
        advance = cumulative_advance(reference, candidate)
    except (TypeError, ValueError, OverflowError):
        report["reason"] = "noncomparable-plan"
        return candidate, current_info
    report["advance"] = advance
    if advance is None:
        report["reason"] = "no-temporal-advance"
        return candidate, current_info

    report["blocked"] = True
    report["reason"] = "late-optional-temporal-advance"
    current_info["accepted"] = False
    current_info["acceptance_score"] = 0.0
    current_info["acceptance_rule"] = "microstack_s420_block"
    return copy.deepcopy(reference), current_info


class _Installation:
    def __init__(self, module: Any, original_horizon: Any, original_optimize_lot: Any):
        self.module = module
        self.original_horizon = original_horizon
        self.original_optimize_lot = original_optimize_lot
        self.active = True

    def restore(self) -> None:
        if not self.active:
            return
        self.module.HORIZON = self.original_horizon
        self.module.optimize_lot = self.original_optimize_lot
        self.active = False


def install(
    frozen_selected_module: Any,
    *,
    baseline_horizon: int = BASELINE_HORIZON,
    suppress_after_step: int | None = None,
) -> _Installation:
    """Install one isolated experiment arm into the current seller module.

    ``suppress_after_step=None`` is the H3-only arm. Supplying literal ``420``
    is the H3+S420 arm used by the recovered MICROSTACK re-gate.

    The caller owns process isolation and must call ``restore()`` before using
    another arm in the same interpreter.
    """
    horizon = _plain_int(baseline_horizon)
    if horizon is None or not 1 <= horizon <= 8:
        raise ValueError("baseline_horizon must be a plain integer in 1..8")
    if not hasattr(frozen_selected_module, "HORIZON"):
        raise ValueError("current frozen_selected module has no HORIZON seam")
    original_optimize = getattr(frozen_selected_module, "optimize_lot", None)
    if not callable(original_optimize):
        raise ValueError("current frozen_selected module has no optimize_lot seam")

    if suppress_after_step is not None:
        threshold = _plain_int(suppress_after_step)
        if threshold is None or threshold < 0:
            raise ValueError("suppress_after_step must be a nonnegative plain integer")
    else:
        threshold = None

    installation = _Installation(
        module=frozen_selected_module,
        original_horizon=frozen_selected_module.HORIZON,
        original_optimize_lot=original_optimize,
    )
    frozen_selected_module.HORIZON = horizon

    if threshold is not None:
        def wrapped_optimize_lot(*args: Any, **kwargs: Any):
            plan, info = original_optimize(*args, **kwargs)
            return suppress_optional_late_advance(
                kwargs.get("now"),
                kwargs.get("reference"),
                plan,
                info,
                threshold=threshold,
            )

        frozen_selected_module.optimize_lot = wrapped_optimize_lot

    return installation
