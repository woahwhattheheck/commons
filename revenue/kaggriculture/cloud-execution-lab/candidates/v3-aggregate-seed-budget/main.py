# SPDX-License-Identifier: Apache-2.0
"""Default-off experimental entrypoint for aggregate seed-budget admission."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_PARENT = _load("_titan_granary_parent", ROOT / "main.py")
from candidate_runtime import apply_completed_action


def _record(instance, report):
    diagnostics = getattr(instance, "diagnostics", None)
    if isinstance(diagnostics, dict):
        diagnostics["aggregate_seed_budget"] = dict(report)


def agent(observation, configuration=None):
    """Call canonical TITAN exactly once, then use only its reserved tail time."""
    started = time.perf_counter()
    selected = _PARENT.agent(observation, configuration)
    instance = getattr(_PARENT, "_INSTANCE", None)
    if instance is None:
        return selected

    features = getattr(instance, "features", None)
    try:
        budget = float(features.budget_seconds)
        reserve = float(features.reserve_seconds)
    except (AttributeError, TypeError, ValueError, OverflowError):
        _record(instance, {"changed": False, "reason": "invalid_parent_deadline"})
        return selected

    remaining = budget - (time.perf_counter() - started)
    guard = max(0.001, reserve / 3.0)
    if remaining <= guard:
        _record(instance, {
            "changed": False,
            "reason": "insufficient_reserved_time",
            "remaining_seconds": remaining,
            "guard_seconds": guard,
        })
        return selected

    deadline = getattr(sys.modules.get("titan_runtime"), "deadline", None)
    timer_type = getattr(deadline, "_DeadlineTimer", None)
    deadline_error = getattr(deadline, "DeadlineExceeded", None)
    if timer_type is None or deadline_error is None:
        _record(instance, {"changed": False, "reason": "deadline_guard_unavailable"})
        return selected

    timer = timer_type(remaining - guard)
    try:
        with timer:
            result, report = apply_completed_action(
                instance, dict(observation), dict(configuration or {}), selected)
    except deadline_error as error:
        if error is not timer.expired:
            raise
        _record(instance, {"changed": False, "reason": "candidate_deadline_fallback"})
        return selected
    except Exception as error:  # Candidate failure must never forfeit a game.
        _record(instance, {
            "changed": False,
            "reason": "candidate_exception",
            "error": type(error).__name__,
        })
        return selected

    _record(instance, report)
    return result
