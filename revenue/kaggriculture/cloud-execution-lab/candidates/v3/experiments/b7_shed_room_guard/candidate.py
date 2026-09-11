#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact evaluator entrypoint for the default-off B7 shed-room guard experiment."""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve()
EXPERIMENTS = HERE.parents[1]
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
for path in (EXPERIMENTS, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from b7_shed_room_guard import install as install_b7  # noqa: E402
from r04_full_router import install as install_r04  # noqa: E402

# Exact ready-submission V3.1 R04 tuple. B7 remains experiment-only and outside
# deterministic package inputs until execution evidence proves useful activations.
BASE = install_r04(
    None,
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
)

agent = install_b7(BASE, enabled=True)

B7_EVALUATOR_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "b7_shed_room_guard": True,
    "official_interpreter_commit": "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c",
    "official_engine_sha256": "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e",
}
