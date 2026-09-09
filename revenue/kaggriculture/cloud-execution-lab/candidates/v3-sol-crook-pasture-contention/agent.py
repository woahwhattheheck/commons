# SPDX-License-Identifier: Apache-2.0
"""SOL-CROOK candidate bound inside the canonical TITAN producer lifecycle."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
from types import MethodType

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
_parent_new_instance = _parent._new_instance


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
            "boundary": "spatial_transform_before_consumer",
            "report": report,
            "before": before,
            "after": after,
        }
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
    except (OSError, TypeError, ValueError):
        return


def _bind_producer_boundary(instance):
    """Install once, after SpatialTempo exists but before its producer is used.

    SpatialTempo's installed controller closure resolves ``self.transform`` on
    every call. Replacing that method after canonical initialization therefore
    changes the selected producer bytes before FrozenSelected simulates units,
    before seller checkpoints, and before every final receipt. Reconstruction
    retains the SpatialTempo object and installs the same wrapped transform on
    the replacement controller without nesting another wrapper.
    """
    original_initialize = instance._initialize

    def initialize(self):
        original_initialize()
        spatial = getattr(self, "spatial", None)
        if spatial is None or getattr(spatial, "_sol_crook_installed", False):
            return
        spatial._sol_crook_parent_transform = spatial.transform

        def guarded_transform(observation, selected, controller):
            produced = spatial._sol_crook_parent_transform(
                observation, selected, controller
            )
            repaired, report = _guard.repair_selected(observation, produced)
            self.diagnostics["pasture_contention"] = report
            _record(observation, produced, repaired, report)
            return repaired

        spatial.transform = guarded_transform
        spatial._sol_crook_installed = True
        spatial._sol_crook_boundary = "before_frozen_selected"

    instance._initialize = MethodType(initialize, instance)
    instance._sol_crook_initialize_bound = True
    return instance


def _new_instance(root, feature_data):
    return _bind_producer_boundary(_parent_new_instance(root, feature_data))


# Preserve the exact canonical entrypoint, deadline guard, reset policy,
# FinalPressure subclass, and fallback behavior. Only its instance constructor
# receives the one-time producer-boundary binding above.
_parent._new_instance = _new_instance


def agent(observation, configuration=None):
    return _parent.agent(observation, configuration)
