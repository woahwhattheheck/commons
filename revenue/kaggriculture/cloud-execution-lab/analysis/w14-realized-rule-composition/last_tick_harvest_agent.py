#!/usr/bin/env python3
"""Evaluator-only wrapper around the exact colocated current TITAN ``main.py``.

A hosted workflow copies this file and ``last_tick_harvest.py`` beside the
canonical archive's ``main.py``.  ``_w14`` is test telemetry; the paired runner
must remove it before calling the official interpreter.
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from last_tick_harvest import rewrite_last_tick_crop_harvest


def _load_base():
    path = HERE / "main.py"
    if not path.is_file():
        raise FileNotFoundError(f"canonical base agent not colocated: {path}")
    spec = importlib.util.spec_from_file_location("w14_exact_base_titan", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load canonical base agent: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    function = getattr(module, "agent")
    if not callable(function):
        raise TypeError("canonical main.py::agent is not callable")
    try:
        inspect.signature(function).bind({}, {})
        takes_configuration = True
    except TypeError:
        inspect.signature(function).bind({})
        takes_configuration = False
    return function, takes_configuration


_BASE_AGENT, _TAKES_CONFIGURATION = _load_base()


def agent(observation, configuration=None):
    selected = (
        _BASE_AGENT(observation, configuration)
        if _TAKES_CONFIGURATION
        else _BASE_AGENT(observation)
    )
    rewritten, receipt = rewrite_last_tick_crop_harvest(
        observation,
        selected,
        configuration,
    )
    if "_w14" in rewritten:
        raise ValueError("canonical action unexpectedly owns reserved _w14 telemetry key")
    rewritten["_w14"] = receipt
    return rewritten


__all__ = ["agent"]
