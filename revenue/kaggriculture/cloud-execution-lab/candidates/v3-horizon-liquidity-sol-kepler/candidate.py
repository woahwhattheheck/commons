# SPDX-License-Identifier: Apache-2.0
"""Canonical TITAN entrypoint with one V1 horizon-liquidity factor restored."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any

from liquidity_haircut import install

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


_CANONICAL = _load("_sol_kepler_horizon_liquidity_main", LAB / "main.py")
_ORIGINAL_NEW_INSTANCE = _CANONICAL._new_instance
_LAST_INSTALL_RECEIPT: dict[str, Any] | None = None


def _candidate_new_instance(root: Path, feature_data: dict[str, Any]):
    """Install before canonical lazy initialization, then construct unchanged."""
    global _LAST_INSTALL_RECEIPT
    import scheduler

    _LAST_INSTALL_RECEIPT = install(scheduler)
    instance = _ORIGINAL_NEW_INSTANCE(root, feature_data)
    instance.horizon_liquidity_receipt = dict(_LAST_INSTALL_RECEIPT)
    return instance


# canonical ``agent`` resolves this global at runtime.  Replacing only this hook
# retains its prelude, whole-call deadline, fallback, reconstruction, and final
# pressure ordering byte-for-byte.
_CANONICAL._new_instance = _candidate_new_instance


def agent(observation, configuration=None):
    return _CANONICAL.agent(observation, configuration)
