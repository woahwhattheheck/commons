# SPDX-License-Identifier: Apache-2.0
"""Emit source-bound age-decay, actor-reachability and optimizer witnesses."""
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
# Keep the evidence carrier authoritative over the lab-root compatibility
# module. Running ``python witness.py`` sets HERE on sys.path initially, but a
# blind LAB prepend would shadow this lane's candidate.py with LAB/candidate.py.
for root in (LAB, HERE):
    text = str(root.resolve(strict=True))
    while text in sys.path:
        sys.path.remove(text)
    sys.path.insert(0, text)

from decay_observer import (
    OPERATION,
    REACHABILITY_OPERATION,
    make_decay_safe_frozen_selected,
)
import candidate
import scheduler

if Path(candidate.__file__).resolve() != (HERE / "candidate.py").resolve(strict=True):
    raise RuntimeError(f"wrong evidence candidate imported: {candidate.__file__}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plant(
    units: int,
    *,
    crop: str = "MELON",
    planted_day: int = 0,
    lifespan: int = 100,
) -> dict[str, Any]:
    return {
        "kind": "PLANT",
        "crop": crop,
        "planted_day": planted_day,
        "max_lifespan_step": lifespan,
        "yield_units": units,
        "watered_today": False,
        "consecutive_unwatered": 0,
        "fertilized_until_day": -1,
    }


def empty_farm(size: int = 2) -> dict[str, Any]:
    return {
        "tiles": [[None for _ in range(size)] for _ in range(size)],
        "farmer": [size - 1, size - 1],
        "hands": [],
    }


