# SPDX-License-Identifier: Apache-2.0
"""B1 experiment: bounded alternate-day animal feeding for a fully-built V3.1 agent.

This is an evaluator/bench wrapper only.  It does not buy feed, alter market rows,
route workers, or enter ``overlay/**`` / build_v3.py package inputs.

Kaggriculture's pinned animal rules have two distinct feed effects:
* base animal production does not require FEED;
* an animal escapes only after two consecutive unfed daily refreshes.
CARE's production bonus still requires both CARE and FEED, so skipped feeds can
sacrifice bonus yield.  This experiment therefore exposes telemetry rather than
claiming that every skipped feed is profitable.

The wrapper suppresses an inherited FEED only when all of these are true:
* the worker is standing on a live animal;
* that animal is not already fed today;
* ``consecutive_unfed == 0`` (so one missed refresh cannot escape it);
* the worker actually carries WHEAT (so the inherited FEED would consume one).

When ``consecutive_unfed >= 1`` the parent FEED passes through unchanged.  Disabled
mode returns the exact parent output object.
"""
from __future__ import annotations

import copy
from collections import Counter
from typing import Any, Callable, Mapping

ANIMALS = frozenset({"GOOSE", "COW", "SHEEP"})


def install(
    parent: Callable[[Mapping[str, Any], Mapping[str, Any] | None], Mapping[str, Any]],
    *,
    enabled: bool = False,
):
    """Wrap ``parent`` with the fail-safe feed suppression experiment."""
    telemetry: dict[str, Any] = {
        "calls": 0,
        "commands_suppressed": 0,
        "feed_units_saved": 0,
        "protected_second_miss": 0,
        "suppressed_on_cared_tile": 0,
        "by_species": Counter(),
        "reasons": Counter(),
    }
    last_step: dict[int, int] = {}
    suppressed_days: dict[int, set[tuple[int, int, int]]] = {}

    def agent(observation, configuration=None):
        action = parent(observation, configuration)
        telemetry["calls"] += 1
        if not enabled:
            telemetry["reasons"]["OFF"] += 1
            return action

        try:
            player = int(observation["player"])
            step = int(observation["step"])
            farm = observation["farms"][player]
            tiles = farm["tiles"]
            positions = [farm["farmer"], *(farm.get("hands") or [])]
            inventories = observation["private"]["inventories"]
            commands = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
        except (KeyError, IndexError, TypeError, ValueError):
            telemetry["reasons"]["MALFORMED_OBSERVATION"] += 1
            return action

        if player not in last_step or step <= last_step[player]:
            suppressed_days[player] = set()
        last_step[player] = step
        day = step // 24

        edits: list[int] = []
        species_for_edit: dict[int, str] = {}
        save_keys: set[tuple[int, int, int]] = set()
        cared_edits = 0

        for actor in range(min(len(commands), len(positions), len(inventories))):
            command = commands[actor]
            if not isinstance(command, list) or not command or command[0] != "FEED":
                continue
            inventory = inventories[actor]
            if not isinstance(inventory, Mapping) or int(inventory.get("WHEAT", 0) or 0) <= 0:
                telemetry["reasons"]["NO_CARRIED_WHEAT"] += 1
                continue
            try:
                x, y = positions[actor]
                tile = tiles[y][x]
            except (IndexError, TypeError, ValueError):
                telemetry["reasons"]["BAD_POSITION"] += 1
                continue
            if not isinstance(tile, Mapping) or tile.get("animal") not in ANIMALS:
                telemetry["reasons"]["NO_LIVE_ANIMAL"] += 1
                continue
            if bool(tile.get("fed_today")):
                telemetry["reasons"]["ALREADY_FED"] += 1
                continue

            try:
                unfed = int(tile.get("consecutive_unfed", 0))
            except (TypeError, ValueError):
                telemetry["reasons"]["BAD_UNFED_STATE"] += 1
                continue
            if unfed != 0:
                telemetry["protected_second_miss"] += 1
                telemetry["reasons"]["SECOND_MISS_PROTECTED"] += 1
                continue

            edits.append(actor)
            species_for_edit[actor] = str(tile["animal"])
            save_keys.add((day, int(x), int(y)))
            if bool(tile.get("cared_today")):
                cared_edits += 1

        if not edits:
            return action

        out = copy.deepcopy(action)
        out_commands = [out.get("farmer") or ["PASS"], *(out.get("hands") or [])]
        for actor in edits:
            if actor < len(out_commands):
                out_commands[actor] = ["PASS"]
                telemetry["commands_suppressed"] += 1
                telemetry["by_species"][species_for_edit[actor]] += 1
        out["farmer"] = out_commands[0]
        out["hands"] = out_commands[1:]

        prior = suppressed_days.setdefault(player, set())
        new_saves = save_keys - prior
        telemetry["feed_units_saved"] += len(new_saves)
        prior.update(save_keys)
        telemetry["suppressed_on_cared_tile"] += cared_edits
        telemetry["reasons"]["SAFE_FIRST_MISS"] += len(edits)
        return out

    agent.telemetry = telemetry
    agent.parent = parent
    agent.b1_enabled = bool(enabled)
    return agent
