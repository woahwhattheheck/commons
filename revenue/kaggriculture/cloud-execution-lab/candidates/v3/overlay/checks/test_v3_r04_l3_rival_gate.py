# SPDX-License-Identifier: Apache-2.0
"""R04 lane L3 rival gate: L3 applies only against off-tape rivals.

    python -m unittest -v checks/test_v3_r04_l3_rival_gate.py

An on-tape lineage rival walks the tape's shared opening, so its farmer stands where ours
does on nearly every step 1-143. rival_on_tape() counts that agreement over the opening and
holds L3 back while the share is at least RIVAL_GATE_SHARE; otherwise, including when no
opening was readable, L3 applies exactly as before. Covers the detector (matching, diverging,
threshold edge, unreadable observation, reset on a new game, frozen after the window) and the
E184 call site: with L3 on, an on-tape rival still gets the reservation at step >= 648, an
off-tape rival does not.
Standard library only.
"""
from __future__ import annotations

import copy
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_full_router as r04  # noqa: E402
import r04_no_late_sale_advance as nla  # noqa: E402


def observation(step, ours=(4, 4), theirs=(4, 4), player=0):
    farm = {"tiles": [], "farmer": list(ours), "hands": []}
    rival = copy.deepcopy(farm)
    rival["farmer"] = list(theirs)
    farms = [farm, rival] if player == 0 else [rival, farm]
    return {"step": step, "player": player, "farms": farms}


def play_opening(match_every):
    """Feed steps 0-143; the rival matches our farmer on every `match_every`-th step."""
    result = None
    for step in range(0, 144):
        same = step % match_every == 0
        result = r04.rival_on_tape(observation(step, theirs=(4, 4) if same else (9, 9)), step)
    return result


class RivalGate(unittest.TestCase):
    def setUp(self):
        r04._RIVAL_TAPE.update(same=0, seen=0, last=-1)

    def test_rival_on_the_tape_opening_is_on_tape(self):
        self.assertTrue(play_opening(1))

    def test_rival_off_the_tape_opening_is_off_tape(self):
        self.assertFalse(play_opening(3))

    def test_threshold_edge(self):
        r04._RIVAL_TAPE.update(same=80, seen=100, last=99)
        self.assertTrue(r04.rival_on_tape(observation(100), 100))    # 81/101 >= 0.8
        r04._RIVAL_TAPE.update(same=79, seen=100, last=99)
        self.assertFalse(r04.rival_on_tape(observation(100, theirs=(9, 9)), 100))  # 79/101 < 0.8

    def test_decision_is_frozen_after_the_opening(self):
        play_opening(3)
        for step in range(144, 700):
            self.assertFalse(r04.rival_on_tape(observation(step), step))  # later agreement is ignored

    def test_unreadable_observation_counts_nothing(self):
        self.assertFalse(r04.rival_on_tape({"step": 50, "player": 0, "farms": []}, 50))
        self.assertEqual(r04._RIVAL_TAPE["seen"], 0)

    def test_new_game_resets_the_count(self):
        play_opening(1)
        self.assertFalse(r04.rival_on_tape(observation(0), 0))  # new game: no evidence yet
        self.assertEqual(r04._RIVAL_TAPE["seen"], 0)

    def test_seat_one_reads_the_other_farm(self):
        for step in range(0, 144):
            on = r04.rival_on_tape(observation(step, ours=(2, 2), theirs=(2, 2), player=1), step)
        self.assertTrue(on)


class CallSite(unittest.TestCase):
    """At step >= 648 with L3 on, reserve_sales() runs only when the rival is on tape."""

    def setUp(self):
        self.calls = []
        self.saved = (r04.reserve_sales, r04._SALE_PARENT, r04._POLICY, r04.NO_LATE_SALE_ADVANCE, r04.FarmView)
        r04.reserve_sales = lambda *args: self.calls.append(args[-1])
        r04._SALE_PARENT = lambda obs, cfg=None: {"farmer": ["PASS"], "hands": [], "market": []}
        state = type("State", (), {"plan": 0})()
        r04._POLICY = type("Policy", (), {"players": {0: state}, "tapes": {0: []}})()
        r04.NO_LATE_SALE_ADVANCE = True
        r04.FarmView = lambda obs: None

    def tearDown(self):
        (r04.reserve_sales, r04._SALE_PARENT, r04._POLICY, r04.NO_LATE_SALE_ADVANCE,
         r04.FarmView) = self.saved
        r04._RIVAL_TAPE.update(same=0, seen=0, last=-1)
        nla.reset()

    def run_game(self, rival_matches):
        r04._RIVAL_TAPE.update(same=0, seen=0, last=-1)
        for step in range(0, 144):
            r04.rival_on_tape(observation(step, theirs=(4, 4) if rival_matches else (9, 9)), step)
        r04.agent(observation(650, theirs=(4, 4)), None)

    def test_on_tape_rival_keeps_the_reservation(self):
        self.run_game(rival_matches=True)
        self.assertEqual(self.calls, [650])

    def test_off_tape_rival_gets_l3(self):
        self.run_game(rival_matches=False)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
