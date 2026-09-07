"""Paired full-game arm: the same native baseline with and without the motif layer.

Both arms play the same seed against the same opponent with the same baseline
agent. The ONLY difference between them is whether `native_motifs.Proposer` gets
to fill idle worker slots, so the cash and margin difference between the arms is
attributable to the layer and to nothing else.

Every turn the layer changes is recorded exactly -- step, slot, the displaced
baseline op, the accepted op, the motif and its support -- so a cash difference can
be read against the decisions that produced it instead of asserted.
"""

import argparse
import json
import os
import time

import cards as cards_mod
import native_motifs as NM


def load_agent(spec):
    import hashlib
    import importlib.util
    if "::" not in spec:
        return spec, {"kind": "builtin", "spec": spec, "label": spec}
    path, name = spec.split("::", 1)
    rp = os.path.realpath(path)
    sp = importlib.util.spec_from_file_location(
        os.path.splitext(os.path.basename(path))[0] + "_arm", path)
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    sha = hashlib.sha256(open(rp, "rb").read()).hexdigest()
    return getattr(mod, name), {"kind": "file", "spec": spec, "path": rp,
                                "sha256": sha, "function": name,
                                "label": f"{os.path.basename(path)}::{name}@{sha[:12]}"}


def call(agent, obs, config):
    if isinstance(agent, str):
        from kaggle_environments.envs.kaggriculture import kaggriculture as K
        return {"starter": K.starter_agent, "random": K.random_agent,
                "pass": K.pass_agent}[agent](obs)
    try:
        return agent(obs, config)
    except TypeError:
        return agent(obs)


def run(seed, seat, baseline_spec, opponent_spec, table, arm="on", max_steps=None,
        allow_displace_move=False):
    base_ag, base_id = load_agent(baseline_spec)
    opp_ag, opp_id = load_agent(opponent_spec)
    env = cards_mod.make_env(seed)
    env.reset(2)
    prop = NM.Proposer(table, allow_displace_move=allow_displace_move) \
        if arm == "on" else None
    changes, overhead, n_turns, worst = [], 0.0, 0, 0.0
    while not env.done and (max_steps is None or n_turns < max_steps):
        acts = []
        for i in range(2):
            obs = env.state[i].observation
            cfg = env.configuration
            if i == seat:
                a = call(base_ag, obs, cfg)
                if prop is not None:
                    t0 = time.perf_counter()
                    a2, notes = prop.propose(obs, dict(cfg), seat, a)
                    dt = time.perf_counter() - t0
                    overhead += dt
                    worst = max(worst, dt)
                    if a2 != a:
                        for n in notes:
                            if "accepted" in n:
                                changes.append({
                                    "step": int(obs.get("step", 0)),
                                    "day": int(obs["day"]), "hour": int(obs["hour"]),
                                    "slot": n["slot"], "displaced": n["displaced"],
                                    "accepted": n["accepted"], "motif": n["motif"],
                                    "effect": n["effect"], "support": n["support"]})
                        a = a2
                acts.append(a)
            else:
                acts.append(call(opp_ag, obs, cfg))
        env.step(acts)
        n_turns += 1
    final = env.state[0].observation.farms
    money = float(final[seat]["money"])
    opp = float(final[1 - seat]["money"])
    return {"seed": seed, "seat": seat, "arm": arm, "turns": n_turns,
            "baseline": base_id, "opponent": opp_id,
            "motif_table": {"motifs": len(table.get("motifs", [])),
                            "proposable": sum(1 for m in table.get("motifs", [])
                                              if m.get("proposable")),
                            "meta": table.get("meta", {})},
            "money": money, "opponent_money": opp, "margin": money - opp,
            "changed_turns": len(changes), "changes": changes,
            "proposer_overhead_s": round(overhead, 3),
            "proposer_worst_turn_s": round(worst, 4),
            "proposer_mean_turn_s": round(overhead / max(1, n_turns), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--seat", type=int, default=0)
    ap.add_argument("--baseline", default="../20260907-offline-agent/main.py::agent")
    ap.add_argument("--opponent", default="starter")
    ap.add_argument("--motifs", default="results/motifs.json")
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--allow-displace-move", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    table = json.load(open(a.motifs))
    rows = []
    for seed in a.seeds:
        for arm in ("off", "on"):
            r = run(seed, a.seat, a.baseline, a.opponent, table, arm=arm,
                    max_steps=a.max_steps,
                    allow_displace_move=a.allow_displace_move)
            rows.append(r)
            print(f"seed {seed} arm {arm:3s}  cash {r['money']:10.0f}  "
                  f"opp {r['opponent_money']:10.0f}  margin {r['margin']:+10.0f}  "
                  f"changed {r['changed_turns']:3d}  "
                  f"overhead {r['proposer_overhead_s']:.2f}s "
                  f"(worst turn {r['proposer_worst_turn_s'] * 1000:.0f}ms)", flush=True)
    print("\n=== paired ===")
    for seed in a.seeds:
        off = next(r for r in rows if r["seed"] == seed and r["arm"] == "off")
        on = next(r for r in rows if r["seed"] == seed and r["arm"] == "on")
        print(f"seed {seed}: cash {off['money']:.0f} -> {on['money']:.0f} "
              f"({on['money'] - off['money']:+.0f}), margin {off['margin']:+.0f} -> "
              f"{on['margin']:+.0f} ({on['margin'] - off['margin']:+.0f}), "
              f"{on['changed_turns']} turns changed")
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        json.dump(rows, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
