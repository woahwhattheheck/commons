# SPDX-License-Identifier: Apache-2.0
"""SOL-CROOK experimental wrapper around the current canonical TITAN source."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_parent = _load("_sol_crook_parent_main", ROOT / "main.py")
_guard = _load("_sol_crook_pasture_contention", HERE / "pasture_contention.py")


def _record(observation, before, after, report):
    """Write bounded experimental evidence; logging failure never changes play."""
    if not report.get("duplicate_groups"):
        return
    try:
        target = Path(os.environ.get("TITAN_CROOK_LOG", "/tmp/sol-crook-pasture.jsonl"))
        row = {
            "pid": os.getpid(),
            "step": int(observation.get("step", 0)),
            "player": int(observation.get("player", 0)),
            "report": report,
            "before": before,
            "after": after,
        }
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
    except (OSError, TypeError, ValueError):
        return


def agent(observation, configuration=None):
    selected = _parent.agent(observation, configuration)
    repaired, report = _guard.repair_selected(observation, selected)
    _record(observation, selected, repaired, report)
    return repaired
