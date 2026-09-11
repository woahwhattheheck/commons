# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import l3_tape_regime as regime  # noqa: E402


def make_tape(horizontal: bool) -> list[dict]:
    rows = []
    for step in range(719):
        if horizontal:
            op = "EAST" if step % 2 == 0 else "WEST"
        else:
            op = "SOUTH" if step % 2 == 0 else "NORTH"
        rows.append({"farmer": ["PASS"], "hands": [[op]], "market": []})
    return rows


def rival_farm(position, *, malformed_hands=None):
    hands = [list(position)] if malformed_hands is None else malformed_hands
    return {
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "farmer": [4, 4],
        "hands": hands,
        "unlocked_quadrants": ["NW"],
    }


def observation(step, position=(2, 2), *, player=0, malformed_hands=None, private=None):
    rival = rival_farm(position, malformed_hands=malformed_hands)
    own = {
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "farmer": [4, 4],
        "hands": [],
        "unlocked_quadrants": ["NW"],
    }
    farms = [own, rival] if player == 0 else [rival, own]
    return {
        "step": step,
        "player": player,
        "farms": farms,
        "market": {"prices": {}},
        "town": {"unlocked_shops": []},
        "private": {} if private is None else private,
    }


def ideal_horizontal_positions(start=144, stop=648):
    pos = [2, 2]
    out = {start: tuple(pos)}
    for action_step in range(start, stop):
        if action_step % 2 == 0:
            pos[0] += 1
        else:
            pos[0] -= 1
        out[action_step + 1] = tuple(pos)
    return out


class TapeRegimeTests(unittest.TestCase):
    def setUp(self):
        self.tapes = [make_tape(True), make_tape(False)]

    def test_exact_public_horizontal_trace_is_tape_like_candidate(self):
        scorer = regime.TapeRegimeScorer(self.tapes)
        positions = ideal_horizontal_positions()
        for step in range(144, 649):
            scorer.observe(observation(step, positions[step]))
        result = scorer.result()
        self.assertFalse(result["broken"])
        self.assertEqual(result["best"]["tape"], 0)
        self.assertEqual(result["best"]["matches"], 504)
        self.assertEqual(result["best"]["comparisons"], 504)
        self.assertEqual(result["best"]["ratio"], 1.0)
        self.assertEqual(result["provisional_status"], "PROVISIONAL_TAPE_LIKE")
        self.assertFalse(result["gate_ready"])

    def test_stationary_trace_is_off_tape_candidate_but_never_gate_ready(self):
        scorer = regime.TapeRegimeScorer(self.tapes)
        for step in range(144, 649):
            scorer.observe(observation(step, (2, 2)))
        result = scorer.result()
        self.assertEqual(result["best"]["matches"], 0)
        self.assertEqual(result["best"]["comparisons"], 504)
        self.assertEqual(result["provisional_status"], "PROVISIONAL_OFF_TAPE")
        self.assertFalse(result["gate_ready"])

    def test_hand_count_changes_are_excluded_not_counted_as_mismatches(self):
        scorer = regime.TapeRegimeScorer(self.tapes)
        positions = ideal_horizontal_positions()
        for step in range(144, 649):
            if step == 300:
                scorer.observe(observation(step, malformed_hands=[]))
            else:
                scorer.observe(observation(step, positions[step]))
        result = scorer.result()
        self.assertFalse(result["broken"])
        self.assertEqual(result["excluded_hand_count_changes"], 2)
        self.assertEqual(result["best"]["comparisons"], 502)
        self.assertEqual(result["best"]["matches"], 502)

    def test_private_payload_cannot_change_public_score(self):
        positions = ideal_horizontal_positions()
        a = regime.TapeRegimeScorer(self.tapes)
        b = regime.TapeRegimeScorer(self.tapes)
        for step in range(144, 649):
            a.observe(observation(step, positions[step], private={"shed": {"MILK": 999999}}))
            b.observe(observation(step, positions[step], private={"inventories": [{"WHEAT": 777}]}))
        self.assertEqual(a.result()["best"], b.result()["best"])

    def test_seat_one_reads_public_rival_seat_zero(self):
        scorer = regime.TapeRegimeScorer(self.tapes)
        positions = ideal_horizontal_positions()
        for step in range(144, 649):
            scorer.observe(observation(step, positions[step], player=1))
        self.assertEqual(scorer.result()["best"]["matches"], 504)

    def test_skipped_observation_fails_closed_for_rest_of_game(self):
        scorer = regime.TapeRegimeScorer(self.tapes)
        positions = ideal_horizontal_positions()
        scorer.observe(observation(144, positions[144]))
        scorer.observe(observation(145, positions[145]))
        scorer.observe(observation(147, positions[147]))
        for step in range(148, 649):
            scorer.observe(observation(step, positions[step]))
        result = scorer.result()
        self.assertTrue(result["broken"])
        self.assertEqual(result["provisional_status"], "UNKNOWN")
        self.assertFalse(result["gate_ready"])

    def test_malformed_boolean_coordinate_fails_closed(self):
        scorer = regime.TapeRegimeScorer(self.tapes)
        positions = ideal_horizontal_positions()
        for step in range(144, 200):
            scorer.observe(observation(step, positions[step]))
        scorer.observe(observation(200, malformed_hands=[[True, 2]]))
        for step in range(201, 649):
            scorer.observe(observation(step, positions[step]))
        result = scorer.result()
        self.assertTrue(result["broken"])
        self.assertGreaterEqual(result["invalid_observations"], 1)
        self.assertEqual(result["provisional_status"], "UNKNOWN")

    def test_restart_resets_broken_state(self):
        scorer = regime.TapeRegimeScorer(self.tapes)
        scorer.observe(observation(144, (2, 2)))
        scorer.observe(observation(146, (2, 2)))
        self.assertTrue(scorer.result()["broken"])
        scorer.observe(observation(0, (2, 2)))
        self.assertFalse(scorer.result()["broken"])
        self.assertEqual(scorer.result()["invalid_observations"], 0)

    def test_current_tape_bank_is_exact_expected_shape(self):
        tapes = regime.load_current_tapes()
        self.assertEqual(len(tapes), 13)
        self.assertTrue(all(len(tape) == 719 for tape in tapes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
