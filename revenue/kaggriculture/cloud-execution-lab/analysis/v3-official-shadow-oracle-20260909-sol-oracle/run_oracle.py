# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

from official_shadow_oracle import (
    MECHANICS_BLOB,
    audit_contracts,
    canonical_json,
    git_blob,
    official_atomic_plant,
)

HERE = Path(__file__).resolve().parent
DEFAULT_MECHANICS = HERE.parents[1] / "mechanics.py"


def load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("sol_oracle_mechanics", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load mechanics module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mechanics_sequential_probe(mechanics: Any) -> dict[str, Any]:
    """Execute the exact active S01 transition pattern on a minimized fixture."""
    board = 4
    farm = {
        "farmer": [0, 0],
        "hands": [[1, 0]],
        "tiles": [[None for _ in range(board)] for _ in range(board)],
        "money": 0,
    }
    private = {
        "shed": {},
        "seeds": {"WHEAT": 1},
        "inventories": [{}, {}],
    }
    actions = [["PLANT", "WHEAT"], ["PLANT", "WHEAT"]]
    for idx, action in enumerate(actions):
        mechanics._apply_unit_action(farm, private, idx, action, board, 0, 24, 100)
    planted = []
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                planted.append([x, y, tile.get("crop")])
    official = official_atomic_plant(actions, {"WHEAT": 1})
    return {
        "fixture": {"actions": actions, "seeds": {"WHEAT": 1}},
        "official_executable": list(official.executable),
        "sequential_mechanics": {
            "planted": planted,
            "remaining_seeds": private["seeds"],
        },
        "mismatch_detected": bool(planted) and all(a == ["PASS"] for a in official.executable),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Titan v3 official-shadow oracle")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mechanics", type=Path, default=DEFAULT_MECHANICS)
    parser.add_argument("--skip-live-probe", action="store_true")
    args = parser.parse_args()

    report = audit_contracts()
    if not args.skip_live_probe:
        data = args.mechanics.read_bytes()
        blob = git_blob(data)
        if blob != MECHANICS_BLOB:
            raise SystemExit(f"mechanics blob drift: expected {MECHANICS_BLOB}, got {blob}")
        mechanics = load_module(args.mechanics)
        probe = mechanics_sequential_probe(mechanics)
        if not probe["mismatch_detected"]:
            raise SystemExit("negative-control probe no longer discriminates official atomic semantics")
        report["live_negative_control"] = {
            "mechanics_path": str(args.mechanics),
            "mechanics_blob": blob,
            **probe,
        }

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    sys.stdout.write(canonical_json(report) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
