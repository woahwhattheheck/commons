# SPDX-License-Identifier: Apache-2.0
"""Default-off TITAN candidate with exact operating-stock prefix isolation."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for path in (str(HERE), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import operating_stock as _operating_stock
from active_prefix import install

_original_guard = _operating_stock.protect_operating_stock
_patched_guard = install(_operating_stock)
# Loading the parent needs no patched global. Keep baseline imports uncontaminated
# and expose the adapter only for this candidate's action call.
_operating_stock.protect_operating_stock = _original_guard

_spec = importlib.util.spec_from_file_location(
    "_titan_v3_operating_stock_active_prefix_parent", ROOT / "main.py"
)
if _spec is None or _spec.loader is None:
    raise ImportError("unable to load canonical TITAN entrypoint")
_parent = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_parent)


def agent(observation, configuration=None):
    previous = _operating_stock.protect_operating_stock
    _operating_stock.protect_operating_stock = _patched_guard
    try:
        return _parent.agent(observation, configuration)
    finally:
        _operating_stock.protect_operating_stock = previous
