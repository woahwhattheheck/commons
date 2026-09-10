# SPDX-License-Identifier: Apache-2.0
"""Emit the source-bound, legally reachable rival-harvest witness."""
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
PULSE = LAB.parent / "cloud-runtime-pulse"
for root in (PULSE, LAB, HERE):
    text = str(root.resolve(strict=True))
    while text in sys.path:
        sys.path.remove(text)
    sys.path.insert(0, text)

from decay_observer import OPERATION, REACHABILITY_OPERATION
from legal_trace import run_legal_drought_trace
import candidate
import scheduler

if Path(candidate.__file__).resolve() != (HERE / "candidate.py").resolve(strict=True):
    raise RuntimeError(f"wrong evidence candidate imported: {candidate.__file__}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_engine():
    package = types.ModuleType("kaggle_environments")
    utils = types.ModuleType("kaggle_environments.utils")
    utils.resolve_episode_seed = lambda env: 0
    old_package = sys.modules.get("kaggle_environments")
    old_utils = sys.modules.get("kaggle_environments.utils")
    sys.modules["kaggle_environments"] = package
    sys.modules["kaggle_environments.utils"] = utils
    path = LAB / "reference/engine/kaggriculture.py"
    spec = importlib.util.spec_from_file_location("_reachable_harvest_engine", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if old_package is None:
        sys.modules.pop("kaggle_environments", None)
    else:
        sys.modules["kaggle_environments"] = old_package
    if old_utils is None:
        sys.modules.pop("kaggle_environments.utils", None)
    else:
        sys.modules["kaggle_environments.utils"] = old_utils
    return module


def dates_for(obs: dict[str, Any], config: dict[str, Any]) -> tuple[int, ...]:
    now = int(obs["step"])
    last = int(config.get("episodeSteps", 720)) - 2
    end = min(now + scheduler.HORIZON, last, (now // 24 + 1) * 24 - 1)
    for checkpoint, *_ in scheduler.parent.DECISIONS:
        if now < checkpoint <= end:
            end = checkpoint - 1
    shops = obs.get("town", {}).get("unlocked_shops", [])
    dates = [now] + [
        step
        for step in range(now + 1, end + 1)
        if any(scheduler.absorption(product, step - 1, shops, config) for product in scheduler.PRODUCTS)
    ]
    if len(dates) > 3:
        dates = dates[:2] + dates[-1:]
    if dates[-1] != end:
        dates.append(end)
    return tuple(sorted(set(dates)))


def sold(action: dict[str, Any], item: str) -> int:
    return sum(
        max(0, int(order[2]))
        for order in action.get("market", [])
        if order and len(order) > 2 and order[0] == "SELL" and order[1] == item
    )


def observe(cls: type, predecessor: dict[str, Any], current: dict[str, Any]):
    value = cls()
    value.previous = copy.deepcopy(predecessor)
    value.observe(copy.deepcopy(current))
    return value


def run() -> dict[str, Any]:
    trace = run_legal_drought_trace(load_engine())
    predecessor = trace["predecessor"]
    current = trace["current"]
    config = trace["configuration"]

    control_observer = observe(scheduler.SellScheduler, predecessor, current)
    patched_observer = observe(candidate.INSTALLED_CLASS, predecessor, current)
    control_supply = control_observer.rival_supply(current, "CARROT")
    patched_supply = patched_observer.rival_supply(current, "CARROT")
    assert control_observer.observed_harvests == {"CARROT": [(96, 1)]}
    assert patched_observer.observed_harvests == {}
    assert (control_supply, patched_supply) == (1, 0)

    quantity = current["private"]["shed"]["CARROT"]
    inventory = current["market"]["inventory"]["CARROT"]
    shops = current["town"]["unlocked_shops"]
    dates = dates_for(current, config)
    assert (quantity, inventory, shops, dates) == (6, 9996, [], (96, 97, 104))
    common = dict(
        item="CARROT", quantity=quantity, inventory=inventory,
        params=current["market"].get("params", {}).get("CARROT"), shops=shops,
        config=config, now=96, dates=dates, reference=((96, 6),), minimum_now=0,
        capacity_ok=lambda _plan: True, last=config["episodeSteps"] - 2,
    )
    control_plan, control_info = scheduler.optimize_lot(rival_quantity=1, **common)
    patched_plan, patched_info = scheduler.optimize_lot(rival_quantity=0, **common)
    assert control_plan == ((96, 6),) and control_info["worst_relative_gain"] == 0.0
    assert patched_plan == ((96, 5),) and patched_info["worst_relative_gain"] == 1.0

    control = scheduler.SellScheduler()
    patched = candidate.INSTALLED_CLASS()
    control.previous = copy.deepcopy(predecessor)
    patched.previous = copy.deepcopy(predecessor)
    control_action = control.act(copy.deepcopy(current), copy.deepcopy(config))
    patched_action = patched.act(copy.deepcopy(current), copy.deepcopy(config))
    assert sold(control_action, "CARROT") == 6
    assert sold(patched_action, "CARROT") == 5
    assert control_action != patched_action

    action_bytes = json.dumps(trace["actions"], sort_keys=True, separators=(",", ":")).encode()
    lane_names = (
        "candidate.py", "decay_observer.py", "legal_trace.py", "test_candidate.py",
        "test_decay_observer.py", "test_actor_reachability.py", "witness.py",
    )
    return {
        "schema": 3,
        "operations": [OPERATION, REACHABILITY_OPERATION],
        "source_commit": candidate.SOURCE_COMMIT,
        "source_git_blobs": candidate.verify_source(),
        "lane_sha256": {name: sha256(HERE / name) for name in lane_names},
        "candidate_import": str(Path(candidate.__file__).resolve()),
        "official_engine_ref": "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c",
        "legal_trace": {
            "action_count": len(trace["actions"]),
            "action_tape_sha256": hashlib.sha256(action_bytes).hexdigest(),
            "key_actions": trace["key_actions"],
            "derived": trace["derived"],
        },
        "observer": {
            "control_ledger": control_observer.observed_harvests,
            "candidate_ledger": patched_observer.observed_harvests,
            "control_supply": control_supply,
            "candidate_supply": patched_supply,
        },
        "optimizer": {
            "dates": list(dates),
            "control_plan": [list(row) for row in control_plan],
            "candidate_plan": [list(row) for row in patched_plan],
            "control_gain": control_info["worst_relative_gain"],
            "candidate_gain": patched_info["worst_relative_gain"],
        },
        "caller": {
            "control_action": control_action,
            "candidate_action": patched_action,
            "control_carrot_sold": sold(control_action, "CARROT"),
            "candidate_carrot_sold": sold(patched_action, "CARROT"),
        },
        "review_receipts": {
            "p0_review_id": 4918187132,
            "p0_comment_id": 2394919203,
            "peer_assist_slack_ts": "1789077848.040539",
        },
        "truth_boundary": (
            "Full official initialization and 96 legal two-player turns prove one reachable "
            "predecessor, observer delta, direct optimizer delta, and returned-action delta. "
            "This is not a full-game panel, promotion, leaderboard, or Kaggle claim."
        ),
    }


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("WITNESS.json")
    payload = run()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "trace_actions": payload["legal_trace"]["action_count"],
        "observer_supply": [payload["observer"]["control_supply"], payload["observer"]["candidate_supply"]],
        "caller_sold": [payload["caller"]["control_carrot_sold"], payload["caller"]["candidate_carrot_sold"]],
        "gain": payload["optimizer"]["candidate_gain"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
