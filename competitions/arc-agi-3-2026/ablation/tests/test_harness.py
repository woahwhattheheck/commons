from __future__ import annotations
import copy
import sys
from pathlib import Path
import unittest

AB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AB))
from harness import BASELINE, DEFAULT_VARIANTS, ExperimentPlan, TrialRecord, compile_report, validate_records, verify_report


def plan():
    return ExperimentPlan("t", DEFAULT_VARIANTS, (0, 1), (0, 1), 80, "mock", "deadbeef")


def records(p):
    out = []
    for vi, v in enumerate(p.variants):
        for seed in p.seeds:
            for level in p.levels:
                out.append(TrialRecord(v.name, seed, level, vi != 2, 10 + vi, vi, 5 if vi != 2 else None, 12, 20 + vi, 1, level, 1))
    return out


class HarnessTests(unittest.TestCase):
    def test_default_variants_are_one_factor(self):
        p = plan()
        self.assertEqual(p.variants[0], BASELINE)
        self.assertEqual(len(p.variants), 5)

    def test_complete_pairing_required(self):
        p = plan()
        rows = records(p)
        validate_records(p, rows)
        with self.assertRaises(ValueError):
            validate_records(p, rows[:-1])
        with self.assertRaises(ValueError):
            validate_records(p, rows + [rows[0]])

    def test_report_is_deterministic_and_tamper_evident(self):
        p = plan()
        a = compile_report(p, records(p))
        b = compile_report(p, list(reversed(records(p))))
        self.assertEqual(a["receipt_sha256"], b["receipt_sha256"])
        self.assertTrue(verify_report(a))
        altered = copy.deepcopy(a)
        altered["records"][0]["actions"] += 1
        self.assertFalse(verify_report(altered))

    def test_mock_authority_never_claims_competition_score(self):
        report = compile_report(plan(), records(plan()))
        self.assertFalse(report["authority"]["competition_score_authorized"])
        self.assertEqual(report["authority"]["evidence_kind"], "mock")

    def test_paired_delta_direction_is_explicit(self):
        report = compile_report(plan(), records(plan()))
        delta = report["paired_against_baseline"]["uniform_random"]
        self.assertGreater(delta["baseline_only_wins"], 0)
        self.assertLess(delta["paired_win_delta"], 0)


if __name__ == "__main__":
    unittest.main()
