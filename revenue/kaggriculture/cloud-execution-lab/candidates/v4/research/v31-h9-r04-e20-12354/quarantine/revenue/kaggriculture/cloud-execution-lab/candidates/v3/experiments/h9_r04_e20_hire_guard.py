# SPDX-License-Identifier: Apache-2.0
"""H9 experiment: make the shipped E20 low-demand HIRE guard reachable on R04.

V3 already ships ``overlay/e20_hire_guard.py`` and wires it through the canonical
``TitanAgent._v3_post`` path.  R04 is a whole-route delegate and returns before that
post-hook, leaving the package key inert on the live R04 route.

This evaluator arm reuses ``apply_hire_guard`` unchanged and wraps the *final* R04
callable.  Running last matters because E20 preserves literal queue positions by
replacing only excess HIRE rows with ``[]``; it must judge the final action that would
otherwise reach the engine rather than an intermediate queue later rewritten by R04.

A final-action edit is not automatically composition-safe.  Stateful R04 layers such as
V219 can queue capital (BUY_LAND/BUY_SEED) and HIRE rows as one investment while already
committing internal intent.  E20 can then suppress part of the coupled labor after that
intent exists.  H9 therefore records every activation, coupled investment rows, observed
next-callback hand count, and available R04 V219/V233 hire-shortfall deltas.  ``changed``
and ``dropped_hire_rows`` remain proposal/edit metrics, not proof that a HIRE would have
executed or that a hand was actually removed relative to the paired baseline.

The file intentionally lives outside ``overlay/**`` and therefore is not a V3 package
input.  Disabled mode returns the exact parent output object.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from typing import Any, Callable, Mapping

OVERLAY = Path(__file__).resolve().parents[1] / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

from e20_hire_guard import apply_hire_guard  # noqa: E402

DEFAULT_MAX_HIRES_PER_DAY = 3
DEFAULT_MIN_UNWATERED_CROPS = 3
TURNS_PER_DAY = 24
_INVESTMENT_OPS = {"BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"}


def _own_hands(observation: Mapping[str, Any], player: int) -> int:
    farms = observation.get("farms") or []
    if not isinstance(farms, list) or not (0 <= player < len(farms)):
        return 0
    farm = farms[player] or {}
    hands = farm.get("hands") or []
    return len(hands) if isinstance(hands, list) else 0


def _r04_report_value(parent: Callable[..., Any], report_name: str, key: str) -> int:
    """Best-effort read-only snapshot of published R04 module telemetry.

    The normal installed R04 callable is defined in ``r04_full_router`` and therefore
    shares globals with ``_V219_REPORT`` / ``_V233_REPORT``.  Tests or alternate harness
    callables may not expose those globals; absence is intentionally zero/fail-soft.
    """
    globals_dict = getattr(parent, "__globals__", None)
    if not isinstance(globals_dict, dict):
        return 0
    report = globals_dict.get(report_name)
    if not isinstance(report, Mapping):
        return 0
    try:
        return int(report.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _investment_rows(action: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = action.get("market") or []
    found: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not row or not isinstance(row, (list, tuple)):
            continue
        op = str(row[0]) if row else ""
        if op in _INVESTMENT_OPS:
            found.append({"index": index, "order": list(row)})
    return found


def _hire_indices(action: Mapping[str, Any]) -> list[int]:
    rows = action.get("market") or []
    return [
        index
        for index, row in enumerate(rows)
        if row and isinstance(row, (list, tuple)) and row[0] == "HIRE"
    ]


def install(
    parent: Callable[[Mapping[str, Any], Mapping[str, Any] | None], Mapping[str, Any]],
    *,
    enabled: bool = False,
    max_hires_per_day: int = DEFAULT_MAX_HIRES_PER_DAY,
    min_unwatered_crops: int = DEFAULT_MIN_UNWATERED_CROPS,
):
    """Wrap a fully installed R04 callable with the existing E20 edit."""
    pending: dict[int, dict[str, Any]] = {}
    last_step: dict[int, int] = {}
    telemetry: dict[str, Any] = {
        "calls": 0,
        "changed": 0,
        "dropped_hire_rows": 0,
        "coupled_investment_activations": 0,
        "settled_activations": 0,
        "unresolved_on_reset": 0,
        "v219_hire_shortfall_delta": 0,
        "v233_hire_shortfall_delta": 0,
        "reasons": Counter(),
        "activation_trace": [],
    }

    def agent(observation, configuration=None):
        # Parent runs first by design.  On a later callback this also lets published R04
        # state machines reconcile the previous action before H9 snapshots their reports.
        action = parent(observation, configuration)
        telemetry["calls"] += 1
        if not enabled:
            telemetry["reasons"]["OFF"] += 1
            return action

        player = int(observation.get("player", 0))
        step = int(observation.get("step", 0))
        is_reset = player not in last_step or step <= last_step[player]
        prior = pending.get(player)
        if is_reset:
            if prior is not None:
                prior["settlement"] = "EPISODE_RESET"
                telemetry["unresolved_on_reset"] += 1
                pending.pop(player, None)
        elif prior is not None and step > int(prior["step"]):
            hands_now = _own_hands(observation, player)
            v219_now = _r04_report_value(parent, "_V219_REPORT", "hire_shortfalls")
            v233_now = _r04_report_value(parent, "_V233_REPORT", "sheep_hire_shortfalls")
            v219_delta = max(0, v219_now - int(prior["v219_hire_shortfalls_before"]))
            v233_delta = max(0, v233_now - int(prior["v233_hire_shortfalls_before"]))
            prior.update(
                settlement="NEXT_OBSERVATION",
                next_step=step,
                hands_next_observation=hands_now,
                observed_hand_delta=hands_now - int(prior["hands_before"]),
                v219_hire_shortfall_delta=v219_delta,
                v233_hire_shortfall_delta=v233_delta,
            )
            telemetry["settled_activations"] += 1
            telemetry["v219_hire_shortfall_delta"] += v219_delta
            telemetry["v233_hire_shortfall_delta"] += v233_delta
            pending.pop(player, None)
        last_step[player] = step

        cfg = dict(configuration or {})
        cfg["e20_max_hires_per_day"] = int(max_hires_per_day)
        cfg["e20_min_unwatered_crops"] = int(min_unwatered_crops)
        out, report = apply_hire_guard(observation, action, cfg, enabled=True)
        telemetry["reasons"][report.get("reason", "UNKNOWN")] += 1
        changed = int(bool(report.get("changed")))
        dropped = list(report.get("dropped_indices") or [])
        telemetry["changed"] += changed
        telemetry["dropped_hire_rows"] += len(dropped)

        if changed:
            investments = _investment_rows(action)
            event = {
                "player": player,
                "step": step,
                "day": step // TURNS_PER_DAY,
                "original_hire_indices": _hire_indices(action),
                "dropped_hire_indices": dropped,
                "coupled_investment_rows": investments,
                "hands_before": _own_hands(observation, player),
                "v219_hire_shortfalls_before": _r04_report_value(
                    parent, "_V219_REPORT", "hire_shortfalls"
                ),
                "v233_hire_shortfalls_before": _r04_report_value(
                    parent, "_V233_REPORT", "sheep_hire_shortfalls"
                ),
                "settlement": "PENDING",
            }
            telemetry["activation_trace"].append(event)
            telemetry["coupled_investment_activations"] += int(bool(investments))
            pending[player] = event
        return out

    agent.telemetry = telemetry
    agent.parent = parent
    agent.h9_enabled = bool(enabled)
    return agent
