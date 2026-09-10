# SPDX-License-Identifier: Apache-2.0
"""Build a reachable predecessor by driving the pinned official interpreter.

Player 0 legally grows, fertilizes, harvests, and sheds six CARROT units.
Player 1 legally grows one CARROT, moves off it, and omits water for two
whole days. The day-3 refresh turns that unoccupied crop into WEED between
public steps 95 and 96.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping


class AttrDict(dict):
    """Mapping with attribute access, matching Kaggle's runtime objects."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def configuration() -> AttrDict:
    return AttrDict(
        episodeSteps=720,
        boardSize=10,
        startingMoney=3000,
        turnsPerDay=24,
        shedCapacity=100,
        maxMarketOrdersPerTurn=10,
        farmHandCostMult=1.0,
        weedSpawnChance=0.0,
        townShopUnlockInterval=1000,
        townShopSellInterval=4,
        townCenterSellInterval=24,
    )


def _agent() -> AttrDict:
    return AttrDict(
        observation=AttrDict(step=0),
        action={},
        reward=0.0,
        status="ACTIVE",
    )


def _action(
    farmer: list[Any] | None = None,
    *,
    market: list[list[Any]] | None = None,
) -> dict[str, Any]:
    return {
        "farmer": list(farmer or ["PASS"]),
        "hands": [],
        "market": copy.deepcopy(market or []),
    }


def _scheduled_action(player: int, step: int) -> dict[str, Any]:
    if player == 0:
        market = []
        if step == 0:
            market = [
                ["BUY_SEED", "CARROT", 2],
                ["BUY_PRODUCT", "FERTILIZER", 2],
            ]
        farmer = {
            1: ["PLANT", "CARROT"],
            2: ["WATER"],
            3: ["WEST"],
            4: ["PLANT", "CARROT"],
            5: ["WATER"],
            24: ["WATER"],
            25: ["WEST"],
            26: ["WATER"],
            48: ["PICKUP", "FERTILIZER", 2],
            49: ["FERTILIZE"],
            50: ["WATER"],
            51: ["WEST"],
            52: ["FERTILIZE"],
            53: ["WATER"],
            72: ["HARVEST"],
            73: ["WEST"],
            74: ["HARVEST"],
            75: ["EAST"],
            76: ["DROP"],
        }.get(step, ["PASS"])
        return _action(farmer, market=market)

    market = [["BUY_SEED", "CARROT", 1]] if step == 0 else []
    farmer = {
        1: ["PLANT", "CARROT"],
        2: ["WATER"],
        24: ["WATER"],
        # Daily refresh returns the farmer to [4,4]; move off the crop on
        # both drought days so the predecessor proves no harvest custody.
        48: ["EAST"],
        72: ["EAST"],
    }.get(step, ["PASS"])
    return _action(farmer, market=market)


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return copy.deepcopy(value)


def public_observation(
    state: list[AttrDict],
    player: int,
    step: int,
) -> dict[str, Any]:
    observation = state[player].observation
    return _plain(
        {
            "step": step,
            "player": player,
            "day": step // 24,
            "hour": step % 24,
            "farms": observation.farms,
            "market": observation.market,
            "town": observation.town,
            "private": observation.private,
        }
    )


def _tile(obs: Mapping[str, Any], player: int, x: int, y: int) -> Any:
    return obs["farms"][player]["tiles"][y][x]


def run_legal_drought_trace(engine: Any) -> dict[str, Any]:
    """Run official initialization and 96 legal two-player turns."""
    config = configuration()
    env = AttrDict(configuration=config, info={"seed": 0}, done=False)
    state = [_agent(), _agent()]

    # First call invokes the engine's own initializer and consumes no action.
    engine.interpreter(state, env)
    actions: list[dict[str, Any]] = []
    snapshots: dict[int, dict[str, Any]] = {
        0: public_observation(state, 0, 0),
    }

    for step in range(96):
        for player in (0, 1):
            state[player].observation.step = step
            state[player].action = _scheduled_action(player, step)
        actions.append(
            {
                "step": step,
                "player_0": copy.deepcopy(state[0].action),
                "player_1": copy.deepcopy(state[1].action),
            }
        )
        engine.interpreter(state, env)
        snapshots[step + 1] = public_observation(state, 0, step + 1)

    predecessor = snapshots[95]
    current = snapshots[96]
    rival_before = _tile(predecessor, 1, 4, 4)
    rival_after = _tile(current, 1, 4, 4)

    # All score-facing consumers fail before use unless the predecessor is
    # actually reachable and has the exact public lifecycle/custody facts.
    assert rival_before["kind"] == "PLANT"
    assert rival_before["crop"] == "CARROT"
    assert rival_before["yield_units"] == 1
    assert rival_before["watered_today"] is False
    assert rival_before["consecutive_unwatered"] == 1
    assert rival_before["max_lifespan_step"] == 96
    assert predecessor["farms"][1]["farmer"] == [5, 4]
    assert predecessor["farms"][1]["hands"] == []
    assert rival_after == {"kind": "WEED"}

    own_private = current["private"]
    assert own_private["shed"].get("CARROT", 0) == 6
    assert all(not inventory for inventory in own_private["inventories"])
    assert current["market"]["inventory"]["CARROT"] == 9996
    assert current["town"]["unlocked_shops"] == []
    assert _tile(current, 0, 4, 4) is None
    assert _tile(current, 0, 3, 4) is None

    return {
        "configuration": _plain(config),
        "predecessor": predecessor,
        "current": current,
        "actions": actions,
        "key_actions": [
            row
            for row in actions
            if row["step"]
            in {0, 1, 2, 3, 4, 5, 24, 25, 26, 48, 49, 50, 51, 52, 53, 72, 73, 74, 75, 76, 95}
        ],
        "derived": {
            "step": current["step"],
            "own_carrot_shed": own_private["shed"]["CARROT"],
            "market_carrot_inventory": current["market"]["inventory"]["CARROT"],
            "unlocked_shops": current["town"]["unlocked_shops"],
            "rival_coordinate": [4, 4],
            "rival_predecessor_actor_positions": {
                "farmer": predecessor["farms"][1]["farmer"],
                "hands": predecessor["farms"][1]["hands"],
            },
            "rival_before": rival_before,
            "rival_after": rival_after,
        },
    }
