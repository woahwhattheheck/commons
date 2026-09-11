#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Current-root loader for the exact reviewed C4 donor.

The reviewed #12468 donor is preserved byte-for-byte in the sibling
``c4_town_demand_boundary`` directory.  Its historical relative-path bootstrap points one
parent too high after transplantation under ``candidates/v3/experiments``.  This loader fixes
only that custody seam: it pre-binds the literal current V3 overlay, executes the untouched
donor, and refuses to expose an agent unless the donor's ``r04_full_router`` module resolves to
the shipped checkout path.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
OVERLAY = (V3 / "overlay").resolve()
DONOR = (HERE.parent / "c4_town_demand_boundary" / "candidate.py").resolve()
EXPECTED_R04 = (OVERLAY / "r04_full_router.py").resolve()

if not DONOR.is_file() or not EXPECTED_R04.is_file():
    raise ImportError("C4 current-root donor or shipped R04 is missing")

# Put the exact current overlay ahead of ambient paths.  The reviewed donor's historical
# bootstrap may subsequently add a nonexistent .../candidates/overlay entry at index 0; Python
# will skip that path and resolve r04_full_router from this exact existing directory.
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

spec = importlib.util.spec_from_file_location("_titan_c4_reviewed_donor", DONOR)
if spec is None or spec.loader is None:
    raise ImportError("cannot load reviewed C4 donor")
impl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(impl)

actual_r04 = Path(impl.base.__file__).resolve()
if actual_r04 != EXPECTED_R04:
    raise ImportError(f"C4 R04 custody mismatch: {actual_r04} != {EXPECTED_R04}")

# Candidate entry surface.  Do not copy or reinterpret C4 gameplay logic here.
agent = impl.agent
install = impl.install
telemetry = impl.telemetry
C4_EVALUATOR_CONFIG = impl.C4_EVALUATOR_CONFIG
