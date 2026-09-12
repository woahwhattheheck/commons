# SPDX-License-Identifier: Apache-2.0
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import engagement_fingerprint as ef


class EngagementFingerprintTests(unittest.TestCase):
    def test_mapping_order_is_canonical(self):
        left = {"b": [1, True], "a": {"x": -0.0}}
        right = {"a": {"x": -0.0}, "b": [1, True]}
        self.assertEqual(ef.fingerprint(left), ef.fingerprint(right))

    def test_typed_scalars_do_not_collapse(self):
        self.assertNotEqual(ef.fingerprint(True), ef.fingerprint(1))
        self.assertNotEqual(ef.fingerprint(-0.0), ef.fingerprint(0.0))
        self.assertNotEqual(ef.fingerprint(["1"]), ef.fingerprint([1]))

    def test_non_finite_values_fail_closed(self):
        with self.assertRaises(ef.FingerprintError):
            ef.fingerprint(float("nan"))
        with self.assertRaises(ef.FingerprintError):
            ef.fingerprint(float("inf"))

    def test_noop_requires_threshold(self):
        tracker = ef.EngagementTracker(noop_threshold=3)
        for step in range(2):
            tracker.observe(
                {"seed": 5, "seat": 0, "step": step, "phase": "unit"},
                [["MOVE", 1]],
                [["MOVE", 1]],
            )
        self.assertEqual("INSUFFICIENT", tracker.summary()["classification"])
        self.assertFalse(tracker.observed_noop)

        tracker.observe(
            {"seed": 5, "seat": 0, "step": 2, "phase": "unit"},
            [["MOVE", 1]],
            [["MOVE", 1]],
        )
        self.assertEqual("NO_OP_OBSERVED", tracker.summary()["classification"])
        self.assertTrue(tracker.observed_noop)

    def test_first_divergence_and_sequence_fingerprints(self):
        tracker = ef.EngagementTracker(noop_threshold=2)
        tracker.observe(
            {"seed": 7, "seat": 1, "step": 10, "phase": "market"},
            [["SELL", "MILK", 1]],
            [["SELL", "MILK", 1]],
        )
        tracker.observe(
            {"seed": 7, "seat": 1, "step": 11, "phase": "market"},
            [["SELL", "MILK", 1]],
            [["SELL", "MILK", 2]],
        )
        summary = tracker.summary()
        self.assertEqual("ENGAGED", summary["classification"])
        self.assertEqual(1, summary["divergence_count"])
        self.assertEqual(0.5, summary["engagement_rate"])
        self.assertEqual(2, summary["first_divergence"]["observation"])
        self.assertEqual(11, summary["first_divergence"]["key"]["step"])
        self.assertNotEqual(
            summary["control_sequence_fingerprint"],
            summary["candidate_sequence_fingerprint"],
        )

    def test_duplicate_alignment_key_fails_closed(self):
        tracker = ef.EngagementTracker()
        row = {"seed": 1, "seat": 0, "step": 4, "phase": "unit"}
        tracker.observe(row, [], [])
        with self.assertRaises(ef.AlignmentError):
            tracker.observe(row, [], [])

    def test_missing_alignment_field_fails_closed(self):
        with self.assertRaises(ef.AlignmentError):
            ef.compare_rows(
                [{"seed": 1, "seat": 0, "step": 0, "control": [], "candidate": []}]
            )

    def test_custom_payload_fields(self):
        report = ef.compare_rows(
            [
                {
                    "seed": 1,
                    "seat": 0,
                    "step": 0,
                    "phase": "unit",
                    "baseline_action": ["WAIT"],
                    "variant_action": ["MOVE", 2],
                }
            ],
            control_field="baseline_action",
            candidate_field="variant_action",
            noop_threshold=1,
        )
        self.assertEqual("ENGAGED", report["classification"])

    def test_cli_emits_machine_readable_report(self):
        rows = [
            {
                "seed": 9,
                "seat": 0,
                "step": step,
                "phase": "unit",
                "control": ["WAIT"],
                "candidate": ["WAIT"],
            }
            for step in range(3)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "paired.jsonl"
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(Path(ef.__file__)),
                    str(path),
                    "--noop-threshold",
                    "3",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        report = json.loads(proc.stdout)
        self.assertEqual("NO_OP_OBSERVED", report["classification"])
        self.assertEqual(3, report["observations"])

    def test_cli_rejects_duplicate_key(self):
        row = {
            "seed": 9,
            "seat": 0,
            "step": 0,
            "phase": "unit",
            "control": ["WAIT"],
            "candidate": ["WAIT"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "paired.jsonl"
            path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(Path(ef.__file__)), str(path)],
                capture_output=True,
                text=True,
            )
        self.assertEqual(2, proc.returncode)
        self.assertIn("duplicate matched key", proc.stderr)


if __name__ == "__main__":
    unittest.main()
