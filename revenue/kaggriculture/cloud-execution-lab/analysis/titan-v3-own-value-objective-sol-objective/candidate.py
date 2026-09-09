# SPDX-License-Identifier: Apache-2.0
"""TITAN V3 candidate: canonical runtime with one SELL-objective overlay."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LAB = HERE.parent.parent
EXPECTED_MAIN_BLOB = "4a8cf7bcda1f0fea231a144692cb84a779a9e73e"
if LAB.name != "cloud-execution-lab":
    raise ImportError(f"unexpected TITAN lab root: {LAB}")
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

_patch_spec = importlib.util.spec_from_file_location(
    "_titan_v3_own_value_objective_patch", HERE / "own_value_objective.py"
)
if _patch_spec is None or _patch_spec.loader is None:
    raise ImportError("cannot load own-value objective overlay")
_patch = importlib.util.module_from_spec(_patch_spec)
_patch_spec.loader.exec_module(_patch)
INSTALL_RECEIPT = dict(_patch.install(expected_root=LAB))

_raw_main_path = LAB / "main.py"
if _raw_main_path.is_symlink() or not _raw_main_path.is_file():
    raise ImportError(f"canonical TITAN main is not one regular file: {_raw_main_path}")
_main_path = _raw_main_path.resolve()
_main_blob = _patch.git_blob_sha1(_raw_main_path)
if _main_blob != EXPECTED_MAIN_BLOB:
    raise ImportError(
        f"canonical TITAN main Git blob drift: expected {EXPECTED_MAIN_BLOB}, got {_main_blob}"
    )
_main_spec = importlib.util.spec_from_file_location(
    "_titan_v3_own_value_canonical_main", _main_path
)
if _main_spec is None or _main_spec.loader is None:
    raise ImportError("cannot load canonical TITAN main")
_canonical_main = importlib.util.module_from_spec(_main_spec)
_main_spec.loader.exec_module(_canonical_main)
_loaded_main_path = Path(getattr(_canonical_main, "__file__", "")).resolve()
if _loaded_main_path != _main_path:
    raise ImportError(
        f"canonical TITAN main path mismatch: expected {_main_path}, got {_loaded_main_path}"
    )

INSTALL_RECEIPT.update(
    {
        "lab_root": str(LAB.resolve()),
        "canonical_main_path": str(_loaded_main_path),
        "canonical_main_git_blob": _main_blob,
        "expected_canonical_main_git_blob": EXPECTED_MAIN_BLOB,
    }
)


def agent(observation, configuration=None):
    """Delegate unchanged action construction to the exact canonical TITAN entrypoint."""
    return _canonical_main.agent(observation, configuration)
