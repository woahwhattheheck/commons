# SPDX-License-Identifier: Apache-2.0
"""Playable repository entrypoint for the exact-bound multi-lot portfolio candidate."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
for path in reversed((HERE, LAB)):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from candidate_patch import git_blob_sha, patch_scheduler_path

EXPECTED_OBSERVED_CLONE_GIT_BLOB = "f810d53193d3035655a36c21021e18ba1d415916"
OBSERVED_CLONE_SOURCE = LAB.parent / "cloud-runtime-pulse" / "observed_clone.py"


def _install_exact_observed_clone() -> None:
    """Expose the archive-root dependency without accepting ambient shadowing."""
    source = OBSERVED_CLONE_SOURCE.resolve()
    if not source.is_file():
        raise RuntimeError(f"observed_clone source missing: {source}")
    actual = git_blob_sha(source.read_bytes())
    if actual != EXPECTED_OBSERVED_CLONE_GIT_BLOB:
        raise RuntimeError(
            "observed_clone Git blob drift: "
            f"expected {EXPECTED_OBSERVED_CLONE_GIT_BLOB}, got {actual}"
        )

    existing = sys.modules.get("observed_clone")
    if existing is not None:
        origin_text = getattr(existing, "__file__", None)
        if not origin_text:
            raise RuntimeError("ambient observed_clone has no auditable origin")
        origin = Path(origin_text).resolve()
        if not origin.is_file() or git_blob_sha(origin.read_bytes()) != EXPECTED_OBSERVED_CLONE_GIT_BLOB:
            raise RuntimeError(f"ambient observed_clone does not match pinned bytes: {origin}")
        return

    spec = importlib.util.spec_from_file_location("observed_clone", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load observed_clone from {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["observed_clone"] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop("observed_clone", None)
        raise


_install_exact_observed_clone()

SOURCE = LAB / "scheduler.py"
PATCHED_SOURCE = patch_scheduler_path(SOURCE)
MODULE_NAME = "titan_v3_multi_lot_portfolio_scheduler"
_module = types.ModuleType(MODULE_NAME)
_module.__file__ = str(SOURCE)
_module.__package__ = ""
sys.modules[MODULE_NAME] = _module
exec(compile(PATCHED_SOURCE, str(SOURCE), "exec"), _module.__dict__)

SellScheduler = _module.SellScheduler
agent = _module.agent
naive_agent = _module.naive_agent
