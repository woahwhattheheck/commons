# SPDX-License-Identifier: Apache-2.0
"""Canonical TITAN entrypoint with isolated saturated-queue SELL expansion."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any

from growth_patch import attach

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))


def _load(name: str, path: Path):
    if not path.is_file():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_CANONICAL = _load("_sol_amplifier_full_queue_growth_main", LAB / "main.py")
_ORIGINAL_NEW_INSTANCE = _CANONICAL._new_instance
_LAST_INSTALL_RECEIPT: dict[str, Any] | None = None


def _candidate_new_instance(root: Path, feature_data: dict[str, Any]):
    """Attach the private selected-seller class before canonical lazy init."""
    global _LAST_INSTALL_RECEIPT
    instance = _ORIGINAL_NEW_INSTANCE(root, feature_data)
    import frozen_selected

    _LAST_INSTALL_RECEIPT = attach(instance, frozen_selected)
    return instance


# Canonical agent resolves this global during its existing timed construction.
# Its prelude, whole-call deadline, fallback, reconstruction and final-pressure
# return boundary remain the original implementation.
_CANONICAL._new_instance = _candidate_new_instance


def agent(observation, configuration=None):
    return _CANONICAL.agent(observation, configuration)
