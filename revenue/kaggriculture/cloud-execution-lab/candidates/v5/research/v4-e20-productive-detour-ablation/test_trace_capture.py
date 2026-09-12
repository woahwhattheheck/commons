# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import json
import unittest

import trace_capture as trace


class _Actor:
    def __init__(self, spec):
        self.spec = spec

    def act(self, observation, configuration, timeout):
        return {"kind": "action", "action": copy.deepcopy(observation["action"])}


class _Evaluator:
    Actor = _Actor

    @staticmethod
    def play(candidate_spec, other_spec):
        candidate = _Evaluator.Actor(candidate_spec)
        other = _Evaluator.Actor(other_spec)
        candidate.act({"action": {"market": [["HIRE"]]}}, {}, 1.0)
        other.act({"action": {"market": [["SELL", "MILK", 1]]}}, {}, 1.0)
        candidate.act({"action": {"market": [["PASS"]]}}, {}, 1.0)
        return {"status": "complete", "steps": 719, "scores": [10, 7]}


class TraceCaptureTests(unittest.TestCase):
    def test_action_trace_hash_is_stable_and_order_sensitive(self):
        actions = [{"market": [["HIRE"]]}, {"market": [["PASS"]]}]
        expected = hashlib.sha256()
        for step, action in enumerate(actions):
            expected.update(json.dumps(
                {"step": step, "action": action},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8"))
        self.assertEqual(trace.action_trace_sha256(actions), expected.hexdigest())
        self.assertNotEqual(
            trace.action_trace_sha256(actions),
            trace.action_trace_sha256(list(reversed(actions))),
        )

    def test_first_divergence_uses_e20_treatment_label(self):
        control = [{"x": 1}, {"x": 2}]
        treatment = [{"x": 1}, {"x": 3}]
        self.assertEqual(
            trace.first_action_divergence(control, treatment),
            {"step": 1, "control": {"x": 2}, "e20_detour_off": {"x": 3}},
        )
        self.assertIsNone(trace.first_action_divergence(control, copy.deepcopy(control)))
        self.assertEqual(
            trace.first_action_divergence([{"x": 1}], [{"x": 1}, {"x": 2}]),
            {"step": 1, "control": None, "e20_detour_off": {"x": 2}},
        )

    def test_play_trace_captures_only_candidate_and_restores_actor_method(self):
        original = _Evaluator.Actor.act
        game, actions = trace.play_with_candidate_trace(
            _Evaluator,
            "candidate.py",
            "rival.py",
            candidate_spec="candidate.py",
        )
        self.assertEqual(game["scores"], [10, 7])
        self.assertEqual(actions, [
            {"market": [["HIRE"]]},
            {"market": [["PASS"]]},
        ])
        self.assertIs(_Evaluator.Actor.act, original)

    def test_play_trace_restores_method_on_exception(self):
        class BrokenEvaluator(_Evaluator):
            @staticmethod
            def play(candidate_spec, other_spec):
                actor = BrokenEvaluator.Actor(candidate_spec)
                actor.act({"action": {"market": [["HIRE"]]}}, {}, 1.0)
                raise RuntimeError("boom")

        original = BrokenEvaluator.Actor.act
        with self.assertRaisesRegex(RuntimeError, "boom"):
            trace.play_with_candidate_trace(
                BrokenEvaluator,
                "candidate.py",
                "rival.py",
                candidate_spec="candidate.py",
            )
        self.assertIs(BrokenEvaluator.Actor.act, original)

    def test_game_scores_requires_complete_terminal_game(self):
        game = {"status": "complete", "steps": 719, "scores": [11, 5]}
        self.assertEqual(trace.game_scores(game, 0), {"own": 11, "rival": 5, "margin": 6})
        self.assertEqual(trace.game_scores(game, 1), {"own": 5, "rival": 11, "margin": -6})
        self.assertIsNone(trace.game_scores({"status": "timeout", "steps": 719, "scores": [1, 2]}, 0))
        self.assertIsNone(trace.game_scores({"status": "complete", "steps": 718, "scores": [1, 2]}, 0))
        self.assertIsNone(trace.game_scores({"status": "complete", "steps": 719, "scores": [True, 2]}, 0))
        with self.assertRaisesRegex(ValueError, "seat"):
            trace.game_scores(game, 2)

    def test_source_pattern_authority_is_recorded(self):
        self.assertEqual(
            trace.SOURCE_PATTERN_GIT_BLOB,
            "5dc273dcbfaf07d69b2ded7de672bfd003d7454d",
        )


if __name__ == "__main__":
    unittest.main()
