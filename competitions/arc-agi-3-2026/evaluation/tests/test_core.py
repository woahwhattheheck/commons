from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from evaluation.core import ExperimentSpec, TrialPair, compile_report, verify_report
from evaluation.manifest import load_manifest, write_manifest


class EvaluationCoreTests(unittest.TestCase):
    def spec(self, evidence="mock"):
        return ExperimentSpec("H2", "probe", "uniform", "info", "score", True,
                              evidence, 80, "abc123", {"x": 1})

    def pairs(self):
        return tuple(TrialPair(i, {"score": i}, {"score": i + 2}, f"d{i}") for i in range(6))

    def test_report_is_deterministic_and_verifiable(self):
        a = compile_report(self.spec(), self.pairs())
        b = compile_report(self.spec(), reversed(self.pairs()))
        self.assertEqual(a, b)
        self.assertTrue(verify_report(a))
        self.assertEqual(a["candidate_wins"], 6)
        self.assertEqual(a["claim_ceiling"], "MOCK_EVIDENCE_ONLY")

    def test_tamper_fails(self):
        report = compile_report(self.spec(), self.pairs())
        bad = copy.deepcopy(report)
        bad["trials"][0]["candidate_metrics"]["score"] = 999
        self.assertFalse(verify_report(bad))

    def test_nonfinite_metric_fails(self):
        with self.assertRaises(ValueError):
            TrialPair(1, {"score": 1.0}, {"score": float("nan")}, "x")

    def test_duplicate_seed_fails(self):
        pair = TrialPair(1, {"score": 1}, {"score": 2}, "x")
        with self.assertRaises(ValueError):
            compile_report(self.spec(), (pair, pair))

    def test_metric_key_mismatch_fails(self):
        with self.assertRaises(ValueError):
            TrialPair(1, {"a": 1}, {"b": 1}, "x")

    def test_manifest_round_trip_and_reject_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            specs = (self.spec(),)
            write_manifest(path, specs)
            self.assertEqual(load_manifest(path), specs)
            obj = json.loads(path.read_text())
            obj["extra"] = True
            path.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):
                load_manifest(path)

    def test_evidence_class_is_closed_set(self):
        with self.assertRaises(ValueError):
            self.spec("leaderboard")


if __name__ == "__main__":
    unittest.main()
