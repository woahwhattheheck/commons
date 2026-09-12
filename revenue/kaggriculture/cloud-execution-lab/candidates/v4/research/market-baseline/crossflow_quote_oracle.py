#!/usr/bin/env python3
"""Exact-engine oracle for opposite-side market lockstep (BUY_PRODUCT vs SELL).

Research-only.  This module proves quote/commit mechanics for already-required
WHEAT/FERTILIZER flows.  It does not predict rival orders or authorize retiming.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
BUYABLE = ("WHEAT", "FERTILIZER")
CONFIG = {
    "boardSize": 10,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
    "farmHandCostMult": 1,
}
STARTING_MONEY = 1_000_000


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_engine(path: str | Path):
    path = Path(path)
    data = path.read_bytes()
    actual = git_blob(data)
    if actual != ENGINE_BLOB:
        raise ValueError(f"engine Git blob mismatch: {actual}")
    try:
        import kaggle_environments.utils  # noqa: F401
    except ModuleNotFoundError:
        pkg = sys.modules.setdefault("kaggle_environments", types.ModuleType("kaggle_environments"))
        util = types.ModuleType("kaggle_environments.utils")
        util.resolve_episode_seed = lambda env: int(getattr(env, "info", {}).get("seed", 0))
        pkg.utils = util
        sys.modules["kaggle_environments.utils"] = util
    spec = importlib.util.spec_from_file_location("titan_crossflow_engine", path)
    if spec is None or spec.loader is None:
        raise ValueError("could not load engine module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    required = ("_new_farm", "_new_private", "_new_market", "_process_market", "market_price")
    missing = [name for name in required if not hasattr(mod, name)]
    if missing:
        raise ValueError(f"engine missing symbols: {missing}")
    return mod


def _plain_qty(value: Any, name: str, *, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be a plain int >= {minimum}")
    if value > CONFIG["shedCapacity"]:
        raise ValueError(f"{name} exceeds default physical shed capacity {CONFIG['shedCapacity']}")
    return value


def _plain_inventory(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError&¢inventory must be a plain nonnegative int")
    return value


def _world(engine, *, item: str, inventory: int):
    if item not in BUYABLE:
        raise ValueError(f"item must be one of {BUYABLE}")
    inventory = _plain_inventory(inventory)
    farms = [engine._new_farm(CONFIG["boardSize"], STARTING_MONEY) for _ in range(2)]
    privates = [engine._new_private() for _ in range(2)]
    market = engine._new_market()
    market["inventory"][item] = inventory
    states = []
    for player in range(2):
        obs = SimpleNamespace(player=player, farms=farms, private=privates[player], market=market)
        states.append(SimpleNamespace(observation=obs, action={}))
    env = SimpleNamespace(configuration=dict(CONFIG), info={"seed": 0})
    return states, env


def _market_call(engine, states, env, p0_orders: list, p1_orders: list) -> None:
    states[0].action = {"farmer": ["PASS"], "hands": [], "market": p0_orders}
    states[1].action = {"farmer": ["PASS"], "hands": [], "market": p1_orders}
    engine._process_market(states, env)


def _buy(item: str, quantity: int) -> list:
    return ["BUY_PRODUCT", item, quantity]


def _sell(item: str, quantity: int) -> list:
    return ["SELL", item, quantity]


def _row1(order: list) -> list[list]:
    # Zero quantity is rejected by _parse_order and is therefore an inert raw row.
    return [["SELL", "WHEAT", 0], order]


def _money_delta(states, player: int) -> int:
    farm = states[0].observation.farms[player]
    return int(round(farm["money"] - STARTING_MONEY))


def buyer_waits_for_rival_supply(
    engine,
    *,
    item: str,
    quantity: int,
    inventory: int = 10_000,
    delayed: bool,
) -> dict[str, Any]:
    """Player1 BUYs while player0 SELLs the same item.

    delayed=False aligns both orders at raw market row 0.  delayed=True moves
    the BUY to row 1, after the rival's entire row-0 SELL has completed.
    """
    if item not in BUYABLE:
        raise ValueError(f"item must be one of {BUYABLE}")
    quantity = _plain_qty(quantity, "quantity")
    states, env = _world(engine, item=item, inventory=inventory)
    states[0].observation.private["shed"][item] = quantity
    p0 = [_sell(item, quantity)]
    buy = _buy(item, quantity)
    p1 = _row1(buy) if delayed else [buy]
    before = int(states[0].observation.market["inventory"][item])
    _market_call(engine, states, env, p0, p1)
    return {
        "delayed": bool(delayed),
        "buyer_cost": -_money_delta(states, 1),
        "rival_sell_revenue": _money_delta(states, 0),
        "market_inventory_before": before,
        "market_inventory_after": int(states[0].observation.market["inventory"][item]),
        "buyer_shed": int(states[1].observation.private["shed"].get(item, 0)),
        "rival_shed": int(states[0].observation.private["shed"].get(item, 0)),
    }


def seller_waits_for_rival_demand(
    engine,
    *,
    item: str,
    quantity: int,
    inventory: int = 10_000,
    delayed: bool,
) -> dict[str, Any]:
    """Player1 SELLs while player0 BUYs the same item.

    delayed=False aligns both orders at raw market row 0.  delayed=True moves
    the SELL to row 1, after the rival's entire row-0 BUY has completed.
    """
    if item not in BUYABLE:
        raise ValueError(f"item must be one of {BUYABLE}")
    quantity = _plain_qty(quantity, "quantity")
    states, env = _world(engine, item=item, inventory=inventory)
    states[1].observation.private["shed"][item] = quantity
    p0 = [_buy(item, quantity)]
    sell = _sell(item, quantity)
    p1 = _row1(sell) if delayed else [sell]
    before = int(states[0].observation.market["inventory"][item])
    _market_call(engine, states, env, p0, p1)
    return {
        "delayed": bool(delayed),
        "seller_revenue": _money_delta(states, 1),
        "rival_buy_cost": -_money_delta(states, 0),
        "market_inventory_before": before,
        "market_inventory_after": int(states[0].observation.market["inventory"][item]),
        "seller_shed": int(states[1].observation.private["shed"].get(item, 0)),
        "rival_shed": int(states[0].observation.private["shed"].get(item, 0)),
    }


def compare(engine, *, item: str, quantity: int = 100, inventory: int = 10_000) -> dict[str, Any]:
    """Compare aligned cross-flow against waiting one raw market row.

    The clean quote theorem is reported only when aligned and delayed worlds end
    at the same public inventory.  At PRICE_FLOOR, SELL intentionally stops
    returning units to public inventory, so timing can change terminal inventory;
    those cases are surfaced as a separate floor boundary rather than laundered
    into a cost/revenue theorem.
    """
    if item not in BUYABLE:
        raise ValueError(f"item must be one of {BUYABLE}")
    quantity = _plain_qty(quantity, "quantity")
    inventory = _plain_inventory(inventory)
    b_aligned = buyer_waits_for_rival_supply(
        engine, item=item, quantity=quantity, inventory=inventory, delayed=False
    )
    b_delayed = buyer_waits_for_rival_supply(
        engine, item=item, quantity=quantity, inventory=inventory, delayed=True
    )
    s_aligned = seller_waits_for_rival_demand(
        engine, item=item, quantity=quantity, inventory=inventory, delayed=False
    )
    s_delayed = seller_waits_for_rival_demand(
        engine, item=item, quantity=quantity, inventory=inventory, delayed=True
    )
    buyer_same_terminal = b_aligned["market_inventory_after"] == b_delayed["market_inventory_after"]
    seller_same_terminal = s_aligned["market_inventory_after"] == s_delayed["market_inventory_after"]
    clean = buyer_same_terminal and seller_same_terminal
    price_here = int(engine.market_price(item, inventory))
    out = {
        "kind": "titan-v4-crossflow-quote-oracle",
        "engine_git_blob": ENGINE_BLOB,
        "item": item,
        "quantity": quantity,
        "inventory": inventory,
        "price_at_inventory": price_here,
        "clean_same-terminal-quote-theorem": clean,
        "buyer": {
            "aligned_cost": b_aligned["buyer_cost"],
            "delayed_cost": b_delayed["buyer_cost"],
            "saving_by_waiting_for_supply": b_aligned["buyer_cost"] - b_delayed["buyer_cost"],
            "same_terminal_inventory": buyer_same_terminal,
            "aligned_terminal_inventory": b_aligned["market_inventory_after"],
            "delayed_terminal_inventory": b_delayed["market_inventory_after"],
        },
        "seller": {
            "aligned_revenue": s_aligned["seller_revenue"],
            "delayed_revenue": s_delayed["seller_revenue"],
            "gain_by_waiting_for_demand": s_delayed["seller_revenue"] - s_aligned["seller_revenue"],
            "same_terminal_inventory": seller_same_terminal,
            "aligned_terminal_inventory": s_aligned["market_inventory_after"],
            "delayed_terminal_inventory": s_delayed["market_inventory_after"],
        },
        "limits": [
            "mechanics/current-cash witness only; not rival-order prediction or field EV",
            "BUY_PRODUCT cross-flow exists only for WHEAT/FERTILIZER",
            "retiming requires an independent raw-row opportunity/cap/safety theorem",
            "PRICE_FLOOR SELL is destructive and can make timing change terminal inventory; clean theorem then refuses",
        ],
    }
    return out


def default_engine_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if parent.name == "cloud-execution-lab":
            return parent / "reference" / "engine" / "kaggriculture.py"
    raise FileNotFoundError("cloud-execution-lab ancestor not present")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", type=Path, default=None)
    ap.add_argument("--item", choices=BUYABLE, default="WHEAT")
    ap.add_argument("--quantity", type=int, default=100)
    ap.add_argument("--inventory", type=int, default=10_000)
    ns = ap.parse_args(argv)
    engine_path = ns.engine if ns.engine is not None else default_engine_path()
    engine = load_engine(engine_path)
    print(json.dumps(compare(engine, item=ns.item, quantity=ns.quantity, inventory=ns.inventory),
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
