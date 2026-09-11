# SPDX-License-Identifier: Apache-2.0
"""TITAN V3.1 H5 experiment: terminal animal-capital ROI guard.

Default-off and experiment-only.  The guard removes only a suffix of market
``BUY_ANIMAL`` rows that cannot reach first production before the standard
720-step episode ends.  Rows are blanked in place so cross-player market row
indices remain stable.

A deliberately conservative affordability rule prevents a dropped purchase
from funding a later cash-consuming row that previously might have failed:
only dead-animal purchases *after* the last other cash-consuming/unknown market
row are eligible.  SELL rows and empty placeholders may follow safely.

No worker command, liquidation row, SELL quantity, HIRE, BUY_LAND,
BUY_PRODUCT, or BUY_SEED row is created, removed, moved, or rewritten.
Malformed/type-confused state fails closed to the exact parent action.
"""
from __future__ import annotations

import copy
from typing import Any, Callable, Mapping

KEY = "h5_terminal_animal_capital"
TURNS_PER_DAY = 24
EPISODE_STEPS = 720
FINAL_PLAN_STEP = 648
LAST_ACTION_STEP = EPISODE_STEPS - 2
FIRST_YIELD_DAYS = {"GOOSE": 4, "SHEEP": 6, "COW": 8}
FIRST_YIELD_TURNS = {
    animal: days * TURNS_PER_DAY for animal, days in FIRST_YIELD_DAYS.items()
}


def _standard_config(configuration: Mapping[str, Any] | None) -> bool:
    """Accept only the pinned timing contract; omitted keys mean defaults."""
    if configuration is None:
        return True
    if not isinstance(configuration, Mapping):
        return False
    for key, expected in (("turnsPerDay", TURNS_PER_DAY),
                          ("episodeSteps", EPISODE_STEPS)):
        if key not in configuration:
            continue
        value = configuration[key]
        if type(value) is not int or value != expected:
            return False
    return True


def apply_terminal_animal_capital_guard(
    observation: Mapping[str, Any],
    action: Mapping[str, Any],
    configuration: Mapping[str, Any] | None = None,
    *,
    enabled: bool = False,
):
    """Return ``(action, report)`` after a proof-safe terminal capital edit.

    No-op paths return the exact input ``action`` object.
    """
    report: dict[str, Any] = {
        "enabled": enabled is True,
        "changed": False,
        "reason": "OFF" if enabled is not True else "NO_OP",
        "dropped_indices": [],
        "dropped_units": {},
    }
    if enabled is not True:
        return action, report
    if not isinstance(observation, Mapping) or not isinstance(action, Mapping):
        report["reason"] = "BAD_INPUT"
        return action, report
    if not _standard_config(configuration):
        report["reason"] = "NONSTANDARD_CONFIG"
        return action, report

    step = observation.get("step")
    if type(step) is not int or step < 0:
        report["reason"] = "BAD_STEP"
        return action, report
    if step < FINAL_PLAN_STEP:
        report["reason"] = "BEFORE_FINAL_PLAN"
        return action, report
    if step > LAST_ACTION_STEP:
        report["reason"] = "AFTER_LAST_ACTION"
        return action, report

    raw_market = action.get("market")
    if not isinstance(raw_market, list):
        report["reason"] = "BAD_MARKET_QUEUE"
        return action, report

    remaining_turns = LAST_ACTION_STEP - step
    report.update(
        step=step,
        last_action_step=LAST_ACTION_STEP,
        remaining_turns=remaining_turns,
    )

    # Parse the whole queue before mutating.  Empty lists are legitimate fixed
    # row placeholders.  Any structurally ambiguous non-empty row fails closed.
    dead: dict[int, tuple[str, int]] = {}
    parsed_ops: list[str | None] = []
    for index, order in enumerate(raw_market):
        if order == []:
            parsed_ops.append(None)
            continue
        if not isinstance(order, list) or not order or type(order[0]) is not str:
            report["reason"] = "BAD_MARKET_ROW"
            return action, report
        op = order[0]
        parsed_ops.append(op)
        if op != "BUY_ANIMAL":
            continue
        if len(order) != 3 or type(order[1]) is not str or type(order[2]) is not int:
            report["reason"] = "BAD_BUY_ANIMAL_ROW"
            return action, report
        animal, quantity = order[1], order[2]
        if quantity <= 0:
            report["reason"] = "BAD_BUY_ANIMAL_ROW"
            return action, report
        if animal not in FIRST_YIELD_TURNS:
            # Unknown/future animal semantics are not ours to optimize.
            continue
        if remaining_turns < FIRST_YIELD_TURNS[animal]:
            dead[index] = (animal, quantity)

    if not dead:
        report["reason"] = "NO_PROVABLY_DEAD_ANIMAL_CAPITAL"
        return action, report

    # Dropping spend can change affordability of later market rows.  Treat every
    # non-SELL, non-placeholder row other than another proven-dead animal buy as
    # protected/possibly cash-consuming.  Only the proven-dead suffix after the
    # last such row is safe to blank.
    last_protected = -1
    for index, op in enumerate(parsed_ops):
        if op is None or op == "SELL" or index in dead:
            continue
        last_protected = index

    drop_indices = [index for index in sorted(dead) if index > last_protected]
    if not drop_indices:
        report["reason"] = "DOWNSTREAM_AFFORDABILITY_AMBIGUITY"
        return action, report

    out = copy.deepcopy(action)
    market = out.get("market")
    if not isinstance(market, list) or len(market) != len(raw_market):
        report["reason"] = "COPY_SHAPE_MISMATCH"
        return action, report

    units: dict[str, int] = {}
    for index in drop_indices:
        animal, quantity = dead[index]
        market[index] = []
        units[animal] = units.get(animal, 0) + quantity

    report.update(
        changed=True,
        reason="DROP_PROVABLY_DEAD_ANIMAL_CAPITAL_SUFFIX",
        dropped_indices=drop_indices,
        dropped_units=units,
        protected_prefix_through=last_protected,
    )
    return out, report


def wrap_agent(parent: Callable, *, enabled: bool = False):
    """Return an R04-compatible callable with H5 outermost."""
    if not callable(parent):
        raise TypeError("parent must be callable")

    def agent(observation, configuration=None):
        action = parent(observation, configuration)
        guarded, _ = apply_terminal_animal_capital_guard(
            observation,
            action,
            configuration,
            enabled=enabled,
        )
        return guarded

    return agent
