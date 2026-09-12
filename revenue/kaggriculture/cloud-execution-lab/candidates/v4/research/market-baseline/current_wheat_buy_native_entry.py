#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""TEST-ONLY transparent telemetry wrapper for returned BUY_PRODUCT rows.

The current native parent's action object is returned unchanged.  Telemetry is
advisory evidence only and cannot authorize, add, suppress, reorder, or resize an
order.  Any telemetry exception is counted and swallowed after the parent action
has already been obtained.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys

LAB = Path(__file__).resolve().parents[4]
TELEMETRY_PATH = os.environ.get("TOWNPROCURE_TELEMETRY_PATH")
_parent = None
stats = {
    "callback_attempts": 0,
    "callbacks": 0,
    "telemetry_errors": 0,
    "buy_product_rows_by_item": {},
    "wheat_buy_callbacks": 0,
    "wheat_buy_rows": 0,
    "wheat_buy_units": 0,
    "witnesses": [],
}


def _load_parent():
    global _parent
    if _parent is not None:
        return
    root = str(LAB)
    if root not in sys.path:
        sys.path.insert(0, root)
    path = LAB / "main.py"
    spec = importlib.util.spec_from_file_location("townprocure_current_parent", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _parent = module


def _get(obj, name, default=None):
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


def _record(step, action) -> None:
    stats["callback_attempts"] += 1
    try:
        market = action.get("market") or [] if isinstance(action, dict) else []
        wheat_here = []
        for row_index, raw in enumerate(market):
            if not isinstance(raw, list) or not raw or raw[0] != "BUY_PRODUCT":
                continue
            item = raw[1] if len(raw) > 1 else None
            quantity = raw[2] if len(raw) > 2 else None
            key = str(item)
            bucket = stats["buy_product_rows_by_item"]
            bucket[key] = bucket.get(key, 0) + 1
            if item != "WHEAT":
                continue
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
                raise ValueError(f"invalid returned WHEAT purchase quantity: {quantity!r}")
            stats["wheat_buy_rows"] += 1
            stats["wheat_buy_units"] += quantity
            wheat_here.append({"row_index": row_index, "quantity": quantity})
        if wheat_here:
            stats["wheat_buy_callbacks"] += 1
            if len(stats["witnesses"]) < 128:
                stats["witnesses"].append({"step": step, "rows": wheat_here})
        stats["callbacks"] += 1
    except Exception:
        stats["telemetry_errors"] += 1


def _write() -> None:
    if not TELEMETRY_PATH:
        return
    try:
        path = Path(TELEMETRY_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(stats, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def agent(observation, configuration=None):
    _load_parent()
    parent = _parent.agent(observation, configuration)
    step = _get(observation, "step")
    _record(step, parent)
    episode_steps = _get(configuration, "episodeSteps", 720)
    if type(step) is int and type(episode_steps) is int and step >= episode_steps - 2:
        _write()
    return parent
