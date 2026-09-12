# SPDX-License-Identifier: Apache-2.0
"""TEST-ONLY current-runtime entry for the default-OFF WF1 wheat-fertilize adapter.

This file is an execution fixture, not production wiring.  It delegates every
callback to the unmodified native ``main.py::agent`` first, then applies the
source-bound ``wf1_current_adapter`` with its current guards enabled.  The
fixture is intended to be copied beside an authenticated runtime package.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
TELEMETRY_PATH = os.environ.get("WF1_TELEMETRY_PATH")
_parent = None
_adapter = None
stats = {
    "callbacks": 0,
    "transformed_actions": 0,
    "changed_unit_rows": 0,
    "changed_market_callbacks": 0,
    "first_change_step": None,
    "last_change_step": None,
}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _ensure_loaded():
    global _parent, _adapter
    root = str(ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    if _parent is None:
        _parent = _load("wf1_native_parent", ROOT / "main.py")
    if _adapter is None:
        _adapter = _load("wf1_current_adapter_runtime", ROOT / "wf1_current_adapter.py")


def _cfg(configuration, name: str, default=None):
    if isinstance(configuration, dict):
        return configuration.get(name, default)
    return getattr(configuration, name, default)


def _write_telemetry(configuration) -> None:
    if not TELEMETRY_PATH or _adapter is None:
        return
    try:
        payload = dict(stats)
        donor = getattr(_adapter, "_donor", None)
        report = getattr(donor, "REPORT", None)
        if isinstance(report, dict):
            payload["donor_report"] = dict(report)
        path = Path(TELEMETRY_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    except Exception:
        # Telemetry must never affect the returned action.
        pass


def agent(observation, configuration=None):
    _ensure_loaded()
    parent = _parent.agent(observation, configuration)
    candidate = _adapter.apply_wf1_current(observation, parent, configuration, enabled=True)
    stats["callbacks"] += 1
    if candidate != parent:
        stats["transformed_actions"] += 1
        before_rows = [parent.get("farmer"), *(parent.get("hands") or [])]
        after_rows = [candidate.get("farmer"), *(candidate.get("hands") or [])]
        stats["changed_unit_rows"] += sum(a != b for a, b in zip(before_rows, after_rows))
        stats["changed_market_callbacks"] += int(parent.get("market") != candidate.get("market"))
        step = observation.get("step") if isinstance(observation, dict) else getattr(observation, "step", None)
        stats["last_change_step"] = step
        if stats["first_change_step"] is None:
            stats["first_change_step"] = step
    step = observation.get("step") if isinstance(observation, dict) else getattr(observation, "step", None)
    episode_steps = _cfg(configuration, "episodeSteps", 720)
    if type(step) is int and type(episode_steps) is int and step >= episode_steps - 2:
        _write_telemetry(configuration)
    return candidate
