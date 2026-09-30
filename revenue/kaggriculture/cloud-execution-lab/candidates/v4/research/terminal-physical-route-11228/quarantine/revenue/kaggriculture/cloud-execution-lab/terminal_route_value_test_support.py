# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy


class M:
    CROPS = {"WHEAT": {"first_yield_day": 2}, "MELON": {"first_yield_day": 10}}
    ANIMALS = {"COW": {"product": "MILK"}}

    @staticmethod
    def market_price(item, inventory, params=None):
        base = {"WHEAT": 25, "MELON": 250, "MILK": 160}.get(item, 10)
        return max(1, base - max(0, inventory - 10000))


def row(hands=0, market=None):
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in range(hands)],
            "market": [] if market is None else deepcopy(market)}


def plant(crop, planted_day, yield_units, max_lifespan_step=720):
    return {"kind": "PLANT", "crop": crop, "planted_day": planted_day,
            "yield_units": yield_units, "max_lifespan_step": max_lifespan_step}


def observation(step=710, *, farmer=(4, 4), hands=(), shed=None, inventories=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    farm = {"farmer": list(farmer), "hands": [list(p) for p in hands], "money": 1000,
            "hires_today": len(hands), "unlocked_quadrants": ["NW"], "tiles": tiles}
    private = {"shed": {} if shed is None else deepcopy(shed),
               "inventories": ([{} for _ in range(1 + len(hands))]
                               if inventories is None else deepcopy(inventories)),
               "seeds": {}}
    rival = {"farmer": [4, 4], "hands": [], "money": 1000, "hires_today": 0,
             "unlocked_quadrants": ["NW"],
             "tiles": [[None for _ in range(10)] for _ in range(10)]}
    return {"step": step, "player": 0, "farms": [farm, rival], "private": private,
            "market": {"inventory": {"WHEAT": 10000, "MELON": 10000, "MILK": 10000}}}
