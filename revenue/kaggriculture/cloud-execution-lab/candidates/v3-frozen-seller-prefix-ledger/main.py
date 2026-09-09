# SPDX-License-Identifier: Apache-2.0
"""TITAN V3 exact-prefix seller-ledger candidate entrypoint."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
_CANONICAL = None

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

from prefix_ledger import install


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _initialize():
    global _CANONICAL
    if _CANONICAL is not None:
        return
    canonical = _load("_prefix_ledger_canonical", LAB / "main.py")
    original_new_instance = canonical._new_instance

    def new_instance(root, feature_data):
        return install(original_new_instance(root, feature_data))

    canonical._new_instance = new_instance
    _CANONICAL = canonical


def agent(observation, configuration=None):
    """Delegate to the canonical entrypoint with reconstruction-safe install."""
    if _CANONICAL is None:
        _initialize()
    return _CANONICAL.agent(observation, configuration)


def diagnostics():
    """Return a detached evidence-only receipt; Kaggle calls only ``agent``."""
    if _CANONICAL is None:
        return None
    instance = getattr(_CANONICAL, "_INSTANCE", None)
    if instance is None:
        return None
    return {
        "agent": deepcopy(getattr(instance, "diagnostics", {})),
        "prefix_ledger": deepcopy(getattr(instance, "_prefix_ledger_state", {})),
    }
