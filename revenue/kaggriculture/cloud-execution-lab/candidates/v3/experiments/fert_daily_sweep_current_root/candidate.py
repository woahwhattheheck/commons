#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact Riot fert-daily donor wrapped around the shipped current V3.1 stack.

Composition rule: the shipped parent runs first, including B5 CARROT + JIT. The
fert-daily donor may rewrite only workers that remain PASS afterward. This gives
already-shipped fertilizer work priority rather than reproducing stale-508 layer
ordering by accident.
"""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from baseline import CURRENT_STACK_CONFIG, agent as BASE, r04  # noqa: E402
from donor import apply_fert_daily_sweep, reset  # noqa: E402

reset()


def _active_tape(observation):
    try:
        player = observation["player"]
        if type(player) is not int:
            return None
        state = r04._POLICY.players[player]
        return r04._POLICY.tapes[state.plan]
    except Exception:
        return None


def _engine_shed_capacity(configuration):
    """Mirror the engine's ``int(get(configuration, 'shedCapacity', 100))``."""
    try:
        if configuration is None:
            raw = 100
        elif isinstance(configuration, dict):
            raw = configuration.get("shedCapacity", 100)
        else:
            raw = getattr(configuration, "shedCapacity", 100)
        return int(raw)
    except Exception:
        return None


def agent(observation, configuration=None):
    action = BASE(observation, configuration)
    return apply_fert_daily_sweep(
        observation,
        action,
        _active_tape(observation),
        _engine_shed_capacity(configuration),
    )


FERT_DAILY_CURRENTROOT_CONFIG = dict(CURRENT_STACK_CONFIG)
FERT_DAILY_CURRENTROOT_CONFIG["r04_fert_daily_sweep"] = True