def observation(step: int, rival_farm: dict[str, Any]) -> dict[str, Any]:
    return {
        "step": step,
        "player": 0,
        "farms": [empty_farm(len(rival_farm["tiles"])), copy.deepcopy(rival_farm)],
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
    spec = importlib.util.spec_from_file_location("_reachability_witness_engine", path)
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


def run_age_decay_witness(engine, patched_class):
    control = bare(scheduler.SellScheduler)
    patched = bare(patched_class)
    farm = {
        "tiles": [[plant(4, crop="CARROT", lifespan=96)]],
        # Keep the actor on the crop so this witness exercises only the parent
        # exact-age discriminator, not the new reachability suppression.
        "farmer": [0, 0],
        "hands": [],
    }
    current = observation(96, farm)
    control.previous = copy.deepcopy(current)
    patched.previous = copy.deepcopy(current)
    transitions = []
    for step in range(96, 101):
        before = copy.deepcopy(farm["tiles"][0][0])
        engine._decay_plants(farm, step)
        after = copy.deepcopy(farm["tiles"][0][0])
        current = observation(step + 1, farm)
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
    control_supply = scheduler.SellScheduler.rival_supply(control, current, "CARROT")
    patched_supply = patched_class.rival_supply(patched, current, "CARROT")
    assert control_supply == 3
    assert patched_supply == 1
    return {
        "product": "CARROT",
        "metadata_valid_lifespan": 96,
        "transitions": transitions,
        "control_observed_harvests": control.observed_harvests,
        "candidate_observed_harvests": patched.observed_harvests,
        "visible_final_yield": farm["tiles"][0][0]["yield_units"],
        "control_rival_supply": control_supply,
        "candidate_rival_supply": patched_supply,
    }


def run_actor_reachability_witness(engine, patched_class):
    control = bare(scheduler.SellScheduler)
    patched = bare(patched_class)
    farm = {
        "tiles": [
            [
                plant(1, crop="CARROT", lifespan=96),
                plant(1, crop="CARROT", lifespan=96),
            ],
            [
                plant(1, crop="CARROT", lifespan=96),
                plant(1, crop="CARROT", planted_day=1, lifespan=120),
            ],
        ],
        # The actor occupies only the surviving visible crop. No unit occupies a
        # declining coordinate, and one action cannot move then harvest.
        "farmer": [1, 1],
        "hands": [],
    }
    current = observation(96, farm)
    control.previous = copy.deepcopy(current)
    patched.previous = copy.deepcopy(current)
    transitions = []
    for step in range(96, 101):
        before_tiles = copy.deepcopy(farm["tiles"])
        engine._decay_plants(farm, step)
        current = observation(step + 1, farm)
        scheduler.SellScheduler.observe(control, copy.deepcopy(current))
        patched_class.observe(patched, copy.deepcopy(current))
        control.previous = copy.deepcopy(current)
        patched.previous = copy.deepcopy(current)
        transitions.append({
            "interpreter_step": step,
            "before_tiles": before_tiles,
            "after_tiles": copy.deepcopy(farm["tiles"]),
        })
    control_supply = scheduler.SellScheduler.rival_supply(control, current, "CARROT")
    patched_supply = patched_class.rival_supply(patched, current, "CARROT")
    assert control.observed_harvests == {
        "CARROT": [(97, 1), (97, 1), (97, 1)]
    }
    assert patched.observed_harvests == {}
    assert control_supply == 3
    assert patched_supply == 1
    return {
        "product": "CARROT",
        "interpreter_steps": [96, 97, 98, 99, 100],
        "predecessor_actor_positions": {
            "farmer": [1, 1],
            "hands": [],
        },
        "declining_crop_coordinates": [[0, 0], [1, 0], [0, 1]],
        "visible_crop_coordinate": [1, 1],
        "final_tiles": current["farms"][1]["tiles"],
        "control_observed_harvests": control.observed_harvests,
        "candidate_observed_harvests": patched.observed_harvests,
        "control_rival_supply": control_supply,
        "candidate_rival_supply": patched_supply,
    }


def run_optimizer_witness(control_supply: int, patched_supply: int):
    # now=101 and replans 105/109 are inside the current-day caller horizon.
    # PET_CAFE consumes two CARROT at steps 104 and 108. Clean stress 1 admits
    # carrying stock across those events; phantom stress 3 rejects that plan.
    common = dict(
        item="CARROT",
        quantity=5,
        inventory=10002,
        params=None,
        shops=["PET_CAFE"],
        config={},
        now=101,
        dates=(101, 105, 109),
        reference=((101, 5),),
        minimum_now=0,
        capacity_ok=lambda _plan: True,
        last=718,
    )
    control_plan, control_info = scheduler.optimize_lot(
        rival_quantity=control_supply, **common
    )
    patched_plan, patched_info = scheduler.optimize_lot(
        rival_quantity=patched_supply, **common
    )
    assert control_supply == 3
    assert patched_supply == 1
    assert control_plan == ((101, 5),)
    assert control_info["worst_relative_gain"] == 0.0
    assert patched_plan == ((101, 0), (105, 1), (109, 4))
    assert patched_info["worst_relative_gain"] == 5.0
    assert [row["relative_value"] - row["reference_relative_value"] for row in patched_info["scenarios"].values()] == [9, 7, 5, 5, 5]
    return {
        "item": "CARROT",
        "inventory": 10002,
        "quantity": 5,
        "now": 101,
        "dates": [101, 105, 109],
        "active_shop": "PET_CAFE",
        "intervening_shop_absorption_steps": [104, 108],
        "control_rival_supply": control_supply,
        "candidate_rival_supply": patched_supply,
        "control_plan": [list(row) for row in control_plan],
        "candidate_plan": [list(row) for row in patched_plan],
        "control_worst_relative_gain": control_info["worst_relative_gain"],
        "candidate_worst_relative_gain": patched_info["worst_relative_gain"],
        "candidate_scenarios": patched_info["scenarios"],
        "peer_assist_slack_ts": "1789077848.040539",
    }


def run() -> dict[str, Any]:
    engine = load_engine()
    patched_class = make_decay_safe_frozen_selected(
        scheduler.SellScheduler,
        products=scheduler.PRODUCTS,
        animals=scheduler.m.ANIMALS,
    )
    age = run_age_decay_witness(engine, patched_class)
    reachability = run_actor_reachability_witness(engine, patched_class)
    optimizer = run_optimizer_witness(
        reachability["control_rival_supply"],
        reachability["candidate_rival_supply"],
    )

    source_sha256 = {
        relative: sha256(LAB / relative)
        for relative in candidate.EXPECTED_GIT_BLOBS
    }
    lane_sha256 = {
        name: sha256(HERE / name)
        for name in (
            "candidate.py",
            "decay_observer.py",
            "test_candidate.py",
            "test_decay_observer.py",
            "test_actor_reachability.py",
            "witness.py",
        )
    }
    return {
        "schema": 2,
        "operations": [OPERATION, REACHABILITY_OPERATION],
        "source_commit": candidate.SOURCE_COMMIT,
        "source_git_blobs": candidate.verify_source(),
        "source_sha256": source_sha256,
        "lane_sha256": lane_sha256,
        "configured_consumer_seam": {
            "class": "frozen_selected.FrozenSelected",
            "observer_inherited_from": "scheduler.SellScheduler.observe",
            "candidate_class": candidate.INSTALLED_CLASS.__name__,
            "decay_marker": (
                candidate.INSTALLED_CLASS._titan_rival_decay_decontamination
            ),
            "actor_reachability_marker": (
                candidate.INSTALLED_CLASS._titan_rival_harvest_actor_reachability
            ),
        },
        "official_engine_ref": "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c",
        "official_engine_age_decay": age,
        "official_engine_actor_reachability": reachability,
        "optimizer_predecessor_witness": optimizer,
        "truth_boundary": (
            "This proves exact public transition classification, executable seam "
            "and one predecessor decision. It is not a full opponent panel, "
            "leaderboard claim, production enablement or Kaggle authorization."
        ),
    }


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("WITNESS.json")
    payload = run()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "age_decay_supply": [
            payload["official_engine_age_decay"]["control_rival_supply"],
            payload["official_engine_age_decay"]["candidate_rival_supply"],
        ],
        "actor_reachability_supply": [
            payload["official_engine_actor_reachability"]["control_rival_supply"],
            payload["official_engine_actor_reachability"]["candidate_rival_supply"],
        ],
        "control_plan": payload["optimizer_predecessor_witness"]["control_plan"],
        "candidate_plan": payload["optimizer_predecessor_witness"]["candidate_plan"],
        "gain": payload["optimizer_predecessor_witness"]["candidate_worst_relative_gain"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
