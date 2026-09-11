# SPDX-License-Identifier: Apache-2.0
"""Mechanical current-6e5 adapter for the reviewed C6 donor.

The reviewed #12452 candidate is imported byte-for-byte, then its parent R04
installation is rebound to the literal repaired-P0 / shipped-8e3 tuple.  No C6
accounting, reserve, debt, market-row, or telemetry logic is reimplemented here.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "candidate.py"
spec = importlib.util.spec_from_file_location("c6_reviewed_source_current6e5", SOURCE)
if spec is None or spec.loader is None:
    raise ImportError(f"cannot load reviewed C6 donor: {SOURCE}")
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)

CURRENT_R04_TUPLE = {
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
    "b5_carrot_fertilizer": True,
    "b5_jit_fertilize": True,
}

# Importing the reviewed donor necessarily executes its historical install call.
# Immediately restore the complete literal 6e5/8e3 tuple before any agent call.
source._BASE_AGENT = source.base.install(**CURRENT_R04_TUPLE)


def agent(observation, configuration=None):
    """Delegate exactly to the reviewed C6 agent after current-stack rebinding."""
    return source.agent(observation, configuration)


agent.telemetry = source.REPORT
