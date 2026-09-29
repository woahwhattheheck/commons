from __future__ import annotations

import copy
import gzip
import json
import tempfile
from unittest import mock
from pathlib import Path



def _farm(hand_count: int) -> dict:
    return {"hands": [{} for _ in range(hand_count)], "money": 100}


def _record(
    seat: int,
    own_hand_count: int,
    action_hands: list,
    *,
    other_hand_count: int = 0,
    day: int = 5,
    hour: int = 0,
    market: list | None = None,
    player: object | None = None,
) -> dict:
    farms = [_farm(other_hand_count), _farm(other_hand_count)]
    farms[seat] = _farm(own_hand_count)
    return {
        "action": {
            "farmer": ["PASS"],
            "hands": action_hands,
            "market": [] if market is None else market,
        },
        "info": {},
        "observation": {
            "day": day,
            "hour": hour,
            "player": seat if player is None else player,
            "farms": farms,
        },
        "reward": 0,
        "status": "ACTIVE",
    }


def _replay(
    own_counts: list[int],
    actions: list[list],
    *,
    seat: int = 1,
    markets: list[list] | None = None,
    episode_id: int = 7001,
    agent_name: str = "Bryce Muhlnickel",
) -> dict:
    if len(own_counts) != len(actions):
        raise ValueError("own_counts/actions length mismatch")
    markets = markets or [[] for _ in actions]
    steps = []
    for index, (count, hand_rows, market_rows) in enumerate(
        zip(own_counts, actions, markets)
    ):
        records = [
            _record(0, 0, [], day=index // 24, hour=index % 24),
            _record(1, 0, [], day=index // 24, hour=index % 24),
        ]
        records[seat] = _record(
            seat,
            count,
            hand_rows,
            day=index // 24,
            hour=index % 24,
            market=market_rows,
        )
        steps.append(records)
    return {
        "name": "kaggriculture",
        "module_version": "1.32.7",
        "info": {
            "EpisodeId": episode_id,
            "seed": 123456,
            "Agents": [{"Name": "Opponent"}, {"Name": "Opponent"}],
        },
        "steps": steps,
    } | {
        "info": {
            "EpisodeId": episode_id,
            "seed": 123456,
            "Agents": [
                {"Name": agent_name if seat == 0 else "Opponent"},
                {"Name": agent_name if seat == 1 else "Opponent"},
            ],
        }
    }


