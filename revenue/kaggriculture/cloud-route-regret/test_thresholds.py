# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

from thresholds import build_pairs, select_threshold


def outcome(own, rival):
    result = "W" if own > rival else "L" if own < rival else "T"
    return {
        "own": float(own),
        "rival": float(rival),
        "margin": float(own - rival),
        "result": result,
        "win": int(result == "W"),
        "loss": int(result == "L"),
        "tie": int(result == "T"),
    }


def pair(value, force_own, stay_own, *, seed=1):
    return {
        "checkpoint": 10,
        "feature": "x",
        "feature_value": value,
        "shipped_threshold": 5,
        "target": "T",
        "opponent": "o",
        "seed": seed,
        "seat": 0,
        "auto_match": True,
        "force": outcome(force_own, 100),
        "stay": outcome(stay_own, 100),
        "auto": outcome(force_own if value >= 5 else stay_own, 100),
    }


def game(arm, *, pre="same", feature=7, route_after=None, stream="natural"):
    mode = arm.split("_", 1)[0] if arm != "auto" else "auto"
    if route_after is None:
        route_after = "T" if mode == "force" else "M"
    receipt = {
        "schema": "titan-route-regret-event/v1",
        "mode": mode,
        "checkpoint": 10,
        "step": 10,
        "player": 0,
        "feature": "x",
        "feature_value": feature,
        "shipped_threshold": 5,
        "target": "T",
        "natural_target": feature >= 5,
        "route_before": "M",
        "route_after": route_after,
        "switch_legal": True,
        "override_applied": True,
        "pre_world_sha256": pre,
        "opponent_action_sha256": "rival",
    }
    return {
        "arm": arm,
        "opponent": "o",
        "seed": 1,
        "tested_seat": 0,
        "status": "complete",
        "failure": None,
        "bank_snapshot": [150, 100],
        "checkpoint_receipts": [receipt],
        "tested_action_stream_sha256": stream,
        "opponent_action_stream_sha256": "opponent-stream",
        "world_stream_sha256": "world-stream",
    }


class ThresholdSelectionTests(unittest.TestCase):
    def test_shipped_threshold_wins_exact_ties(self):
        rows = [pair(4, 100, 100), pair(7, 100, 100)]
        selected = select_threshold(rows, 5)
        self.assertEqual(selected["selected_threshold"], 5)
        self.assertFalse(selected["strict_development_improvement"])

    def test_selector_receives_development_only(self):
        development = [pair(4, 80, 120), pair(7, 140, 80)]
        first = select_threshold(development, 5)
        hostile_holdout = [pair(4, -100000, 100000, seed=9)]
        second = select_threshold(development, 5)
        self.assertEqual(first, second)
        self.assertTrue(hostile_holdout)  # Demonstrates it was not an argument.

    def test_prefix_mismatch_is_rejected_not_scored(self):
        auto = game("auto", stream="natural")
        force = game("force_10", pre="left", stream="natural")
        stay = game("stay_10", pre="right", stream="other")
        pairs, rejected = build_pairs([auto, force, stay], [(10, "x", 5, "T")])
        self.assertEqual(pairs, [])
        self.assertEqual(len(rejected), 1)
        self.assertIn("prefix state mismatch", rejected[0]["reason"])

    def test_natural_arm_must_reproduce_auto(self):
        auto = game("auto", stream="auto")
        force = game("force_10", stream="force")
        stay = game("stay_10", stream="stay")
        pairs, rejected = build_pairs([auto, force, stay], [(10, "x", 5, "T")])
        self.assertEqual(pairs, [])
        self.assertIn("untouched auto", rejected[0]["reason"])


if __name__ == "__main__":
    unittest.main()
