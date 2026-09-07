"""Paired panel: exact Arlene versus Arlene + motif overlay, both seats.

Control and candidate differ by the overlay and nothing else -- same seed, same
seat, same opponent, same intact baseline underneath. Own cash and own-minus-rival
margin are tracked separately, because a change can move one without the other and
the competition scores the seat's own cash.

Opponents are the vendored public parents (Apache-2.0, notices and lineage under
../cloud-frontier-policy/next-panel/). No source is reacquired here.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import time

import cards as cards_mod
import arlene_motifs
import route_cards


def _load(path, name="agent"):
    rp = os.path.realpath(path)
    sp = importlib.util.spec_from_file_location(
        os.path.splitext(os.path.basename(rp))[0] + "_arm", rp)
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    sha = hashlib.sha256(open(rp, "rb").read()).hexdigest()
    return mod, {"path": rp, "sha256": sha, "label": f"{os.path.basename(rp)}@{sha[:12]}"}


OPPONENTS = {
    "arlene": None,   # the vendored module itself, a fresh Agent per game
    "apex": "/home/user/work/apex-rt/main.py",
}


def make_opponent(name, A):
    if name == "arlene":
        ag = A.Agent()
        return (lambda obs, cfg: ag.act(obs)), {"label": "arlene (vendored)"}
    mod, ident = _load(OPPONENTS[name])
    fn = mod.agent
    def call(obs, cfg):
        try:
            return fn(obs, cfg)
        except TypeError:
            return fn(obs)
    return call, ident


def game(seed, seat, opponent, table, overlay, A, arl_id):
    env = cards_mod.make_env(seed)
    env.reset(2)
    opp, opp_id = make_opponent(opponent, A)
    me = arlene_motifs.Overlay(A, table) if overlay else A.Agent()
    t0 = time.time()
    n = 0
    while not env.done:
        acts = [None, None]
        for i in range(2):
            obs = env.state[i].observation
            acts[i] = me.act(obs) if i == seat else opp(obs, env.configuration)
        env.step(acts)
        n += 1
    farms = env.state[0].observation.farms
    own = float(farms[seat]["money"])
    rival = float(farms[1 - seat]["money"])
    return {"seed": seed, "seat": seat, "opponent": opponent,
            "opponent_id": opp_id, "arlene": arl_id,
            "arm": "candidate" if overlay else "control",
            "own_cash": own, "rival_cash": rival, "margin": own - rival,
            "rounds": n, "wall_s": round(time.time() - t0, 1),
            "fills": getattr(me, "fills", []),
            "motif_table": {"motifs": len(table.get("motifs", [])),
                            "proposable": sum(1 for m in table.get("motifs", [])
                                              if m.get("proposable")),
                            "authored": table.get("meta", {}).get("authored"),
                            "provenance": table.get("meta", {}).get("provenance")}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--seats", type=int, nargs="+", default=[0, 1])
    ap.add_argument("--opponents", nargs="+", default=["arlene", "apex"])
    ap.add_argument("--motifs", required=True)
    ap.add_argument("--label", default=None)
    ap.add_argument("--out", default="results/arlene-arm.json")
    a = ap.parse_args()
    A, arl_id = route_cards.load_arlene()
    table = json.load(open(a.motifs))
    label = a.label or os.path.basename(a.motifs)
    rows = []
    for seed in a.seeds:
        for seat in a.seats:
            for opp in a.opponents:
                c = game(seed, seat, opp, table, False, A, arl_id)
                d = game(seed, seat, opp, table, True, A, arl_id)
                rows.extend([c, d])
                print(f"seed {seed} seat {seat} vs {opp:7s}  "
                      f"control own {c['own_cash']:9.0f} margin {c['margin']:+9.0f} | "
                      f"candidate own {d['own_cash']:9.0f} margin {d['margin']:+9.0f} | "
                      f"d_own {d['own_cash'] - c['own_cash']:+9.0f} "
                      f"d_margin {d['margin'] - c['margin']:+9.0f} "
                      f"fills {len(d['fills'])}", flush=True)
    def agg(sel):
        c = [r for r in rows if r["arm"] == "control" and sel(r)]
        d = [r for r in rows if r["arm"] == "candidate" and sel(r)]
        if not c:
            return None
        pairs = [(x, y) for x in c for y in d
                 if (x["seed"], x["seat"], x["opponent"]) ==
                 (y["seed"], y["seat"], y["opponent"])]
        return {
            "games": len(pairs),
            "mean_own_control": sum(x["own_cash"] for x, _ in pairs) / len(pairs),
            "mean_own_candidate": sum(y["own_cash"] for _, y in pairs) / len(pairs),
            "mean_d_own": sum(y["own_cash"] - x["own_cash"] for x, y in pairs) / len(pairs),
            "mean_margin_control": sum(x["margin"] for x, _ in pairs) / len(pairs),
            "mean_margin_candidate": sum(y["margin"] for _, y in pairs) / len(pairs),
            "mean_d_margin": sum(y["margin"] - x["margin"] for x, y in pairs) / len(pairs),
            "candidate_wins": sum(1 for _, y in pairs if y["margin"] > 0),
            "candidate_ties": sum(1 for _, y in pairs if y["margin"] == 0),
            "candidate_losses": sum(1 for _, y in pairs if y["margin"] < 0),
            "pairs_own_improved": sum(1 for x, y in pairs if y["own_cash"] > x["own_cash"]),
            "pairs_own_worsened": sum(1 for x, y in pairs if y["own_cash"] < x["own_cash"]),
            "total_fills": sum(len(y["fills"]) for _, y in pairs),
        }
    summary = {"table": label, "overall": agg(lambda r: True),
               "by_opponent": {o: agg(lambda r, o=o: r["opponent"] == o)
                               for o in a.opponents}}
    print("\n=== summary ===")
    print(json.dumps(summary, indent=1, default=str))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump({"summary": summary, "rows": rows}, open(a.out, "w"),
              indent=1, default=str)


if __name__ == "__main__":
    main()
