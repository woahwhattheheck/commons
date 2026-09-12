# SPDX-License-Identifier: Apache-2.0
"""Probe frozen V2 and the materialized successor on an external replay tape.

The tape is observation-grounded rather than a counterfactual environment run:
after the first changed action, later observations still come from the recorded
V2 episode.  The tool therefore proves the policy decision seam and action
emission, not downstream score.  Hosted paired evaluation remains required.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
from typing import Any

import materialize as lane


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def load_scheduler(root: Path, label: str):
    for name in ("mechanics", "intact_arlene", "pinned_receipt_math"):
        sys.modules.pop(name, None)
    sys.path.insert(0, str(root))
    try:
        spec = importlib.util.spec_from_file_location(label, root / "scheduler.py")
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import scheduler from {root}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(root))


def run_arm(root: Path, replay: dict, *, player: int, label: str) -> dict[str, Any]:
    module = load_scheduler(root, f"sol_interstice_probe_{label}")
    scheduler = module.SellScheduler()
    rows = []
    durations = []
    action_digest = hashlib.sha256()
    exact_matches = 0
    market_matches = 0
    compared = 0
    for step, frame in enumerate(replay["steps"][:-1]):
        observation = copy.deepcopy(frame[player]["observation"])
        observation["step"] = step
        observation["player"] = player
        before = {
            "planned": copy.deepcopy(scheduler.planned),
            "pending": copy.deepcopy(scheduler.pending),
        }
        started = time.perf_counter()
        action = scheduler.act(observation, replay["configuration"])
        durations.append(time.perf_counter() - started)
        action_digest.update(canonical(action))
        action_digest.update(b"\n")
        after = {
            "planned": copy.deepcopy(scheduler.planned),
            "pending": copy.deepcopy(scheduler.pending),
        }
        recorded = replay["steps"][step + 1][player].get("action")
        if recorded is not None:
            compared += 1
            exact_matches += int(action == recorded)
            market_matches += int(action.get("market") == recorded.get("market"))
        chosen = copy.deepcopy(scheduler.diagnostics.get("chosen"))
        rows.append(
            {
                "step": step,
                "before": before,
                "after": after,
                "action": action,
                "recorded_next_action": recorded,
                "chosen": chosen,
            }
        )
    return {
        "label": label,
        "scheduler_git_blob_sha1": lane.git_blob_sha1(
            (root / "scheduler.py").read_bytes()
        ),
        "scheduler_sha256": lane.sha256((root / "scheduler.py").read_bytes()),
        "calls": len(rows),
        "action_stream_sha256": action_digest.hexdigest(),
        "mean_call_seconds": statistics.fmean(durations),
        "max_call_seconds": max(durations),
        "recorded_action_matches": exact_matches,
        "recorded_market_matches": market_matches,
        "recorded_actions_compared": compared,
        "rows": rows,
    }


def first_difference(left: list[dict], right: list[dict], field: str) -> int | None:
    for a, b in zip(left, right):
        if a[field] != b[field]:
            return int(a["step"])
    return None


def normalized_state(row: dict) -> dict:
    state=copy.deepcopy(row["after"])
    state["planned"]={
        item: plans for item,plans in state["planned"].items() if plans
    }
    return state


def first_normalized_state_difference(left: list[dict], right: list[dict]) -> int | None:
    for a,b in zip(left,right):
        if normalized_state(a) != normalized_state(b):
            return int(a["step"])
    return None


def compact_row(row: dict) -> dict:
    return {
        "step": row["step"],
        "before": row["before"],
        "after": row["after"],
        "market": row["action"].get("market"),
        "chosen": row["chosen"],
        "recorded_next_market": (
            row["recorded_next_action"].get("market")
            if row["recorded_next_action"] is not None
            else None
        ),
    }


def probe(source: Path, replay_path: Path) -> dict[str, Any]:
    source = source.resolve()
    compressed = replay_path.read_bytes()
    replay = json.loads(gzip.decompress(compressed))
    player = 1
    with tempfile.TemporaryDirectory() as temporary:
        candidate_root = Path(temporary) / "candidate"
        receipt = lane.materialize(source, candidate_root)
        control = run_arm(source, replay, player=player, label="frozen-v2")
        candidate = run_arm(
            candidate_root, replay, player=player, label="partial-future-carry"
        )

    first_raw_state = first_difference(control["rows"], candidate["rows"], "after")
    first_state = first_normalized_state_difference(control["rows"], candidate["rows"])
    first_action = first_difference(control["rows"], candidate["rows"], "action")
    if first_raw_state != 326:
        raise RuntimeError(f"unexpected first raw state divergence: {first_raw_state}")
    if first_state != 639:
        raise RuntimeError(f"unexpected first nonempty-plan divergence: {first_state}")
    if first_action != 645:
        raise RuntimeError(f"unexpected first action divergence: {first_action}")
    c639 = control["rows"][639]
    n639 = candidate["rows"][639]
    c645 = control["rows"][645]
    n645 = candidate["rows"][645]
    c646 = control["rows"][646]
    n646 = candidate["rows"][646]
    if c639["chosen"]["plan"] != [(639, 0), (645, 24)]:
        raise RuntimeError("frozen V2 did not reproduce the 24-unit plan")
    if n639["chosen"]["plan"] != [(639, 0), (645, 14)]:
        raise RuntimeError("candidate did not reproduce the 14-unit plan")
    if c645["action"].get("market") != [["SELL", "STRAWBERRY", 24]]:
        raise RuntimeError("frozen V2 did not emit the 24-unit sale")
    if n645["action"].get("market") != [["SELL", "STRAWBERRY", 14]]:
        raise RuntimeError("candidate did not emit the 14-unit sale")
    if candidate["rows"][646]["action"].get("market"):
        raise RuntimeError("candidate emitted an unexpected immediate repeat sale")

    for arm in (control, candidate):
        arm.pop("rows")
    return {
        "schema_version": 1,
        "operation": lane.OPERATION,
        "interpretation": (
            "Observation-tape policy probe only; downstream score is not causal "
            "after the first changed action."
        ),
        "replay": {
            "path_name": replay_path.name,
            "gzip_sha256": hashlib.sha256(compressed).hexdigest(),
            "episode_id": replay["info"]["EpisodeId"],
            "episode_uuid": replay["id"],
            "seed": replay["info"]["seed"],
            "player": player,
            "candidate_name": replay["info"]["Agents"][player]["Name"],
            "opponent_name": replay["info"]["Agents"][1 - player]["Name"],
            "module_version": replay["module_version"],
        },
        "materialization": {
            "source_closure_sha256": receipt["source"]["closure_sha256"],
            "candidate_closure_sha256": receipt["candidate"]["closure_sha256"],
            "candidate_scheduler_git_blob_sha1": receipt["candidate"][
                "scheduler_git_blob_sha1"
            ],
        },
        "first_raw_state_divergence_step": first_raw_state,
        "raw_state_divergence_reason": (
            "The one-shot lifecycle repair removes a stale empty planned-list; "
            "actions remain identical."
        ),
        "first_nonempty_plan_divergence_step": first_state,
        "first_action_divergence_step": first_action,
        "decision_639": {
            "control": compact_row(c639),
            "candidate": compact_row(n639),
        },
        "emission_645": {
            "control": compact_row(c645),
            "candidate": compact_row(n645),
        },
        "next_step_646": {
            "control": compact_row(c646),
            "candidate": compact_row(n646),
        },
        "arms": {"control": control, "candidate": candidate},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = probe(args.source, args.replay)
    # The candidate row for step 646 is recorded separately here to avoid carrying
    # the full 719-row tapes in the durable report.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "first_nonempty_plan_divergence_step": report[
                    "first_nonempty_plan_divergence_step"
                ],
                "first_action_divergence_step": report[
                    "first_action_divergence_step"
                ],
                "candidate_scheduler": report["materialization"][
                    "candidate_scheduler_git_blob_sha1"
                ],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
