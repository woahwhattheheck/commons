#!/usr/bin/env python3
"""Extract a minimal, deterministic final-action receipt from a Kaggriculture replay."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


def _money(observation: dict[str, Any], seat: int) -> int:
    return int(observation["farms"][seat]["money"])


def build_receipt(replay_path: Path, *, seat: int, input_index: int) -> dict[str, Any]:
    raw = replay_path.read_bytes()
    with gzip.open(replay_path, "rt", encoding="utf-8") as handle:
        replay = json.load(handle)

    steps = replay["steps"]
    output_index = input_index + 1
    if input_index < 0 or output_index >= len(steps):
        raise ValueError("input_index must have a following produced state")
    if seat < 0 or seat >= len(steps[input_index]):
        raise ValueError("seat is outside the replay actor grid")

    before = steps[input_index][seat]
    after = steps[output_index][seat]
    observation = before["observation"]
    produced_observation = after["observation"]
    action = after["action"]
    if action is None:
        raise ValueError("following state has no produced action")

    unit_actions = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    inventories = observation["private"]["inventories"]
    if len(unit_actions) != len(inventories):
        raise ValueError("unit-action/inventory actor cardinality mismatch")

    drop_indices = [
        index for index, unit_action in enumerate(unit_actions)
        if unit_action and unit_action[0] == "DROP"
    ]
    dropped = Counter()
    for index in drop_indices:
        dropped.update(inventories[index])

    sales = Counter()
    for order in action.get("market") or []:
        if order and order[0] == "SELL" and len(order) >= 3:
            sales[order[1]] += int(order[2])

    return {
        "schema": "titan.v3.l01-final-executable-replay-receipt.v1",
        "episode_id": int(replay["info"]["EpisodeId"]),
        "replay_uuid": replay["id"],
        "source_file": replay_path.name,
        "source_gzip_sha256": hashlib.sha256(raw).hexdigest(),
        "source_gzip_bytes": len(raw),
        "team_names": replay["info"]["TeamNames"],
        "seat": seat,
        "state_count": len(steps),
        "action_count": len(steps) - 1,
        "input_state_index": input_index,
        "input_observation_step": int(observation["step"]),
        "input_day": int(observation["day"]),
        "input_hour": int(observation["hour"]),
        "output_state_index": output_index,
        "output_observation_step": int(produced_observation["step"]),
        "status_before": before["status"],
        "status_after": after["status"],
        "cash_before": _money(observation, seat),
        "cash_after": _money(produced_observation, seat),
        "cash_delta": _money(produced_observation, seat) - _money(observation, seat),
        "final_action": action,
        "actor_inventories_before": inventories,
        "drop_actor_indices": drop_indices,
        "dropped_inventory": dict(sorted(dropped.items())),
        "market_sales": dict(sorted(sales.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("replay", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seat", type=int, default=0)
    parser.add_argument("--input-index", type=int, default=718)
    parser.add_argument("--slack-file-id")
    args = parser.parse_args()

    receipt = build_receipt(args.replay, seat=args.seat, input_index=args.input_index)
    if args.slack_file_id:
        receipt["source_slack_file_id"] = args.slack_file_id
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
