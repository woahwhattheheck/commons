#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("witness", HERE / "action_divergence_witness.py")
w = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(w)


def row(step, obs, action):
    return {
        "step": step,
        "observation_sha256": w._digest({"obs": obs}),
        "response_kind": "action",
        "action_sha256": w._digest({"a": action}),
        "action": {"a": action},
    }


class WitnessTests(unittest.TestCase):
    def test_candidate_action_first_then_observation_diverges(self):
        lc = [row(i, 0 if i < 4 else 1, 0 if i < 3 else 7) for i in range(6)]
        rc = [row(i, 0 if i < 4 else 2, 0 if i < 3 else 8) for i in range(6)]
        lo = [row(i, 0 if i < 4 else 1, 4 if i < 4 else 5) for i in range(6)]
        ro = [row(i, 0 if i < 4 else 2, 4 if i < 4 else 6) for i in range(6)]
        got = w.compare_traces(lc, rc, lo, ro, radius=1)
        self.assertEqual(got["first_candidate_action_divergence_step"], 3)
        self.assertEqual(got["first_candidate_observation_divergence_step"], 4)
        self.assertEqual(got["first_opponent_action_divergence_step"], 4)
        self.assertEqual(got["first_any_action_divergence_step"], 3)
        self.assertTrue(got["candidate_action_is_first_observed_divergence"])
        self.assertEqual([r["step"] for r in got["witness_window"]], [2, 3, 4])
        self.assertEqual(got["witness_window"][1]["left_candidate"]["action"], {"a": 7})
        self.assertEqual(got["witness_window"][1]["right_candidate"]["action"], {"a": 8})

    def test_complete_compact_vectors_bind_trace_digest_without_full_actions(self):
        trace = [row(i, i, i + 10) for i in range(5)]
        got = w.compare_traces(trace, trace, trace, trace)
        vectors = got["trace_vectors"]
        self.assertEqual(
            set(vectors),
            {"left_candidate", "right_candidate", "left_opponent", "right_opponent"},
        )
        compact = vectors["left_candidate"]
        self.assertEqual(len(compact), 5)
        self.assertEqual([item["step"] for item in compact], list(range(5)))
        self.assertEqual(
            set(compact[0]),
            {"step", "observation_sha256", "action_sha256"},
        )
        expected_digest = w._digest([
            {key: value for key, value in item.items() if key != "action"}
            for item in trace
        ])
        self.assertEqual(got["left_candidate_trace_sha256"], expected_digest)

    def test_identical_traces_have_no_window(self):
        trace = [row(i, i, i + 10) for i in range(5)]
        got = w.compare_traces(trace, trace, trace, trace)
        self.assertTrue(got["all_actions_identical"])
        self.assertIsNone(got["first_any_action_divergence_step"])
        self.assertEqual(got["witness_window"], [])

    def test_opponent_divergence_first_blocks_candidate_causal_label(self):
        lc = [row(i, i, 1 if i < 3 else 2) for i in range(5)]
        rc = [row(i, i, 1 if i < 3 else 3) for i in range(5)]
        lo = [row(i, i, 9 if i < 2 else 8) for i in range(5)]
        ro = [row(i, i, 9 if i < 2 else 7) for i in range(5)]
        got = w.compare_traces(lc, rc, lo, ro)
        self.assertEqual(got["first_opponent_action_divergence_step"], 2)
        self.assertEqual(got["first_candidate_action_divergence_step"], 3)
        self.assertFalse(got["candidate_action_is_first_observed_divergence"])

    def test_same_step_observation_divergence_blocks_causal_label(self):
        lc = [row(i, 0, 0 if i < 2 else 1) for i in range(4)]
        rc = [row(i, 0 if i < 2 else 1, 0 if i < 2 else 2) for i in range(4)]
        opp = [row(i, 0, 5) for i in range(4)]
        got = w.compare_traces(lc, rc, opp, opp)
        self.assertEqual(got["first_candidate_action_divergence_step"], 2)
        self.assertEqual(got["first_candidate_observation_divergence_step"], 2)
        self.assertFalse(got["candidate_action_is_first_observed_divergence"])

    def test_noncontiguous_trace_rejects(self):
        bad = [row(0, 0, 0), row(2, 0, 0)]
        good = [row(0, 0, 0), row(1, 0, 0)]
        with self.assertRaises(w.WitnessError):
            w.compare_traces(bad, good, good, good)

    def test_trace_length_mismatch_rejects(self):
        a = [row(0, 0, 0)]
        b = [row(0, 0, 0), row(1, 0, 0)]
        with self.assertRaises(w.WitnessError):
            w.compare_traces(a, b, b, b)

    def test_window_radius_bounds(self):
        trace = [row(i, i, i) for i in range(2)]
        with self.assertRaises(w.WitnessError):
            w.compare_traces(trace, trace, trace, trace, radius=13)

    def test_seat_parser(self):
        self.assertEqual(w._parse_seats("0,1"), [0, 1])
        self.assertEqual(w._parse_seats("1"), [1])
        for bad in ("", "2", "0,0", "x"):
            with self.assertRaises(w.WitnessError):
                w._parse_seats(bad)

    def test_sha_validation(self):
        good = "a" * 64
        self.assertEqual(w._expected_sha(good, "x"), good)
        for bad in ("A" * 64, "a" * 63, "nope"):
            with self.assertRaises(w.WitnessError):
                w._expected_sha(bad, "x")


if __name__ == "__main__":
    unittest.main()
