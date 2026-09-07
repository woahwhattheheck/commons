"""Downstream value of a model segment: let a pinned policy finish the game.

Early cash is not the measure. A segment that spends 400 on a cow looks worse at
step 8 and may be ahead by step 700. So each candidate state is handed to the SAME
pinned continuation policy, separately instantiated, which plays the rest of the
official game against the same opponent, config and seed. The matched control is
that policy playing the whole game from step 0.

The difference is a conditional estimate of the segment's downstream value under
that policy. It is not proof of an all-model full-game result, and it is only as
general as the one policy and one seed it uses.

Recorded separately, never merged into one number: final cash and margin, the
purchased-but-uninstalled backlog, goods discarded at the end-of-day drop, and
production actually harvested.
"""

import argparse
import copy
import importlib.util
import json
import os

import cards as cards_mod
from constraints import engine


def load_agent(spec):
    """A SEPARATE instantiation each time, so no state leaks between runs."""
    if "::" not in spec:
        name = spec
        K = engine()
        fn = {"starter": K.starter_agent, "random": K.random_agent,
              "pass": K.pass_agent}[name]
        return (lambda obs, cfg=None: fn(obs)), name
    path, fn_name = spec.split("::", 1)
    sp = importlib.util.spec_from_file_location(
        f"cont_{abs(hash(path + fn_name))}", path)
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    fn = getattr(mod, fn_name)

    def call(obs, cfg=None):
        try:
            return fn(obs, cfg)
        except TypeError:
            return fn(obs)
    return call, f"{os.path.basename(path)}::{fn_name}"


def _metrics(env, seat, cfg):
    """Engine-defined facts about how the episode ended."""
    K = engine()
    obs0 = env.state[0].observation
    farm = obs0.farms[seat]
    priv = env.state[seat].observation.private
    shed = dict(priv.get("shed", {}))
    animals_in_shed = {a: int(n) for a, n in shed.items() if a in K.ANIMALS and n > 0}
    installed = 0
    plants = 0
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict) and "animal" in t:
                installed += 1
            elif isinstance(t, dict) and t.get("kind") == "PLANT":
                plants += 1
    return {
        "final_cash": float(farm["money"]),
        "opponent_cash": float(obs0.farms[1 - seat]["money"]),
        "margin": float(farm["money"]) - float(obs0.farms[1 - seat]["money"]),
        "unsold_shed_units": int(sum(shed.values())),
        "installable_backlog": animals_in_shed,
        "installed_animals": installed,
        "plants_on_board": plants,
    }


def play_out(seed, seat, prefix_actions, warmup_spec, opponent_spec, cont_spec,
             from_step, max_steps=100000):
    """Replay the warm-up, apply `prefix_actions`, then let the continuation finish.

    `prefix_actions` is the ordered list of turns the model authored. The warm-up and
    opponent are deterministic and the episode is seeded, so the replay is exact.
    """
    warm, warm_label = load_agent(warmup_spec)
    opp, opp_label = load_agent(opponent_spec)
    cont, cont_label = load_agent(cont_spec)
    env = cards_mod.make_env(seed)
    env.reset(2)
    used = 0
    discarded = 0
    steps = 0
    while not env.done and steps < max_steps:
        cfg = env.configuration
        obs = env.state[seat].observation
        step = int(obs["day"]) * int(cfg["turnsPerDay"]) + int(obs["hour"])
        if step < from_step:
            mine = warm(obs, cfg)
        elif used < len(prefix_actions):
            mine = prefix_actions[used]
            used += 1
        else:
            mine = cont(obs, cfg)
        # end-of-day discard, measured where the engine measures it
        if (step + 1) % int(cfg["turnsPerDay"]) == 0:
            priv = env.state[seat].observation.private
            carried = sum(sum(i.values()) for i in priv.get("inventories", []))
            room = max(0, int(cfg["shedCapacity"]) - sum(priv.get("shed", {}).values()))
            if carried > room:
                discarded += carried - room
        env.step([mine if i == seat else opp(env.state[i].observation, cfg)
                  for i in range(2)])
        steps += 1
    m = _metrics(env, seat, dict(env.configuration))
    m.update({"seed": seed, "seat": seat, "from_step": from_step,
              "model_turns_applied": used, "discarded_units": discarded,
              "warmup": warm_label, "opponent": opp_label, "continuation": cont_label})
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", default=[],
                    help="a play.py run JSON whose model turns are continued")
    ap.add_argument("--continuation", default="../cloud-market/main.py::agent")
    ap.add_argument("--warmup", default=None,
                    help="override the run's warm-up spec (older runs stored only a label)")
    ap.add_argument("--opponent", default=None,
                    help="override the run's opponent spec")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    results = []
    control_done = set()
    for path in a.run:
        d = json.load(open(path))
        seed, seat = d["seed"], d["seat"]
        prefix = [t["action"] for t in d.get("turns", [])]
        # strip the model's carried plan; the engine takes only the three turn keys
        prefix = [{"farmer": p["farmer"], "hands": p["hands"], "market": p["market"]}
                  for p in prefix]
        warm_spec = a.warmup or d.get("warmup_spec") or d["warmup"]
        opp_spec = a.opponent or d.get("opponent_spec") or d["opponent"]
        r = play_out(seed, seat, prefix, warm_spec, opp_spec, a.continuation,
                     d["from_step"])
        r["label"] = f"model-segment+continuation ({os.path.basename(path)})"
        r["render"] = (d["turns"][0].get("render") if d.get("turns") else None)
        results.append(r)
        key = (seed, seat, d["from_step"], warm_spec, opp_spec)
        if key not in control_done:
            control_done.add(key)
            c = play_out(seed, seat, [], warm_spec, opp_spec, a.continuation,
                         10 ** 9)   # warm-up never yields: the policy plays throughout
            c["label"] = "all-policy control (no model turns)"
            results.append(c)

    for r in results:
        print(json.dumps(r, sort_keys=True))
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(results, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
