# SPDX-License-Identifier: Apache-2.0
"""Stacked L3 successor: restore baseline E184 in the final 20 decision steps.

This experiment imports the exact reviewed public-supply conditioner from
``../l3_public_supply_gate/candidate.py`` and changes only one policy boundary:
L3 may suppress reservations through step 699, but step >= 700 always keeps
baseline E184 reservation behavior.

The public-supply theorem, 8-transition warmup, strict public-state parsing,
#12377 debt seam and all package/default boundaries remain owned by the parent.
This child is default-off experiment code only.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PARENT_PATH = HERE.parent / "l3_public_supply_gate" / "candidate.py"
SPEC = importlib.util.spec_from_file_location(
    "l3_public_supply_gate_parent", PARENT_PATH
)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"cannot load parent conditioner: {PARENT_PATH}")
parent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parent)

TERMINAL_GUARD_STEP = 700
TAIL_REPORT = {"tail_guarded": 0, "last_tail_guard": None}
_PARENT_CONDITIONAL = parent._conditional_suppressed


def _tail_guarded_suppressed(
    step: Any,
    enabled: Any,
    threshold: Any = parent.l3.DEFAULT_THRESHOLD,
) -> bool:
    """Delegate to the reviewed parent, forcing baseline behavior at step >=700."""
    parsed_step = int(step)
    parsed_threshold = int(threshold)
    if bool(enabled) and parsed_step >= parsed_threshold and parsed_step >= TERMINAL_GUARD_STEP:
        TAIL_REPORT["tail_guarded"] += 1
        TAIL_REPORT["last_tail_guard"] = parsed_step
        prior = parent._ALLOW_SUPPRESS
        parent._ALLOW_SUPPRESS = False
        try:
            # Delegation preserves the parent's late_decisions/guarded telemetry.
            return _PARENT_CONDITIONAL(parsed_step, enabled, parsed_threshold)
        finally:
            parent._ALLOW_SUPPRESS = prior
    return _PARENT_CONDITIONAL(parsed_step, enabled, parsed_threshold)


# parent.agent resolves its module-global callback at call time. Replacing only
# that callback leaves its exact gate state machine and l3.suppressed finally
# restoration unchanged.
parent._conditional_suppressed = _tail_guarded_suppressed
agent = parent.agent
agent.tail_telemetry = TAIL_REPORT
