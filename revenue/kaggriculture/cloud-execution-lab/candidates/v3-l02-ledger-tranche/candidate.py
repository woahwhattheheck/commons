# SPDX-License-Identifier: Apache-2.0
"""TITAN L02 candidate entrypoint: one canonical producer plus one selected overlay."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

from ledger_tranche import install


def _load_canonical():
    spec = importlib.util.spec_from_file_location("_l02_canonical_entry", LAB / "main.py")
    if spec is None or spec.loader is None:
        raise ImportError("cannot load canonical TITAN entrypoint")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_CANONICAL = _load_canonical()
_INSTANCE = None


def agent(observation, configuration=None):
    """Construct exactly one configured TitanAgent and install L02 before first act."""
    global _INSTANCE
    entry_started = time.perf_counter()
    cfg = dict(configuration or {})
    step = observation.get("step")
    if step is None:
        step = (int(observation["day"]) * int(cfg.get("turnsPerDay", 24))
                + int(observation["hour"]))
    if _INSTANCE is None or int(step) == 0:
        feature_data = json.loads((LAB / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        _INSTANCE = _CANONICAL._new_instance(LAB, feature_data)
        install(_INSTANCE)
    return _INSTANCE.act(observation, cfg, entry_started=entry_started)
