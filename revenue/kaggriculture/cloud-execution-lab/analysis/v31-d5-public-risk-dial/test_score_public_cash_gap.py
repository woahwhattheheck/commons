from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("d5", HERE / "score_public_cash_gap.py")
d5 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(d5)


def payload():
    return {
        "schema": d5.INPUT_SCHEMA,
        "checkpoints": [576, 648],
        "tight_threshold": 100.0,
        "games": [
            {
                "game_id": "g0",
                "opponent": "a",
                "candidate_seat": 0,
                "terminal_scores": [1100, 1000],
                "observations": [
                    {"step": 576, "farms_money": [1000, 950]},
                    {"step": 648, "farms_money": [1050, 1000]},
                ],
            },
            {
                "game_id": "g1",
                "opponent": "b",
                "candidate_seat": 1,
                "terminal_scores": [1000, 800],
                "observations": [
                    {"step": 576, "farms_money": [900, 950]},
                    {"step": 648, "farms_money": [950, 900]},
                ],
            },
        ],
    }


class D5PublicCashGapTests(unittest.TestCase):
    def test_source_contract_is_public_money_and_terminal_money(self):
        engine = HERE.parents[1] / "reference" / "engine" / "kaggriculture.py"
        source = engine.read_text(encoding="utf-8")
        self.assertIn('obs0.farms = farms', source)
        self.assertIn('state[i].observation.farms = farms', source)
        self.assertIn('state[i].observation.private = privates[i]', source)
        self.assertIn('s.reward = float(obs0.farms[s.observation.player]["money"])', source)

    def test_seat_normalization(self):
        report = d5.analyze(payload())
        at648 = report["checkpoints"][1]
        # g0: +50 -> +100; g1 candidate seat1: -50 -> -200.
        self.assertEqual(at648["strict_sign_reversals"], 0)
        self.assertEqual(at648["sign_agreement_rate"], 1.0)
        self.assertEqual(at648["terminal_margin_mean"], -50.0)
        self.assertFalse(report["policy_authorized"])

    def test_tight_confusion_is_candidate_relative(self):
        at648 = d5.analyze(payload())["checkpoints"][1]
        self.assertEqual(at648["tight_confusion"], {"tp": 1, "fp": 1, "fn": 0, "tn": 0})
        self.assertEqual(at648["tight_precision"], 0.5)
        self.assertEqual(at648["tight_recall"], 1.0)

    def test_unknown_game_field_rejected_to_block_private_features(self):
        p = payload()
        p["games"][0]["rival_private"] = {"shed": {"WOOL": 99}}
        with self.assertRaisesRegex(ValueError, "keys must be exactly"):
            d5.analyze(p)

    def test_unknown_observation_field_rejected(self):
        p = payload()
        p["games"][0]["observations"][0]["future_money"] = 999
        with self.assertRaisesRegex(ValueError, "keys must be exactly"):
            d5.analyze(p)

    def test_bool_and_string_numbers_rejected(self):
        for bad in (True, "100", None):
            p = payload()
            p["games"][0]["observations"][0]["farms_money"][0] = bad
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "finite JSON number"):
                d5.analyze(p)

    def test_candidate_seat_strict_integer(self):
        for bad in (True, 1.0, "1", 2):
            p = payload()
            p["games"][0]["candidate_seat"] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                d5.analyze(p)

    def test_checkpoint_set_must_match_exactly(self):
        p = payload()
        p["games"][0]["observations"].pop()
        with self.assertRaisesRegex(ValueError, "observation steps must equal checkpoints"):
            d5.analyze(p)
        p = payload()
        p["games"][0]["observations"].append({"step": 600, "farms_money": [1, 2]})
        with self.assertRaisesRegex(ValueError, "observation steps must equal checkpoints"):
            d5.analyze(p)

    def test_duplicate_game_and_checkpoint_rejected(self):
        p = payload()
        p["games"][1]["game_id"] = "g0"
        with self.assertRaisesRegex(ValueError, "duplicate game_id"):
            d5.analyze(p)
        p = payload()
        p["checkpoints"] = [576, 576]
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            d5.analyze(p)

    def test_nonfinite_rejected(self):
        p = payload()
        p["games"][0]["terminal_scores"][0] = float("inf")
        with self.assertRaisesRegex(ValueError, "finite JSON number"):
            d5.analyze(p)

    def test_output_never_authorizes_policy(self):
        report = d5.analyze(payload())
        self.assertFalse(report["policy_authorized"])
        self.assertIn("holdout", report["required_next"])


if __name__ == "__main__":
    unittest.main()
