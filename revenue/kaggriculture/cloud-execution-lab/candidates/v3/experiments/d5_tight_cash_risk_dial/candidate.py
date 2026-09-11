# SPDX-License-Identifier: Apache-2.0
"""Experiment-only D5 tight-game risk dial for the existing L3 seam.

This module is intentionally outside ``overlay/**``.  It does not change V3.1
package inputs, defaults, routes, quantities, or accounting.  The only decision
under test is whether #12377's already-existing late E184 reservation
suppression is permitted.

The proxy is deliberately modest and fully public: at the first late-game L3
decision, compare the two farms' currently observed ``money`` values and latch
whether their absolute gap is within an explicit development threshold.  The
proxy is *not* final score, net worth, rival private shed/inventory, rival
orders, or an opponent identity classifier.  A malformed or ambiguous public
observation keeps baseline E184 behavior.

``DEFAULT_MAX_ABS_CASH_GAP`` is a screening parameter, not a promoted value.
Economics must sweep/rebind it under exact package/interpreter custody before
any production/default decision.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import sys
from typing import Any

V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as base  # noqa: E402
import r04_no_late_sale_advance as l3  # noqa: E402

DEFAULT_LATCH_STEP = 648
# Development-only screening value.  It has no promotion authority.
DEFAULT_MAX_ABS_CASH_GAP = 5000


def _strict_int(value: Any, name: str) -> int:
    """Accept JSON integers only; bool/float/string aliases fail closed."""
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer")
    return value


def public_cash_gap(observation: Mapping[str, Any]) -> int:
    """Return |our public cash - rival public cash| for the two-player game."""
    if not isinstance(observation, Mapping):
        raise ValueError("observation must be a mapping")
    player = _strict_int(observation.get("player"), "player")
    farms = observation.get("farms")
    if not isinstance(farms, (list, tuple)) or len(farms) != 2:
        raise ValueError("farms must contain exactly two public farm states")
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")

    money: list[int] = []
    for index, farm in enumerate(farms):
        if not isinstance(farm, Mapping):
            raise ValueError(f"farms[{index}] must be a mapping")
        money.append(_strict_int(farm.get("money"), f"farms[{index}].money"))
    return abs(money[player] - money[1 - player])


class TightCashGate:
    """Latch one public cash-gap classification at the first late decision.

    Latching prevents the candidate's own later market behavior from moving the
    classifier in and out of the treatment arm.  A rewind/same-step restart is
    treated as a new episode, matching R04's own ``step <= last_step`` reset.
    """

    def __init__(
        self,
        max_abs_cash_gap: int = DEFAULT_MAX_ABS_CASH_GAP,
        latch_step: int = DEFAULT_LATCH_STEP,
    ) -> None:
        self.max_abs_cash_gap = _strict_int(max_abs_cash_gap, "max_abs_cash_gap")
        self.latch_step = _strict_int(latch_step, "latch_step")
        if self.max_abs_cash_gap < 0 or self.latch_step < 0:
            raise ValueError("gate parameters must be non-negative")
        self.players: dict[int, dict[str, Any]] = {}
        self.last_evidence: dict[int, dict[str, Any]] = {}

    def _clear_all(self) -> None:
        self.players.clear()
        self.last_evidence.clear()

    def allow(self, observation: Mapping[str, Any]) -> bool:
        """Return whether the existing L3 suppression may run on this call."""
        try:
            if not isinstance(observation, Mapping):
                raise ValueError("observation must be a mapping")
            step = _strict_int(observation.get("step"), "step")
            player = _strict_int(observation.get("player"), "player")
            if step < 0 or player not in (0, 1):
                raise ValueError("invalid step/player")
        except (TypeError, ValueError):
            self._clear_all()
            return False

        state = self.players.get(player)
        if state is not None and step <= state["last_step"]:
            self.players.pop(player, None)
            self.last_evidence.pop(player, None)
            state = None
        if state is None:
            state = {"last_step": step, "latched": None}
            self.players[player] = state
        else:
            state["last_step"] = step

        if step < self.latch_step:
            return False
        if state["latched"] is not None:
            return bool(state["latched"])

        try:
            gap = public_cash_gap(observation)
        except (TypeError, ValueError):
            # Never carry a partially established late-game classification.
            self.players.pop(player, None)
            self.last_evidence.pop(player, None)
            return False

        tight = gap <= self.max_abs_cash_gap
        state["latched"] = tight
        self.last_evidence[player] = {
            "step": step,
            "cash_gap": gap,
            "max_abs_cash_gap": self.max_abs_cash_gap,
            "tight": tight,
        }
        return tight


GATE = TightCashGate()
REPORT = {
    "late_decisions": 0,
    "suppressed": 0,
    "guarded": 0,
    "last_step": None,
}
_ALLOW_SUPPRESS = False
_ORIGINAL_SUPPRESSED = l3.suppressed


def reset(max_abs_cash_gap: int = DEFAULT_MAX_ABS_CASH_GAP) -> None:
    """Reset experiment gate/telemetry; runner may bind a different cutoff."""
    global GATE, _ALLOW_SUPPRESS
    GATE = TightCashGate(max_abs_cash_gap=max_abs_cash_gap)
    _ALLOW_SUPPRESS = False
    REPORT.update({"late_decisions": 0, "suppressed": 0, "guarded": 0, "last_step": None})
    l3.reset()


def _conditional_suppressed(
    step: Any,
    enabled: Any,
    threshold: Any = l3.DEFAULT_THRESHOLD,
) -> bool:
    """Exact L3 call-site predicate, with D5 as a permission gate only."""
    try:
        step_i = _strict_int(step, "step")
        threshold_i = _strict_int(threshold, "threshold")
        if type(enabled) is not bool:
            raise ValueError("enabled must be bool")
    except (TypeError, ValueError):
        return False
    if not enabled or step_i < threshold_i:
        return False

    REPORT["late_decisions"] += 1
    REPORT["last_step"] = step_i
    if not _ALLOW_SUPPRESS:
        REPORT["guarded"] += 1
        return False

    REPORT["suppressed"] += 1
    # Preserve #12377's telemetry contract on actual suppression only.
    l3.REPORT["suppressed_steps"] += 1
    l3.REPORT["last"] = step_i
    return True


BASE_AGENT = base.install(
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
    no_late_sale_advance=True,
    no_late_sale_advance_step=DEFAULT_LATCH_STEP,
)


def agent(observation, configuration=None):
    """Exact L3 carrier, with suppression allowed only in the latched tight arm."""
    global _ALLOW_SUPPRESS
    _ALLOW_SUPPRESS = GATE.allow(observation)
    l3.suppressed = _conditional_suppressed
    try:
        return BASE_AGENT(observation, configuration)
    finally:
        l3.suppressed = _ORIGINAL_SUPPRESSED
        _ALLOW_SUPPRESS = False


agent.telemetry = REPORT
