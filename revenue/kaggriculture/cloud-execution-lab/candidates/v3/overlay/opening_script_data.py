# SPDX-License-Identifier: Apache-2.0
"""Constants and exact-step market tapes for the T03 opening lane."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

LAST_OPENING_STEP = 47
MAX_MARKET_ORDERS = 10

SEED_COSTS = {
    "WHEAT": 10,
    "CARROT": 15,
    "TOMATO": 25,
    "STRAWBERRY": 40,
    "MELON": 80,
}
ANIMAL_COSTS = {"GOOSE": 100, "COW": 300, "SHEEP": 400}
LAND_COSTS = (1000, 2000, 4000)

# Planting remains canonical: these tapes replace only the market queue.
# The legacy variants are negative/audit fixtures whose source arithmetic is checked.
SCRIPTS: dict[str, dict[int, list[list[Any]]]] = {
    "balanced": {
        0: [
            ["BUY_SEED", "STRAWBERRY", 8],
            ["BUY_SEED", "WHEAT", 8],
            ["HIRE"],
            ["HIRE"],
        ],
    },
    "liquid": {
        0: [
            ["BUY_SEED", "WHEAT", 16],
            ["HIRE"],
            ["HIRE"],
            ["HIRE"],
            ["HIRE"],
        ],
    },
    "gemini_legacy": {
        0: [
            ["BUY_SEED", "STRAWBERRY", 10],
            ["BUY_SEED", "MELON", 6],
            ["HIRE"],
            ["HIRE"],
        ],
    },
    "leader_legacy": {
        1: [
            ["HIRE"],
            ["HIRE"],
            ["HIRE"],
            ["HIRE"],
            ["BUY_ANIMAL", "COW", 2],
            ["BUY_ANIMAL", "SHEEP", 2],
            ["BUY_SEED", "WHEAT", 10],
        ],
    },
}


def scripted_market(variant: str, step: int) -> list[list[Any]] | None:
    """Return a private copy of the tape at exactly ``step``."""
    table = SCRIPTS.get(str(variant))
    if table is None:
        return None
    actions = table.get(int(step))
    return deepcopy(actions) if actions is not None else None
