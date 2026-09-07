"""Bounded model-driven play inside a real episode.

The episode is real and official from step 0. A cheap warm-up agent plays the seat
up to `--from-step`, then E4B drives the seat for `--turns` real turns while the
opponent plays throughout. Every model turn records its prompt, raw generation,
timing and legality.

This is the model-to-game loop, not a simulation of one: the actions the model
authors are the actions the official interpreter executes.
"""

import argparse
import json
import os
import time

import cards as cards_mod
import driver as driver_mod
import exemplars
import runner as runner_mod


def _load_agent(spec):
    if "::" not in spec:
        return spec, spec
    path, name = spec.split("::", 1)
    import importlib.util
    sp = importlib.util.spec_from_file_location(
        os.path.splitext(os.path.basename(path))[0] + "_ag", path)
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    return getattr(mod, name), f"{os.path.basename(path)}::{name}"


def _call(agent, obs, config):
    if isinstance(agent, str):
        from kaggle_environments.envs.kaggriculture import kaggriculture as K
        return {"starter": K.starter_agent, "random": K.random_agent,
                "pass": K.pass_agent}[agent](obs)
    try:
        return agent(obs, config)
    except TypeError:
        return agent(obs)


def play(model_path, seed, seat, from_step, turns, warmup_spec, opponent_spec,
         deriv_cards, eval_cards, max_market=3, out=None, examples="pairs",
         bank_path=None):
    warm, warm_label = _load_agent(warmup_spec)
    opp, opp_label = _load_agent(opponent_spec)
    surfaces, prov = exemplars.build(deriv_cards, eval_cards)

    if examples == "control":
        # No inference: the warm-up agent plays the same window, so the segment's
        # cash change is attributable to the model turns rather than to the window.
        env2 = cards_mod.make_env(seed)
        env2.reset(2)
        n = 0
        while not env2.done and n < turns + max(0, from_step):
            acts = []
            for i in range(2):
                o = env2.state[i].observation
                acts.append(_call(warm if i == seat else opp, o, env2.configuration))
            step_now = int(env2.state[seat].observation.get("step", 0) or 0)
            env2.step(acts)
            n += 1
            if step_now >= from_step + turns - 1:
                break
        money = float(env2.state[0].observation.farms[seat]["money"])
        opp_money = float(env2.state[0].observation.farms[1 - seat]["money"])
        r_cfg = {"control": True}
        return {"seed": seed, "seat": seat, "from_step": from_step,
                "model_turns": 0, "warmup": warm_label, "opponent": opp_label,
                "money": money, "opponent_money": opp_money,
                "margin": money - opp_money, "settings": r_cfg, "turns": [],
                "summary": {"control": True, "model_turns": 0}}
    env = cards_mod.make_env(seed)
    env.reset(2)
    r = runner_mod.Runner(model_path)
    bank = None
    if examples == "bank":
        import exemplar_bank as EB
        bank = EB.Bank(bank_path)
    d = driver_mod.ModelDriver(r, surfaces, max_market=max_market,
                               examples=examples, bank=bank)
    model_turns = 0
    t_start = time.time()
    try:
        while not env.done and model_turns < turns:
            actions = []
            for i in range(2):
                obs = env.state[i].observation
                cfg = env.configuration
                if i == seat:
                    step = int(obs.get("step", 0))
                    if step >= from_step and model_turns < turns and examples != "control":
                        a = d.act(obs, dict(cfg), seat)
                        model_turns += 1
                        last = d.log[-1]
                        print(f"step{step:4d} day{last['day']:2d} h{last['hour']:2d} "
                              f"{last['action']['farmer']!s:26s} hands={len(last['action']['hands'])} "
                              f"mkt={last['action']['market']!s:34s} "
                              f"{'legal' if last['legal'] else 'ILLEGAL'} "
                              f"{last['timing_s']['model_inference']:5.2f}s"
                              + (f" REJECT[{last['rejected']}]" if last["rejected"] else ""), flush=True)
                        if last.get("examples_used"):
                            for e in last["examples_used"]:
                                print(f"        example[{e['provenance']}] {e['action'][:96]}", flush=True)
                        print(f"        plan: {(last.get('plan') or '')[:150]}", flush=True)
                    else:
                        a = _call(warm, obs, cfg)
                else:
                    a = _call(opp, obs, cfg)
                actions.append(a)
            env.step(actions)
    finally:
        r.close()

    final = env.state
    money = float(final[seat].observation.farms[seat]["money"])
    opp_money = float(final[1 - seat].observation.farms[1 - seat]["money"])
    payload = {
        "seed": seed, "seat": seat, "from_step": from_step,
        "model_turns": model_turns, "warmup": warm_label, "opponent": opp_label,
        "wall_total_s": round(time.time() - t_start, 1),
        "money": money, "opponent_money": opp_money, "margin": money - opp_money,
        "settings": r.cfg, "provenance": prov, "turns": d.log,
    }
    n = len(d.log)
    legal = sum(1 for x in d.log if x["legal"])
    rej = sum(1 for x in d.log if x["rejected"])
    infer = [x["timing_s"]["model_inference"] for x in d.log]
    nonpass = sum(1 for x in d.log if x["action"]["farmer"][0] != "PASS")
    mkt = sum(len(x["action"]["market"]) for x in d.log)
    payload["summary"] = {
        "model_turns": n, "legal": legal, "syntax_rejections": rej,
        "non_pass_farmer": nonpass, "market_orders_authored": mkt,
        "mean_inference_s": round(sum(infer) / n, 2) if n else None,
        "total_inference_s": round(sum(infer), 1),
    }
    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w") as fh:
            json.dump(payload, fh, indent=1, default=str)
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--seat", type=int, default=0)
    ap.add_argument("--from-step", type=int, default=0)
    ap.add_argument("--turns", type=int, default=20)
    ap.add_argument("--warmup", default="starter")
    ap.add_argument("--opponent", default="starter")
    ap.add_argument("--deriv-cards", required=True)
    ap.add_argument("--eval-cards", required=True)
    ap.add_argument("--max-market", type=int, default=3)
    ap.add_argument("--out", default=None)
    ap.add_argument("--examples", default="pairs",
                    choices=("pairs", "bank", "control"))
    ap.add_argument("--bank", default=None)
    a = ap.parse_args()
    p = play(a.model, a.seed, a.seat, a.from_step, a.turns, a.warmup, a.opponent,
             cards_mod.load(a.deriv_cards), cards_mod.load(a.eval_cards),
             max_market=a.max_market, out=a.out, examples=a.examples, bank_path=a.bank)
    print("\n=== summary ===")
    print(json.dumps(p["summary"], indent=1))
    print(f"money={p['money']:.0f} opponent={p['opponent_money']:.0f} margin={p['margin']:+.0f}")


if __name__ == "__main__":
    main()
