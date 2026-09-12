# SPDX-License-Identifier: Apache-2.0
"""Default-off current-ABI transform for strictly dominated terminal HIRE rows."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def _last_action_step(configuration: Mapping[str, Any] | None) -> int:
    if configuration is None:
        return 718
    if not isinstance(configuration, Mapping):
        raise ValueError("configuration must be a mapping or None")
    value = configuration.get("episodeSteps", 720)
    if type(value) is not int or value < 2:
        raise ValueError("episodeSteps must be a plain integer >= 2")
    return value - 2


def _validate_selected_action(selected_action: Any) -> None:
    if not isinstance(selected_action, Mapping):
        raise ValueError("selected_action must be a mapping")
    for field in ("farmer", "hands", "market"):
        if field not in selected_action or not isinstance(selected_action[field], list):
            raise ValueError(f"selected_action.{field} must be a list")
    farmer = selected_action["farmer"]
    if not farmer:
        raise ValueError("farmer command must be nonempty")
    if any(not isinstance(command, list) or not command for command in selected_action["hands"]):
        raise ValueError("hand commands must be nonempty lists")
    for row in selected_action["market"]:
        if not isinstance(row, list):
            raise ValueError("market rows must be lists")
        if row and not isinstance(row[0], str):
            raise ValueError("market opcode must be a string")


def transform(
    observation: Mapping[str, Any],
    configuration: Mapping[str, Any] | None,
    selected_action: Any,
    *,
    enabled: bool = False,
):
    """Replace terminal HIRE rows with parser no-ops while preserving row indices.

    The official engine parser treats ``[]`` as no order. Keeping the list length
    unchanged prevents later SELL/BUY rows from moving to a different market index.
    The transform is deliberately exact-terminal only; step 717 is untouched because
    a new hand can still act on step 718.
    """
    if type(enabled) is not bool:
        raise TypeError("enabled must be exact bool")

    fallback = deepcopy(selected_action)
    report = {
        "enabled": enabled,
        "changed": False,
        "reason": "OFF" if not enabled else "NO_OP",
        "neutralized_indices": [],
    }
    if not enabled:
        return fallback, report

    try:
        if not isinstance(observation, Mapping):
            raise ValueError("observation must be a mapping")
        step = observation.get("step")
        if type(step) is not int or step < 0:
            raise ValueError("observation.step must be a nonnegative plain integer")
        terminal_step = _last_action_step(configuration)
        report["terminal_step"] = terminal_step
        if step != terminal_step:
            report["reason"] = "NONTERMINAL"
            return fallback, report

        _validate_selected_action(selected_action)
        market = selected_action["market"]
        indices = [
            index for index, row in enumerate(market)
            if row and row[0] == "HIRE"
        ]
        if not indices:
            report["reason"] = "NO_TERMINAL_HIRE"
            return fallback, report

        result = deepcopy(selected_action)
        for index in indices:
            result["market"][index] = []
        report.update(
            changed=True,
            reason="TERMINAL_HIRE_DOMINATED",
            neutralized_indices=indices,
            market_length_before=len(market),
            market_length_after=len(result["market"]),
        )
        return result, report
    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
        report["reason"] = f"FAIL_CLOSED:{error}"
        return fallback, report
