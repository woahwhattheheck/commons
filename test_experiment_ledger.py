#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from host import experiment_ledger as el  # noqa: E402

OBJ = {"metric": "margin_delta", "direction": "maximize", "unit": "points"}


def declared():
    return el.add_hypothesis(el.empty_ledger(), "H3c", "goose rescue improves margin", OBJ, ["titan"])


class ExperimentLedgerTests(unittest.TestCase):
    def test_declaration_has_all_four_benches_side_by_side(self):
        ledger = declared()
        row = ledger["hypotheses"]["H3c"]
        self.assertEqual(tuple(row["benches"]), el.BENCHES)
        self.assertTrue(all(v["state"] == "NOT_EXECUTED" for v in row["benches"].values()))
        self.assertTrue(all(v["sample_size"] is None for v in row["benches"].values()))

    def test_hypothesis_declaration_is_idempotent_but_immutable(self):
        one = declared()
        two = el.add_hypothesis(one, "H3c", "goose rescue improves margin", OBJ, ["titan"])
        self.assertEqual(one, two)
        with self.assertRaisesRegex(ValueError, "different declaration"):
            el.add_hypothesis(one, "H3c", "changed claim", OBJ)

    def test_record_keeps_sample_size_metrics_panel_and_evidence(self):
        ledger = el.record_bench(declared(), "H3c", "small_gate", {
            "state": "COMPLETE",
            "sample_size": 32,
            "metrics": {"mean_delta": 12.5, "wins": 18},
            "evidence": ["run:123", "sha256:abcd"],
            "panel": "seeds-6101-6132",
        })
        row = ledger["hypotheses"]["H3c"]["benches"]["small_gate"]
        self.assertEqual(row["sample_size"], 32)
        self.assertEqual(row["metrics"]["mean_delta"], 12.5)
        self.assertEqual(row["panel"], "seeds-6101-6132")

    def test_terminal_evidence_cannot_be_rewritten(self):
        base = declared()
        done = el.record_bench(base, "H3c", "field_gate", {
            "state": "COMPLETE", "sample_size": 64, "metrics": {"mean_delta": 3.0}, "evidence": ["run:1"]
        })
        with self.assertRaisesRegex(ValueError, "terminal bench evidence is immutable"):
            el.record_bench(done, "H3c", "field_gate", {
                "state": "COMPLETE", "sample_size": 64, "metrics": {"mean_delta": 4.0}, "evidence": ["run:1"]
            })

    def test_running_sample_size_cannot_decrease(self):
        run = el.record_bench(declared(), "H3c", "frozen_panel", {
            "state": "RUNNING", "sample_size": 20, "metrics": {}, "evidence": ["run:2"]
        })
        with self.assertRaisesRegex(ValueError, "cannot decrease"):
            el.record_bench(run, "H3c", "frozen_panel", {
                "state": "RUNNING", "sample_size": 19, "metrics": {}, "evidence": ["run:2"]
            })

    def test_not_executed_has_unknown_sample_not_fake_zero(self):
        with self.assertRaisesRegex(ValueError, "must be null"):
            el.normalize_bench({"state": "NOT_EXECUTED", "sample_size": 0})

    def test_terminal_requires_positive_non_bool_sample(self):
        for value in (0, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    el.normalize_bench({"state": "COMPLETE", "sample_size": value})

    def test_metrics_and_objective_reject_nonfinite_or_bool(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            el.normalize_bench({"state": "RUNNING", "sample_size": 1, "metrics": {"x": float("nan")}})
        with self.assertRaisesRegex(ValueError, "finite"):
            el.normalize_objective({"metric": "x", "direction": "maximize", "unit": "u", "threshold": True})

    def test_strict_loader_rejects_duplicate_keys_and_nonfinite(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            el.loads_strict('{"schema":"x","schema":"y"}')
        with self.assertRaisesRegex(ValueError, "non-finite"):
            el.loads_strict('{"x":NaN}')

    def test_validator_requires_exact_four_benches(self):
        row = declared()["hypotheses"]["H3c"]
        bad = json.loads(json.dumps(row))
        del bad["benches"]["field_gate"]
        value = {"schema": el.SCHEMA, "hypotheses": {"H3c": bad}}
        with self.assertRaisesRegex(ValueError, "exactly"):
            el.validate_ledger(value)

    def test_cli_add_record_validate_get_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.json")
            script = os.path.join(os.path.dirname(__file__), "host", "experiment_ledger.py")
            base = [sys.executable, script]
            add = subprocess.run(base + ["add", path, "H3c", "--statement", "claim", "--objective-json", json.dumps(OBJ)], text=True, capture_output=True)
            self.assertEqual(add.returncode, 0, add.stderr)
            record = subprocess.run(base + ["record", path, "H3c", "forensic_estimate", "--record-json", json.dumps({"state": "COMPLETE", "sample_size": 8, "metrics": {"mean_delta": 1.5}, "evidence": ["review:7"]})], text=True, capture_output=True)
            self.assertEqual(record.returncode, 0, record.stderr)
            validate = subprocess.run(base + ["validate", path], text=True, capture_output=True)
            self.assertEqual(validate.returncode, 0, validate.stderr)
            get = subprocess.run(base + ["get", path, "H3c"], text=True, capture_output=True)
            self.assertEqual(get.returncode, 0, get.stderr)
            self.assertEqual(json.loads(get.stdout)["benches"]["forensic_estimate"]["sample_size"], 8)


if __name__ == "__main__":
    unittest.main()
