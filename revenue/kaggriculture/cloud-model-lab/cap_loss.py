"""How much production does the route actually lose to the animal output cap?

`_daily_refresh_animals` writes `yield_units = min(max_held, yield + base + bonus)`
(kaggriculture.py 827), so a unit produced on a day the animal is already at its
cap is silently discarded. That is a recurring loss no "the route harvests it
eventually" test can see: the units are gone before any later harvest reaches
them.

This measures it directly by wrapping the engine's own refresh and comparing what
each animal would have accrued against what the cap let it keep. It also records
which tiles lose, and when, so a card set can be aimed at the animals that
actually overflow instead of at whatever happens to be unharvested.
"""

import argparse
import json
import os
from collections import Counter

import cards as cards_mod
import route_cards


def measure(seed, seat, opponent_spec):
    from kaggle_environments.envs.kaggriculture import kaggriculture as K
    A, arl_id = route_cards.load_arlene()
    import arlene_arm
    opp, opp_id = arlene_arm.make_opponent(opponent_spec, A)
    env = cards_mod.make_env(seed)
    env.reset(2)
    me = A.Agent()
    losses = []
    orig = K._daily_refresh_animals

    def refresh(farm, day):
        board = len(farm["tiles"])
        before = {}
        for y in range(board):
            for x in range(board):
                t = farm["tiles"][y][x]
                if isinstance(t, dict) and "animal" in t:
                    before[(x, y)] = (t["animal"], int(t.get("yield_units", 0)),
                                      bool(t.get("fed_today")),
                                      int(t.get("pending_care_bonus", 0) or 0),
                                      int(t.get("placed_day", day)))
        orig(farm, day)
        for (x, y), (an, y0, fed, bonus, placed) in before.items():
            a = K.ANIMALS[an]
            since = (day + 1) - placed - a["first_yield_day"]
            if since < 0 or since % a["interval"] != 0:
                continue                       # not a production day
            base = 1 + (bonus if fed else 0)
            kept = min(a["max_held"], y0 + base)
            lost = (y0 + base) - kept
            if lost > 0:
                losses.append({"day": day, "at": [x, y], "animal": an,
                               "product": a["product"], "yield_before": y0,
                               "max_held": a["max_held"], "would_add": base,
                               "lost": lost})
    K._daily_refresh_animals = refresh
    try:
        while not env.done:
            acts = [None, None]
            for i in range(2):
                obs = env.state[i].observation
                acts[i] = me.act(obs) if i == seat else opp(obs, env.configuration)
            env.step(acts)
    finally:
        K._daily_refresh_animals = orig
    farms = env.state[0].observation.farms
    prices = env.state[0].observation.market["prices"]
    own = float(farms[seat]["money"])
    by_product = Counter()
    for r in losses:
        by_product[r["product"]] += r["lost"]
    value = sum(n * float(prices.get(p, 0)) for p, n in by_product.items())
    return {"seed": seed, "seat": seat, "opponent": opp_id, "arlene": arl_id,
            "own_cash": own, "rival_cash": float(farms[1 - seat]["money"]),
            "units_lost_to_cap": sum(r["lost"] for r in losses),
            "events": len(losses),
            "by_product": dict(by_product),
            "value_at_final_prices": round(value, 1),
            "tiles": Counter(tuple(r["at"]) for r in losses).most_common(6),
            "losses": losses}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--seats", type=int, nargs="+", default=[0])
    ap.add_argument("--opponents", nargs="+", default=["arlene"])
    ap.add_argument("--out", default="results/cap-loss.json")
    a = ap.parse_args()
    rows = []
    for seed in a.seeds:
        for seat in a.seats:
            for opp in a.opponents:
                r = measure(seed, seat, opp)
                rows.append(r)
                print(f"seed {seed} seat {seat} vs {opp:7s}: own {r['own_cash']:9.0f}"
                      f"  units lost to the cap {r['units_lost_to_cap']:4d} over "
                      f"{r['events']} refreshes {dict(r['by_product'])}, worth about "
                      f"{r['value_at_final_prices']:.0f} at final prices", flush=True)
                if r["tiles"]:
                    print(f"    worst tiles: {r['tiles']}", flush=True)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(rows, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
