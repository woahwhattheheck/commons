# SPDX-License-Identifier: Apache-2.0
"""Emit a source-bound official-transition and optimizer predecessor witness."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[2]
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

from decay_observer import OPERATION, make_decay_safe_frozen_selected
import candidate
import scheduler


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plant(units: int) -> dict[str, Any]:
    return {
        "kind": "PLANT",
        "crop": "MELON",
        "planted_day": 0,
        "max_lifespan_step": 100,
        "yield_units": units,
        "watered_today": False,
        "consecutive_unwatered": 0,
        "fertilized_until_day": -1,
    }


def observation(step: int, tile: Any) -> dict[str, Any]:
    return {
        "step": step,
        "player": 0,
        "farms": [
            {"tiles": [[None]]},
            {"tiles": [[copy.deepcopy(tile)]]},
        ],
    }


def bare(cls: type) -> Any:
    value = object.__new__(cls)
    value.previous = None
    value.observed_harvests = {}
    return value


def load_engine():
    package = types.ModuleType("kaggle_environments")
    utils = types.ModuleType("kaggle_environments.utils")
    utils.resolve_episode_seed = lambda env: 0
    prior_package = sys.modules.get("kaggle_environments")
    prior_utils = sys.modules.get("kaggle_environments.utils")
    sys.modules["kaggle_environments"] = package
    sys.modules["kaggle_environments.utils"] = utils
    path = LAB / "reference/engine/kaggriculture.py"
    spec = importlib.util.spec_from_file_location("_decay_witness_engine", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if prior_package is None:
        sys.modules.pop("kaggle_environments", None)
    else:
        sys.modules["kaggle_environments"] = prior_package
    if prior_utils is None:
        sys.modules.pop("kaggle_environments.utils", None)
    else:
        sys.modules["kaggle_environments.utils"] = prior_utils
    return module


def run() -> dict[str, Any]:
    engine = load_engine()
    patched_class = make_decay_safe_frozen_selected(
        scheduler.SellScheduler,
        products=scheduler.PRODUCTS,
        animals=scheduler.m.ANIMALS,
    )
    control = bare(scheduler.SellScheduler)
    patched = bare(patched_class)
    farm = {"tiles": [[plant(4)]]}
    current = observation(100, farm["tiles"][0][0])
    control.previous = copy.deepcopy(current)
    patched.previous = copy.deepcopy(current)
    transitions = []
    for step in range(100, 105):
        before = copy.deepcopy(farm["tiles"][0][0])
        engine._decay_plants(farm, step)
        after = copy.deepcopy(farm["tiles"][0][0])
        current = observation(step + 1, after)
        scheduler.SellScheduler.observe(control, copy.deepcopy(current))
        patched_class.observe(patched, copy.deepcopy(current))
        control.previous = copy.deepcopy(current)
        patched.previous = copy.deepcopy(current)
        transitions.append({
            "interpreter_step": step,
            "before_yield": before.get("yield_units") if isinstance(before, dict) else None,
            "after_yield": after.get("yield_units") if isinstance(after, dict) else None,
            "after_kind": after.get("kind") if isinstance(after, dict) else None,
        })

    current_supply = scheduler.SellScheduler.rival_supply(control, current, "MELON")
    patched_supply = patched_class.rival_supply(patched, current, "MELON")
    common = dict(
        item="MELON",
        quantity=2,
        inventory=80,
        params=None,
        shops=[],
        config={"townShopSellInterval": 4, "townCenterSellInterval": 24},
        now=100,
        dates=(100, 104, 108),
        reference=((100, 2),),
        minimum_now=0,
        capacity_ok=lambda _plan: True,
        last=718,
    )
    current_plan, current_info = scheduler.optimize_lot(
        rival_quantity=current_supply, **common
    )
    patched_plan, patched_info = scheduler.optimize_lot(
        rival_quantity=patched_supply, **common
    )
    assert current_supply == 3
    assert patched_supply == 1
    assert current_plan == ((100, 2),)
    assert patched_plan == ((108, 2),)
    assert patched_info["worst_relative_gain"] > 100

    source_sha256 = {
        relative: sha256(LAB / relative)
        for relative in candidate.EXPECTED_GIT_BLOBS
    }
    lane_sha256 = {
        name: sha256(HERE / name)
        for name in ("candidate.py", "decay_observer.py", "test_candidate.py",
                     "test_decay_observer.py", "witness.py")
    }
    return {
        "schema": 1,
        "operation": OPERATION,
        "source_commit": candidate.SOURCE_COMMIT,
        "source_git_blobs": candidate.verify_source(),
        "source_sha256": source_sha256,
        "lane_sha256": lane_sha256,
        "configured_consumer_seam": {
            "class": "frozen_selected.FrozenSelected",
            "observer_inherited_from": "scheduler.SellScheduler.observe",
            "candidate_class": candidate.INSTALLED_CLASS.__name__,
            "runtime_marker": candidate.INSTALLED_CLASS._titan_rival_decay_decontamination,
        },
        "official_engine_transition": {
            "engine_ref": "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c",
            "transitions": transitions,
            "control_observed_harvests": control.observed_harvests,
            "candidate_observed_harvests": patched.observed_harvests,
            "visible_final_yield": farm["tiles"][0][0]["yield_units"],
            "control_rival_supply": current_supply,
            "candidate_rival_supply": patched_supply,
        },
        "optimizer_predecessor_witness": {
            "item": "MELON",
            "inventory": 80,
            "quantity": 2,
            "now": 100,
            "dates": [100, 104, 108],
            "control_plan": [list(row) for row in current_plan],
            "candidate_plan": [list(row) for row in patched_plan],
            "control_worst_relative_gain": current_info["worst_relative_gain"],
            "candidate_worst_relative_gain": patched_info["worst_relative_gain"],
            "candidate_scenarios": patched_info["scenarios"],
        },
        "truth_boundary": (
            "This proves the transition, executable seam and predecessor decision. "
            "It is not a full opponent panel, leaderboard claim, production enablement "
            "or Kaggle submission authorization."
        ),
    }


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("WITNESS.json")
    payload = run()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "control_supply": payload["official_engine_transition"]["control_rival_supply"],
        "candidate_supply": payload["official_engine_transition"]["candidate_rival_supply"],
        "control_plan": payload["optimizer_predecessor_witness"]["control_plan"],
        "candidate_plan": payload["optimizer_predecessor_witness"]["candidate_plan"],
        "gain": payload["optimizer_predecessor_witness"]["candidate_worst_relative_gain"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
