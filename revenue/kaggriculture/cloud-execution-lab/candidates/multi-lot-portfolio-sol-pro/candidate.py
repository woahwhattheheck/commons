# SPDX-License-Identifier: Apache-2.0
"""Playable repository entrypoint for the exact-bound multi-lot portfolio candidate."""
from __future__ import annotations

from pathlib import Path
import sys
import types

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
for path in (HERE, LAB):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from candidate_patch import patch_scheduler_path

SOURCE = LAB / "scheduler.py"
PATCHED_SOURCE = patch_scheduler_path(SOURCE)
MODULE_NAME = "titan_v3_multi_lot_portfolio_scheduler"
_module = types.ModuleType(MODULE_NAME)
_module.__file__ = str(SOURCE)
_module.__package__ = ""
sys.modules[MODULE_NAME] = _module
exec(compile(PATCHED_SOURCE, str(SOURCE), "exec"), _module.__dict__)

SellScheduler = _module.SellScheduler
agent = _module.agent
naive_agent = _module.naive_agent
