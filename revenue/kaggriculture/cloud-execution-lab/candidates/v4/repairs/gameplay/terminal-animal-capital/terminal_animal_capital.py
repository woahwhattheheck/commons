# SPDX-License-Identifier: Apache-2.0
"""TITAN V4: terminal animal-capital guard.

Source-bound, default-off component.  It may blank only BUY_ANIMAL rows whose
earliest possible first production lies beyond the last executable action,
and only when doing so cannot fund a later protected market order in the same
queue.  It never rewrites unit actions, SELL rows, or market row indices.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

TURNS_PER_DAY = 24
EPISODE_STEPS = 720
FINAL_PLAN_STEP = 648
LAST_ACTION_STEP = EPISODE_STEPS - 2
FIRST_YIELD_DAYS = {"GOOSE": 4, "SHEEP": 6, "COW": 8}


def _value(obj: Any, key: str) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key)
    return getattr(obj, key, None)


def _standard_timing(configuration: Any) -> bool:
    if configuration is None:
        return False
    turns = _value(configuration, "turnsPerDay")
    steps = _value(configuration, "episodeSteps")
    return (
        type(turns) is int
        and turns == TURNS_PER_DAY
        and type(steps) is int
        and steps == EPISODE_STEPS
    )


def _step(observation: Any) -> int | None:
    value = _value(observation, "step")
    return value if type(value) is int else None


def _earliest_first_yield_step(step: int, first_yield_days: int) -> int:
    """Conservative lower bound on the refresh that can create first yield.

    Market BUY_ANIMAL executes after unit actions, so the animal cannot be
    placed before a later callback.  Granting same-day placement anyway makes
    this bound earlier (therefore conservative).  An animal placed on day d
    first produces at the end-of-day refresh whose next_day is
    d + first_yield_days.
    """
    day = step // TURNS_PER_DAY
    return (day + first_yield_days) * TURNS_PER_DAY - 1


def plan_terminal_animal_capital(
    action: Any,
    observation: Any,
    configuration: Any,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "eligible": False,
        "reason": "NO_OP",
        "drop_indices": [],
        "dropped_units": {},
    }
    if not isinstance(action, Mapping):
        report["reason"] = "BAD_ACTION"
        return report
    if not _standard_timing(configuration):
        report["reason"] = "NONSTANDARD_OR_MISSING_TIMING"
        return report

    step = _step(observation)
    if step is None or step < 0:
        report["reason"] = "BAD_STEP"
        return report
    if step < FINAL_PLAN_STEP:
        report["reason"] = "BEFORE_FINAL_PLAN"
        return report
    if step > LAST_ACTION_STEP:
        report["reason"] = "AFTER_LAST_ACTION"
        return report

    market = action.get("market")
    if not isinstance(market, list):
        report["reason"] = "BAD_MARKET_QUEUE"
        return report

    parsed_ops: list[str | None] = []
    dead: dict[int, tuple[str, int, int]] = {}
    for index, row in enumerate(market):
        if row == []:
            parsed_ops.append(None)
            continue
        if not isinstance(row, list) or not row or type(row[0]) is not str:
            report["reason"] = "BAD_MARKET_ROW"
            return report
        op = row[0]
        parsed_ops.append(op)
        if op != "BUY_ANIMAL":
            continue
        if len(row) != 3 or type(row[1]) is not str or type(row[2]) is not int:
            report["reason"] = "BAD_BUY_ANIMAL_ROW"
            return report
        animal, quantity = row[1], row[2]
        if quantity <= 0:
            report["reason"] = "BAD_BUY_ANIMAL_ROW"
            return report
        days = FIRST_YIELD_DAYS.get(animal)
        if days is None:
            continue
        first_yield_step = _earliest_first_yield_step(step, days)
        if first_yield_step > LAST_ACTION_STEP:
            dead[index] = (animal, quantity, first_yield_step)

    if not dead:
        report["reason"] = "NO_PROVABLY_DEAD_ANIMAL_CAPITAL"
        return report

    # Blank only a dead suffix.  Saving cash before any later non-SELL,
    # non-placeholder row could make that later order newly executable.
    last_protected = -1
    for index, op in enumerate(parsed_ops):
        if op is None or op == "SELL" or index in dead:
            continue
        last_protected = index

    drop = [index for index in sorted(dead) if index > last_protected]
    if not drop:
        report["reason"] = "DOWNSTREAM_AFFORDABILITY_AMBIGUITY"
        return report

    units: dict[str, int] = {}
    witnesses: list[dict[str, int | str]] = []
    for index in drop:
        animal, quantity, first_yield_step = dead[index]
        units[animal] = units.get(animal, 0) + quantity
        witnesses.append(
            {
                "index": index,
                "animal": animal,
                "quantity": quantity,
                "earliest_first_yield_step": first_yield_step,
            }
        )
    report.update(
        eligible=True,
        reason="DROP_PROVABLY_DEAD_ANIMAL_CAPITAL_SUFFIX",
        step=step,
        drop_indices=drop,
        dropped_units=units,
        protected_prefix_through=last_protected,
        witnesses=witnesses,
    )
    return report


def apply_terminal_animal_capital(
    action: Any,
    observation: Any,
    configuration: Any,
    *,
    enabled: bool = False,
) -> Any:
    """Apply the guard.  Every OFF/nonmatch path preserves object identity."""
    if enabled is not True:
        return action
    plan = plan_terminal_animal_capital(action, observation, configuration)
    if plan.get("eligible") is not True:
        return action

    out = copy.deepcopy(action)
    market = out.get("market")
    original = action.get("market")
    if not isinstance(market, list) or not isinstance(original, list) or len(market) != len(original):
        return action
    for index in plan["drop_indices"]:
        market[index] = []
    return out
