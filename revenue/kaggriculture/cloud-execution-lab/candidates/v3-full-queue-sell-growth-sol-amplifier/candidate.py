# SPDX-License-Identifier: Apache-2.0
"""Canonical TITAN entrypoint with isolated saturated-queue SELL expansion."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
EXPECTED_GIT_BLOBS = {
    HERE / "growth_patch.py": "f1803dafb558745376f28d3c9e005c4688ff4452",
    LAB / "main.py": "4a8cf7bcda1f0fea231a144692cb84a779a9e73e",
    LAB / "titan_runtime.py": "b952c9c228ecbde592bf3d2df01638677abb0d24",
    LAB / "frozen_selected.py": "fc7baf5c179818a55037f6a61d92984d81d1a21c",
    LAB / "TITAN-CONFIG.json": "3a3bef83899d3010fad623b628d9e95d9978111b",
}


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _verify_execution_closure() -> dict[str, str]:
    receipt: dict[str, str] = {}
    for path, expected in EXPECTED_GIT_BLOBS.items():
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"SOL-AMPLIFIER dependency is not a regular file: {path}")
        actual = _git_blob_sha1(path)
        if actual != expected:
            raise RuntimeError(
                f"SOL-AMPLIFIER dependency drift: {path.name}; "
                f"expected {expected}, got {actual}"
            )
        receipt[path.relative_to(HERE.parent.parent).as_posix()] = actual
    return receipt


_EXECUTION_CLOSURE = _verify_execution_closure()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

from growth_patch import attach  # noqa: E402  (verified before execution)


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

    _LAST_INSTALL_RECEIPT = {
        **attach(instance, frozen_selected),
        "execution_closure": dict(_EXECUTION_CLOSURE),
    }
    return instance


# Canonical agent resolves this global during its existing timed construction.
# Its prelude, whole-call deadline, fallback, reconstruction and final-pressure
# return boundary remain the original implementation.
_CANONICAL._new_instance = _candidate_new_instance


def agent(observation, configuration=None):
    return _CANONICAL.agent(observation, configuration)
