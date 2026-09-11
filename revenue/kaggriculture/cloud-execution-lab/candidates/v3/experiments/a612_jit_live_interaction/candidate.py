#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Evidence-only composition of exact JIT helper on shipped a612 R04.

The parent action is the exact live tuple (H4 + rival-gated L3 on, current
cattle/sale-fertilizer settings preserved).  Only after that action is produced
does this wrapper offer a literal PASS to the exact reviewed JIT helper.  The
helper's ``next_authored`` input is the same-plan next raw R04 tape row used by
the original execution receipt.

This is not production wiring.  It exists to answer the missing post-ship
interaction question before anyone edits package/default bytes.
"""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
LAB = HERE.parents[4]
OVERLAY = V3 / "overlay"
JIT_DIR = LAB / "analysis" / "v31-b5-fertilizer-jit"
for path in (OVERLAY, JIT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_full_router as base  # noqa: E402
from jit_pass_fertilize import apply_jit_pass_fertilize  # noqa: E402

LIVE_A612 = {
    "horizon": 8,
    "opening": 0,
    "row_order": True,
    "evening_flush": True,
    "sale_fertilizer": True,
    "cattle_early": True,
    "kill_late_water": False,
    "strawberry_endgame": False,
    "strawberry_max_plants": 8,
    "no_late_sale_advance": True,
    "no_late_sale_advance_step": 648,
    "strawberry_topup": True,
}

BASE_AGENT = base.install(
    None,
    LIVE_A612["horizon"],
    LIVE_A612["opening"],
    LIVE_A612["row_order"],
    LIVE_A612["evening_flush"],
    LIVE_A612["sale_fertilizer"],
    LIVE_A612["cattle_early"],
    LIVE_A612["kill_late_water"],
    LIVE_A612["strawberry_endgame"],
    LIVE_A612["strawberry_max_plants"],
    LIVE_A612["no_late_sale_advance"],
    LIVE_A612["no_late_sale_advance_step"],
    LIVE_A612["strawberry_topup"],
)

REPORT = {
    "calls": 0,
    "activation_calls": 0,
    "activations": 0,
    "activation_steps": {},
    "activation_crops": {},
}


def _next_authored(observation):
    """Return exact next raw row for the current live R04 plan, else None."""
    if type(observation) is not dict:
        return None
    step = observation.get("step")
    player = observation.get("player")
    if type(step) is not int or type(player) is not int:
        return None
    if step < 0 or step >= base.LAST_STEP or player not in (0, 1):
        return None
    policy = base._POLICY
    if policy is None:
        return None
    state = policy.players.get(player)
    if state is None or type(state.plan) is not int or not (0 <= state.plan < len(policy.tapes)):
        return None
    tape = policy.tapes[state.plan]
    if step + 1 >= len(tape):
        return None
    return tape[step + 1]


def agent(observation, configuration=None):
    action = BASE_AGENT(observation, configuration)
    REPORT["calls"] += 1
    following = _next_authored(observation)
    if following is None:
        return action
    output, activations = apply_jit_pass_fertilize(
        action, observation, following, enabled=True
    )
    if activations:
        REPORT["activation_calls"] += 1
        REPORT["activations"] += len(activations)
        for event in activations:
            step = str(event["step"])
            crop = str(event["crop"])
            REPORT["activation_steps"][step] = REPORT["activation_steps"].get(step, 0) + 1
            REPORT["activation_crops"][crop] = REPORT["activation_crops"].get(crop, 0) + 1
    return output


agent.telemetry = REPORT
