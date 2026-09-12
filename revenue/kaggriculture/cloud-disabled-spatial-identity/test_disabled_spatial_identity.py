#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Assert that disabled SpatialTempo installation is a strict identity."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("candidate_spatial_tempo", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def controller() -> Any:
    class Controller:
        pass

    value = Controller()
    value.R = {"producer-route": [["PASS"]]}
    value.act = lambda observation: {"farmer": ["PASS"], "hands": [], "market": []}
    return value


def evaluate(module_path: Path) -> dict[str, Any]:
    module = load_module(module_path)

    disabled = controller()
    disabled_act = disabled.act
    disabled_routes = disabled.R
    module.SpatialTempo(None, pathing=False, tempo=False).install(disabled)

    enabled = controller()
    enabled_act = enabled.act
    enabled_routes = enabled.R
    module.SpatialTempo(None, pathing=True, tempo=False).install(enabled)

    checks = {
        "disabled_act_identity": disabled.act is disabled_act,
        "disabled_routes_identity": disabled.R is disabled_routes,
        "enabled_act_is_wrapped": enabled.act is not enabled_act,
        "enabled_routes_identity_at_install": enabled.R is enabled_routes,
    }
    return {
        "schema_version": 1,
        "module": str(module_path),
        "checks": checks,
        "pass": all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("module", type=Path, help="path to spatial_tempo.py")
    args = parser.parse_args()
    result = evaluate(args.module.resolve())
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
