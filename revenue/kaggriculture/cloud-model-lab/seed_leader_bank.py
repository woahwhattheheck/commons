"""Build teacher rows from the public leader episode 106392861.

Source: revenue/kaggriculture/cloud-frontier-trace/results/106392861/decision-cases.json.gz,
retrieved and reconciled by ROWAN against the pinned interpreter (719 verified
transitions). Each case carries a frame with an observation and an action.

Two things this file will not do:

  * It will not bank a row until the frame alignment is VERIFIED against the engine.
    The kaggle-environments recording convention is not obvious -- a recorded step's
    observation already reflects that step's action -- so the pairing is checked by
    applying the candidate action to the candidate observation and comparing the
    result to the following frame. Rows are banked only for the alignment that
    reconciles.
  * It will not present these as this model's own successes. Every row is labelled
    `teacher:ymg_aq:episode106392861`, and the bank's injected header states teacher
    provenance. Episode 106392861 is kept out of evaluation.
"""

import argparse
import copy
import gzip
import json
import os
import subprocess

import constraints
import exemplar_bank as EB
from constraints import engine

PROVENANCE = "teacher:ymg_aq:episode106392861"
CASES_PATH = ("revenue/kaggriculture/cloud-frontier-trace/results/106392861/"
              "decision-cases.json.gz")


def load_cases(repo_root, ref="origin/main"):
    """Read the landed decision cases straight out of git, without a checkout."""
    blob = subprocess.run(["git", "-C", repo_root, "show", f"{ref}:{CASES_PATH}"],
                          capture_output=True, check=True).stdout
    return json.loads(gzip.decompress(blob))


def _apply_unit_phase(obs, config, seat, action):
    """Replay just the seat's unit phase, as the interpreter orders it."""
    K = engine()
    farm = copy.deepcopy(obs["farms"][seat])
    priv = copy.deepcopy(obs["private"])
    board = int(config.get("boardSize", 10) or 10)
    tpd = int(config.get("turnsPerDay", 24) or 24)
    cap = int(config.get("shedCapacity", 100) or 100)
    day = int(obs["day"])
    units = [action.get("farmer", ["PASS"])] + list(action.get("hands") or [])
    demand = {}
    for a in units:
        if isinstance(a, list) and len(a) >= 2 and a[0] == "PLANT":
            demand[a[1]] = demand.get(a[1], 0) + 1
    seeds = priv.get("seeds", {})
    blocked = {c for c, n in demand.items() if n > seeds.get(c, 0)}
    for i, a in enumerate(units):
        eff = list(a)
        if len(eff) >= 2 and eff[0] == "PLANT" and eff[1] in blocked:
            eff = ["PASS"]
        try:
            K._apply_unit_action(farm, priv, i, eff, board, day, tpd, cap)
        except Exception:
            pass
    return farm, priv


def verify_alignment(cases, config, seat=0, sample=25):
    """Which frame pairing reconciles: does frame[k]'s action produce frame[k+1]?

    Returns the offset that matches, or None. Positions are compared because they are
    the least ambiguous consequence of a unit phase.
    """
    for offset in (0, -1):
        agree = total = 0
        for case in cases[:sample]:
            frames = case.get("before_frame") or []
            if len(frames) < 2:
                continue
            a_idx = 0 if offset == 0 else 1
            o_idx = 0
            act = frames[a_idx].get("action")
            obs = frames[o_idx].get("observation")
            nxt = frames[1].get("observation")
            if not (act and obs and nxt):
                continue
            farm, _ = _apply_unit_phase(obs, config, seat, act)
            got = [list(map(int, farm["farmer"]))] + [list(map(int, p)) for p in farm.get("hands", [])]
            want = [list(map(int, nxt["farms"][seat]["farmer"]))] + \
                   [list(map(int, p)) for p in nxt["farms"][seat].get("hands", [])]
            total += 1
            if got == want:
                agree += 1
        if total and agree / total > 0.9:
            return {"offset": offset, "agreement": round(agree / total, 3),
                    "checked": total}
    return None


def build(repo_root, out_bank, seat=0, ref="origin/main", limit=None):
    data = load_cases(repo_root, ref)
    cases = data.get("cases") or []
    config = {"boardSize": 10, "turnsPerDay": 24, "shedCapacity": 100,
              "maxMarketOrdersPerTurn": 10, "episodeSteps": 720}
    align = verify_alignment(cases, config, seat)
    if not align:
        raise SystemExit("frame alignment did not reconcile against the engine; "
                         "no rows banked")
    bank = EB.Bank(out_bank, write_path=out_bank)
    banked = skipped = 0
    for case in (cases[:limit] if limit else cases):
        frames = case.get("before_frame") or []
        if not frames:
            continue
        idx = 0 if align["offset"] == 0 else 1
        if idx >= len(frames):
            continue
        obs = frames[0].get("observation")
        act = frames[idx].get("action")
        if not obs or not act:
            continue
        turn = {"farmer": list(act.get("farmer") or ["PASS"]),
                "hands": [list(h) for h in (act.get("hands") or [])],
                "market": [list(m) for m in (act.get("market") or [])]}
        try:
            adm = constraints.admissible(obs, config, seat)
            cls = EB.situation_class(obs, config, seat, adm)
            state = EB.structured_state(obs, config, seat)
        except Exception:
            skipped += 1
            continue
        bank.record(cls, EB.context_of(obs), state, turn, PROVENANCE,
                    plan=f"leader episode 106392861 step {case.get('action_step')}")
        banked += 1
    return {"alignment": align, "banked": banked, "skipped": skipped,
            "bank": EB.describe(out_bank), "provenance": PROVENANCE}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/home/user/commons")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seat", type=int, default=0)
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    print(json.dumps(build(a.repo, a.out, a.seat, a.ref, a.limit), indent=1))


if __name__ == "__main__":
    main()
