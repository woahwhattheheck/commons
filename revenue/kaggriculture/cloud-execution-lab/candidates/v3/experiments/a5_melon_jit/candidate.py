#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact V3.1 evaluator entrypoint for A5 MELON just-in-time fertilizer."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

HERE = Path(__file__).resolve()
EXPERIMENTS = HERE.parents[1]
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
for path in (EXPERIMENTS, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_full_router as r04  # noqa: E402
from a5_melon_jit_fertilize import apply_melon_jit_fertilize  # noqa: E402

BASE = r04.install(
    None,
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
)

REPORT = Counter()
TRACE = []


def _cfg(configuration, name, default):
    if configuration is None:
        return default
    if isinstance(configuration, dict):
        return configuration.get(name, default)
    return getattr(configuration, name, default)


def _standard_clock(configuration):
    value = _cfg(configuration, "turnsPerDay", 24)
    return type(value) is int and value == 24


def _next_authored_and_blocked(observation):
    if not isinstance(observation, dict):
        return None
    step = observation.get("step")
    player = observation.get("player")
    if type(step) is not int or type(player) is not int or step < 0 or player < 0 or step >= r04.LAST_STEP:
        return None
    policy = getattr(r04, "_POLICY", None)
    players = getattr(policy, "players", None)
    tapes = getattr(policy, "tapes", None)
    if not isinstance(players, dict) or not isinstance(tapes, list):
        return None
    state = players.get(player)
    if state is None or getattr(state, "last_step", None) != step:
        return None
    plan = getattr(state, "plan", None)
    if type(plan) is not int or not (0 <= plan < len(tapes)):
        return None
    tape = tapes[plan]
    if not isinstance(tape, list) or step + 1 >= len(tape):
        return None
    next_authored = tape[step + 1]
    if not isinstance(next_authored, dict):
        return None

    blocked = []
    queues = getattr(state, "queues", None)
    if queues is None:
        queues = {}
    if not isinstance(queues, dict):
        return None
    for worker, queue in queues.items():
        if type(worker) is not int or worker < 0:
            return None
        try:
            has_debt = len(queue) > 0
        except TypeError:
            return None
        if has_debt:
            blocked.append(worker)
    return next_authored, tuple(blocked), plan


def agent(observation, configuration=None):
    action = BASE(observation, configuration)
    if not _standard_clock(configuration):
        REPORT["config_reject"] += 1
        return action
    context = _next_authored_and_blocked(observation)
    if context is None:
        REPORT["context_reject"] += 1
        return action
    next_authored, blocked, plan = context
    result, activations = apply_melon_jit_fertilize(
        action,
        observation,
        next_authored,
        blocked_workers=blocked,
        enabled=True,
    )
    if not activations:
        return action
    REPORT["activations"] += len(activations)
    REPORT["fertilizer_units_requested"] += len(activations)
    for event in activations:
        if len(TRACE) >= 512:
            break
        row = dict(event)
        row["plan"] = plan
        TRACE.append(row)
    return result


agent.telemetry = REPORT
agent.trace = TRACE

A5_EVALUATOR_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "a5_melon_jit_fertilize": True,
    "a5_evidence_boundary": "next_authored_water_not_guaranteed_next_actual_action",
    "official_interpreter_commit": "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c",
    "official_engine_sha256": "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e",
}
