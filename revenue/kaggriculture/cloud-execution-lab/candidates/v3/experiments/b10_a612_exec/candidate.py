# SPDX-License-Identifier: Apache-2.0
"""Exact a612 parent followed by the byte-reviewed B10 ordering transform."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
OVERLAY = V3 / "overlay"
DONOR_PATH = V3 / "experiments" / "b10_rival_supply_order" / "candidate.py"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

spec = importlib.util.spec_from_file_location("b10_reviewed_donor", DONOR_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load reviewed B10 donor")
donor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(donor)
base = donor.base

CANONICAL_A612_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "r04_kill_late_water": False,
    "r04_strawberry_endgame": False,
    "r04_strawberry_max_plants": 8,
    "r04_no_late_sale_advance": True,
    "r04_no_late_sale_advance_step": 648,
    "r04_strawberry_topup": True,
}

# Importing the frozen reviewed donor constructs its historical experiment entrypoint.
# Reinstall immediately so the actual parent action below is the exact shipped a612 tuple.
PARENT_AGENT = base.install(
    None,
    horizon=CANONICAL_A612_CONFIG["r04_sale_horizon"],
    opening=CANONICAL_A612_CONFIG["r04_open_roundtrip"],
    row_order=CANONICAL_A612_CONFIG["r04_row_order"],
    evening_flush=CANONICAL_A612_CONFIG["r04_evening_flush"],
    sale_fertilizer=CANONICAL_A612_CONFIG["r04_sale_fertilizer"],
    cattle_early=CANONICAL_A612_CONFIG["r04_cattle_early"],
    kill_late_water=CANONICAL_A612_CONFIG["r04_kill_late_water"],
    strawberry_endgame=CANONICAL_A612_CONFIG["r04_strawberry_endgame"],
    strawberry_max_plants=CANONICAL_A612_CONFIG["r04_strawberry_max_plants"],
    no_late_sale_advance=CANONICAL_A612_CONFIG["r04_no_late_sale_advance"],
    no_late_sale_advance_step=CANONICAL_A612_CONFIG["r04_no_late_sale_advance_step"],
    strawberry_topup=CANONICAL_A612_CONFIG["r04_strawberry_topup"],
)
ORDER = donor.RivalSupplyOrder(enabled=True)


def agent(observation, configuration=None):
    parent = PARENT_AGENT(observation, configuration)
    return ORDER.apply(observation, parent, configuration)


agent.telemetry = ORDER.telemetry
