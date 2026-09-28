# SPDX-License-Identifier: Apache-2.0
"""Runnable TITAN V3 market-carry candidate.

The canonical current entrypoint is called once for each new observation.  This
wrapper only feeds its completed action through the append-only carry overlay.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
_PARENT = None
_OVERLAY = None
_LAST_STEP = None
_LAST_ACTION = None
_LAST_REPORT = None


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _step(observation: Any, configuration: Any) -> int:
    try:
        explicit = observation.get("step")
    except AttributeError:
        explicit = getattr(observation, "step", None)
    if explicit is not None:
        return int(explicit)
    try:
        day = observation.get("day", 0)
        hour = observation.get("hour", 0)
    except AttributeError:
        day = getattr(observation, "day", 0)
        hour = getattr(observation, "hour", 0)
    try:
        turns = configuration.get("turnsPerDay", 24)
    except AttributeError:
        turns = getattr(configuration, "turnsPerDay", 24)
    return int(day) * int(turns) + int(hour)


def _initialize():
    global _PARENT, _OVERLAY
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if _PARENT is None:
        _PARENT = _load("_titan_market_carry_parent", ROOT / "main.py")
    mechanics = _load("_titan_market_carry_mechanics", ROOT / "mechanics.py")
    scheduler = _load("_titan_market_carry_scheduler", ROOT / "scheduler.py")
    carry = _load("_titan_market_carry_overlay", HERE / "market_carry.py")
    _OVERLAY = carry.MarketCarry(mechanics, post_units=scheduler.post_units)


def agent(observation, configuration=None):
    """Return one canonical action with at most one trailing carry purchase."""
    global _LAST_STEP, _LAST_ACTION, _LAST_REPORT, _OVERLAY
    cfg = dict(configuration or {})
    now = _step(observation, cfg)

    # Exact same-step retries return the already completed candidate action and
    # do not advance either the parent or overlay a second time.
    if _LAST_STEP == now and _LAST_ACTION is not None:
        return deepcopy(_LAST_ACTION)

    if _PARENT is None or _OVERLAY is None:
        _initialize()
    if now == 0:
        _PARENT._INSTANCE = None
        _OVERLAY.reset()
        _LAST_STEP = _LAST_ACTION = _LAST_REPORT = None

    selected = _PARENT.agent(observation, cfg)
    returned, report = _OVERLAY.transform(observation, cfg, selected)
    _LAST_STEP = now
    _LAST_ACTION = deepcopy(returned)
    _LAST_REPORT = deepcopy(report)
    return returned


def diagnostics():
    """Expose a copy for offline evidence; Kaggle calls only ``agent``."""
    return deepcopy(_LAST_REPORT)
