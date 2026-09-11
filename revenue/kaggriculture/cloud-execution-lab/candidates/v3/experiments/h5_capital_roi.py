# SPDX-License-Identifier: Apache-2.0
"""H5: terminal animal-capital ROI guard for the V3.1 R04 route.

This is an experiment, not release wiring. It post-processes only market rows and is
identity when disabled.

Safety certificate:
- R04 switches to its final plan at step 648 and its last action is step 718.
- The extracted Kaggriculture mechanics define first animal yields at 4 days for GOOSE,
  6 days for SHEEP, and 8 days for COW.
- With 24 turns/day, even a goose bought at step 648 needs 96 turns before first yield,
  while only 70 action steps remain. New animals bought in the final-plan window
  therefore cannot produce before the episode ends.

The guard preserves market row positions by blanking only provably non-producing
BUY_ANIMAL rows. HIRE, BUY_LAND, seeds, products, sells, and all worker actions are
untouched.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

TURNS_PER_DAY = 24
FINAL_PLAN_STEP = 648
DEFAULT_LAST_ACTION_STEP = 718
FIRST_YIELD_DAYS = {"GOOSE": 4, "SHEEP": 6, "COW": 8}
FIRST_YIELD_TURNS = {animal: days * TURNS_PER_DAY
                     for animal, days in FIRST_YIELD_DAYS.items()}


def _last_action_step(config: Mapping[str, Any] | None) -> int:
    cfg = config or {}
    try:
        return max(0, int(cfg.get("episodeSteps", 720)) - 2)
    except (TypeError, ValueError):
        return DEFAULT_LAST_ACTION_STEP


def apply_capital_roi_guard(
    observation: Mapping[str, Any],
    action: Mapping[str, Any],
    configuration: Mapping[str, Any] | None = None,
    *,
    enabled: bool = False,
    final_plan_step: int = FINAL_PLAN_STEP,
):
    """Blank terminal BUY_ANIMAL rows that cannot reach their first yield."""
    report: dict[str, Any] = {
        "enabled": bool(enabled),
        "changed": False,
        "reason": "OFF" if not enabled else "NO_OP",
        "dropped_indices": [],
        "dropped_units": {},
    }
    if not enabled:
        return action, report

    try:
        step = int(observation.get("step", 0))
    except (TypeError, ValueError):
        report["reason"] = "BAD_STEP"
        return action, report

    if step < int(final_plan_step):
        report["reason"] = "BEFORE_FINAL_PLAN"
        return action, report

    last = _last_action_step(configuration)
    remaining = max(0, last - step)
    report.update(step=step, last_action_step=last, remaining_turns=remaining)

    raw_market = action.get("market", []) if isinstance(action, Mapping) else []
    if not isinstance(raw_market, list):
        report["reason"] = "BAD_MARKET_QUEUE"
        return action, report

    drop: list[tuple[int, str, int]] = []
    for index, order in enumerate(raw_market):
        if not isinstance(order, list) or len(order) < 3 or order[0] != "BUY_ANIMAL":
            continue
        animal = order[1]
        if animal not in FIRST_YIELD_TURNS:
            continue
        try:
            quantity = max(0, int(order[2]))
        except (TypeError, ValueError):
            continue
        if quantity and remaining < FIRST_YIELD_TURNS[animal]:
            drop.append((index, animal, quantity))

    if not drop:
        report["reason"] = "NO_PROVABLY_DEAD_ANIMAL_CAPITAL"
        return action, report

    out = deepcopy(action)
    market = list(out.get("market") or [])
    units: dict[str, int] = {}
    for index, animal, quantity in drop:
        market[index] = []
        units[animal] = units.get(animal, 0) + quantity
    out["market"] = market
    report.update(
        changed=True,
        reason="DROP_TERMINAL_ANIMAL_CAPITAL",
        dropped_indices=[index for index, _, _ in drop],
        dropped_units=units,
    )
    return out, report


def wrap_agent(parent: Callable, *, enabled: bool = False, final_plan_step: int = FINAL_PLAN_STEP):
    """Return an R04-compatible callable with the H5 guard outermost."""
    def agent(observation, configuration=None):
        action = parent(observation, configuration)
        guarded, _ = apply_capital_roi_guard(
            observation, action, configuration,
            enabled=enabled, final_plan_step=final_plan_step,
        )
        return guarded
    return agent
