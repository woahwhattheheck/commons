# SPDX-License-Identifier: Apache-2.0
"""Fail-closed runtime for replay-derived TITAN route candidates.

The incumbent controller is called on every turn so its hidden route/checkpoint state
never falls behind. A leader action may replace a bounded component only while the
source structural signature still matches the live farm. Any malformed tape row or
structural mismatch permanently hands control back to the incumbent for that game.
"""
from __future__ import annotations

import copy
from collections.abc import Callable, Mapping, Sequence
from typing import Any

MODES = frozenset({"post24_full", "post24_market", "post24_units"})


def _step(obs: Mapping[str, Any]) -> int:
    value = obs.get("step", 0)
    if type(value) is not int or value < 0:
        raise ValueError("observation step must be a nonnegative integer")
    return value


def _farm(obs: Mapping[str, Any]) -> Mapping[str, Any]:
    player = obs.get("player")
    farms = obs.get("farms")
    if type(player) is not int or not isinstance(farms, Sequence):
        raise ValueError("observation has no canonical player/farms view")
    if player < 0 or player >= len(farms) or not isinstance(farms[player], Mapping):
        raise ValueError("observation player farm is unavailable")
    return farms[player]


def structural_signature(obs: Mapping[str, Any]) -> dict[str, int]:
    farm = _farm(obs)
    hands = farm.get("hands", ())
    quadrants = farm.get("unlocked_quadrants", ())
    if not isinstance(hands, Sequence) or isinstance(hands, (str, bytes)):
        raise ValueError("farm hands must be a sequence")
    if not isinstance(quadrants, Sequence) or isinstance(quadrants, (str, bytes)):
        raise ValueError("farm unlocked_quadrants must be a sequence")
    return {"hands": len(hands), "quadrants": len(quadrants)}


def _market_limit(configuration: Mapping[str, Any] | None) -> int:
    raw = (configuration or {}).get("maxMarketOrdersPerTurn", 10)
    # The official interpreter normalizes this limit to at least one.
    if type(raw) is bool:
        return 1
    try:
        return max(1, int(raw))
    except (TypeError, ValueError, OverflowError):
        return 10


def _unit_action(value: Any) -> list[Any] | None:
    if not isinstance(value, list) or not value or not isinstance(value[0], str):
        return None
    return copy.deepcopy(value)


def _market_action(value: Any) -> list[list[Any]] | None:
    if not isinstance(value, list):
        return None
    result: list[list[Any]] = []
    for row in value:
        if row == []:
            result.append([])
        elif isinstance(row, list) and row and isinstance(row[0], str):
            result.append(copy.deepcopy(row))
        else:
            return None
    return result


def _baseline_shape(base: Any) -> dict[str, Any]:
    if not isinstance(base, Mapping):
        raise ValueError("baseline action must be a mapping")
    farmer = _unit_action(base.get("farmer"))
    hands = base.get("hands")
    market = _market_action(base.get("market"))
    if farmer is None or not isinstance(hands, list) or market is None:
        raise ValueError("baseline action has malformed farmer/hands/market fields")
    normalized_hands: list[list[Any]] = []
    for row in hands:
        action = _unit_action(row)
        if action is None:
            raise ValueError("baseline hand action is malformed")
        normalized_hands.append(action)
    return {"farmer": farmer, "hands": normalized_hands, "market": market}


class LeaderRoutePolicy:
    """Shadow the incumbent and conditionally emit one replay-derived route arm."""

    def __init__(
        self,
        baseline_agent: Callable[[Mapping[str, Any], Mapping[str, Any] | None], Any],
        tape: Mapping[int | str, Mapping[str, Any]],
        *,
        mode: str,
        start_step: int = 24,
    ) -> None:
        if mode not in MODES:
            raise ValueError(f"unsupported route mode: {mode}")
        if type(start_step) is not int or start_step < 24:
            raise ValueError("leader route may not own the opening day")
        self._baseline_agent = baseline_agent
        self._tape: dict[int, Mapping[str, Any]] = {}
        for raw_step, entry in tape.items():
            step = int(raw_step)
            if step < 0 or not isinstance(entry, Mapping) or step in self._tape:
                raise ValueError("tape contains an invalid or duplicate step")
            self._tape[step] = entry
        self.mode = mode
        self.start_step = start_step
        self.active = True
        self.handoff_step: int | None = None
        self.activation_steps: list[int] = []

    def _handoff(self, step: int) -> None:
        self.active = False
        if self.handoff_step is None:
            self.handoff_step = step

    def _candidate(
        self,
        obs: Mapping[str, Any],
        configuration: Mapping[str, Any] | None,
        base: dict[str, Any],
        entry: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        expected = entry.get("signature")
        if not isinstance(expected, Mapping):
            return None
        live = structural_signature(obs)
        if type(expected.get("hands")) is not int or type(expected.get("quadrants")) is not int:
            return None
        if live != {"hands": expected["hands"], "quadrants": expected["quadrants"]}:
            return None

        raw = entry.get("action")
        if not isinstance(raw, Mapping):
            return None
        out = copy.deepcopy(base)

        if self.mode in {"post24_full", "post24_units"}:
            farmer = _unit_action(raw.get("farmer"))
            hands = raw.get("hands")
            if farmer is None or not isinstance(hands, list) or len(hands) != live["hands"]:
                return None
            normalized_hands: list[list[Any]] = []
            for row in hands:
                action = _unit_action(row)
                if action is None:
                    return None
                normalized_hands.append(action)
            out["farmer"] = farmer
            out["hands"] = normalized_hands

        if self.mode in {"post24_full", "post24_market"}:
            market = _market_action(raw.get("market"))
            if market is None:
                return None
            out["market"] = market[: _market_limit(configuration)]

        return out

    def agent(
        self,
        obs: Mapping[str, Any],
        configuration: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        step = _step(obs)
        if step == 0:
            self.active = True
            self.handoff_step = None
            self.activation_steps = []

        # This call is unconditional: even when the leader arm emits an action,
        # the incumbent route/checkpoint machine advances on the same observation.
        base = _baseline_shape(self._baseline_agent(obs, configuration))
        if not self.active or step < self.start_step:
            return base
        entry = self._tape.get(step)
        if entry is None:
            self._handoff(step)
            return base
        try:
            candidate = self._candidate(obs, configuration, base, entry)
        except (KeyError, TypeError, ValueError, OverflowError):
            candidate = None
        if candidate is None:
            self._handoff(step)
            return base
        if candidate != base:
            self.activation_steps.append(step)
        return candidate

    def diagnostics(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "start_step": self.start_step,
            "active": self.active,
            "handoff_step": self.handoff_step,
            "activation_count": len(self.activation_steps),
            "activation_steps": list(self.activation_steps),
        }
