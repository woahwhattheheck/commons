"""Deterministic source census for TITAN V3.1 M1 plan-aware product-mix audit.

Reads only the exact authored R04 tapes and SHOP_PLANS mapping.  It does not execute a game,
modify a policy, or infer hidden rival state.  The purpose is to answer whether shop-plan
conditioning already produces materially distinct post-route production / sale programs.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
OVERLAY = V3 / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as r04  # noqa: E402

ROUTE_START = r04.ROUTE_STEP
ROUTE_END = r04.FINAL_PLAN_STEP  # exclusive; plan 2 is forced from this step onward


def qty(command, index=2):
    return max(0, int(command[index])) if len(command) > index else 1


def commands(action):
    return [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]


def route_signature(tape):
    market_sell = Counter()
    market_buy_seed = Counter()
    market_buy_animal = Counter()
    market_buy_product = Counter()
    worker_plant = Counter()
    worker_pickup = Counter()
    worker_place = Counter()
    worker_ops = Counter()
    market_ops = Counter()

    encoded = []
    for step in range(ROUTE_START, ROUTE_END):
        action = tape[step]
        encoded.append(json.dumps(action, sort_keys=True, separators=(",", ":")))
        for order in action.get("market") or []:
            if not order:
                continue
            op = order[0]
            market_ops[op] += 1
            if op == "SELL" and len(order) >= 3:
                market_sell[order[1]] += max(0, int(order[2]))
            elif op == "BUY_SEED" and len(order) >= 3:
                market_buy_seed[order[1]] += max(0, int(order[2]))
            elif op == "BUY_ANIMAL" and len(order) >= 3:
                market_buy_animal[order[1]] += max(0, int(order[2]))
            elif op == "BUY_PRODUCT" and len(order) >= 3:
                market_buy_product[order[1]] += max(0, int(order[2]))
        for command in commands(action):
            if not command:
                continue
            op = command[0]
            worker_ops[op] += 1
            if op == "PLANT" and len(command) >= 2:
                worker_plant[command[1]] += 1
            elif op == "PICKUP" and len(command) >= 2:
                worker_pickup[command[1]] += qty(command)
            elif op == "PLACE" and len(command) >= 2:
                worker_place[command[1]] += qty(command)

    digest = hashlib.sha256("\n".join(encoded).encode()).hexdigest()
    return {
        "route_sha256": digest,
        "market_sell_qty": dict(sorted(market_sell.items())),
        "market_buy_seed_qty": dict(sorted(market_buy_seed.items())),
        "market_buy_animal_qty": dict(sorted(market_buy_animal.items())),
        "market_buy_product_qty": dict(sorted(market_buy_product.items())),
        "worker_plant_count": dict(sorted(worker_plant.items())),
        "worker_pickup_qty": dict(sorted(worker_pickup.items())),
        "worker_place_qty": dict(sorted(worker_place.items())),
        "worker_ops": dict(sorted(worker_ops.items())),
        "market_ops": dict(sorted(market_ops.items())),
    }


def main():
    tapes = r04._INLINE_TAPES
    assert len(tapes) == 13
    assert all(len(tape) == r04.LAST_STEP + 1 for tape in tapes)
    assert ROUTE_START == 144 and ROUTE_END == 648

    signatures = [route_signature(tape) for tape in tapes]
    base = tapes[0]
    changed_vs_plan0 = {}
    for plan, tape in enumerate(tapes):
        changed_vs_plan0[str(plan)] = sum(
            tape[step] != base[step] for step in range(ROUTE_START, ROUTE_END)
        )

    route_hashes = [sig["route_sha256"] for sig in signatures]
    hash_groups = {}
    for plan, digest in enumerate(route_hashes):
        hash_groups.setdefault(digest, []).append(plan)

    shop_plan_pairs = {}
    for shops, plan in sorted(r04.SHOP_PLANS.items()):
        shop_plan_pairs["|".join(shops)] = plan

    result = {
        "source": "r04_full_router._INLINE_TAPES + SHOP_PLANS",
        "route_phase": [ROUTE_START, ROUTE_END - 1],
        "plans": {str(i): signatures[i] for i in range(len(signatures))},
        "changed_steps_vs_plan0": changed_vs_plan0,
        "unique_route_hashes": len(hash_groups),
        "identical_route_groups": [plans for plans in hash_groups.values() if len(plans) > 1],
        "shop_plan_pairs": shop_plan_pairs,
        "shop_plan_usage_counts": dict(sorted(Counter(r04.SHOP_PLANS.values()).items())),
    }
    print("M1_AUDIT_JSON=" + json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
