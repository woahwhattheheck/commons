# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from certified_report import CertifiedReportError, build_report

DIAG_SCHEMA = "titan-v3-s13-certified-activation/v1"
CAPTURE_SCHEMA = "titan-v3-s13-activation-capture-receipt/v1"
CANDIDATE_SHA = "c" * 64
WRAPPER_SHA = "d" * 64


def report(rows, *, certified=False):
    value = {"games": rows}
    if certified:
        value["candidate"] = {"sha256": WRAPPER_SHA}
    return value


def game(opponent, seed, seat, scores, trace, *, activation_steps=None):
    row = {
        "status": "complete",
        "failure": None,
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "scores": scores,
        "trace_sha256": trace,
    }
    if activation_steps is not None:
        diagnostics = {
            "schema": DIAG_SCHEMA,
            "target_name": "candidate.py",
            "target_sha256": CANDIDATE_SHA,
            "source_seat": 0,
            "arm_id": "fixture-arm",
            "policy": {
                "source_seat": 0,
                "start_step": 24,
                "active": True,
                "handoff_step": None if seat == 0 else 24,
                "handoff_reason": None if seat == 0 else "source_seat_mismatch",
                "certificate_checks": len(activation_steps),
                "certificate_matches": len(activation_steps),
                "activation_count": len(activation_steps),
                "activation_steps": activation_steps,
            },
        }
        raw = (
            json.dumps(
                diagnostics, sort_keys=True, separators=(",", ":"), allow_nan=False
            )
            + "\n"
        ).encode()
        actors = [{}, {}]
        actors[seat] = {
            "candidate_diagnostics": diagnostics,
            "candidate_diagnostics_sha256": hashlib.sha256(raw).hexdigest(),
            "candidate_diagnostics_bytes": len(raw),
        }
        row["actors"] = actors
    return row


class CertifiedReportTests(unittest.TestCase):
    def write(self, root, name, value):
        path = root / name
        path.write_text(json.dumps(value))
        return path

    def capture(self, root):
        return self.write(
            root,
            "capture.json",
            {
                "schema": CAPTURE_SCHEMA,
                "candidate_name": "candidate.py",
                "candidate_sha256": CANDIDATE_SHA,
                "wrapper_name": "wrapper.py",
                "wrapper_sha256": WRAPPER_SHA,
                "marker_name": ".marker",
                "diagnostic_name": "diagnostics.json",
                "diagnostic_schema": DIAG_SCHEMA,
            },
        )

    def run_report(self, root, certified_rows):
        control_rows = [
            game("arlene", 1, 0, [100, 90], "c0"),
            game("arlene", 1, 1, [90, 100], "c1"),
        ]
        unsafe_rows = [
            game("arlene", 1, 0, [120, 90], "u0"),
            game("arlene", 1, 1, [90, 120], "u1"),
        ]
        return build_report(
            self.write(root, "control.json", report(control_rows)),
            self.write(root, "unsafe.json", report(unsafe_rows)),
            self.write(root, "certified.json", report(certified_rows, certified=True)),
            source_seat=0,
            capture_receipt_path=self.capture(root),
        )

    def test_rejects_transplant_when_authenticated_diagnostics_show_no_activation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [
                game("arlene", 1, 0, [100, 90], "c0", activation_steps=[]),
                game("arlene", 1, 1, [90, 100], "c1", activation_steps=[]),
            ]
            result = self.run_report(root, rows)
            self.assertEqual(result["verdict"], "CERTIFICATE_REJECTS_TRANSPLANT")
            self.assertFalse(result["source_seat_activated"])
            self.assertEqual(
                result["activation_evidence"]["source_activation_count"], 0
            )

    def test_source_seat_survivor_requires_authenticated_activation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [
                game("arlene", 1, 0, [110, 90], "g0", activation_steps=[24, 25]),
                game("arlene", 1, 1, [90, 100], "c1", activation_steps=[]),
            ]
            result = self.run_report(root, rows)
            self.assertEqual(result["verdict"], "CERTIFIED_SURVIVOR")
            self.assertTrue(result["source_seat_activated"])
            self.assertEqual(
                result["activation_evidence"]["source_activation_count"], 2
            )
            self.assertTrue(
                result["activation_evidence"]["activation_trace_consistent"]
            )

    def test_trace_change_without_authenticated_activation_is_hold_not_survivor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [
                game("arlene", 1, 0, [110, 90], "g0", activation_steps=[]),
                game("arlene", 1, 1, [90, 100], "c1", activation_steps=[]),
            ]
            result = self.run_report(root, rows)
            self.assertEqual(result["verdict"], "CERTIFIED_HOLD")
            self.assertFalse(result["source_seat_activated"])
            self.assertFalse(
                result["activation_evidence"]["activation_trace_consistent"]
            )

    def test_missing_candidate_diagnostics_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = game("arlene", 1, 0, [100, 90], "c0")
            missing["actors"] = [{"candidate_diagnostics": None}, {}]
            rows = [
                missing,
                game("arlene", 1, 1, [90, 100], "c1", activation_steps=[]),
            ]
            with self.assertRaisesRegex(
                CertifiedReportError, "candidate diagnostics are absent"
            ):
                self.run_report(root, rows)

    def test_wrapper_fingerprint_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [
                game("arlene", 1, 0, [100, 90], "c0", activation_steps=[]),
                game("arlene", 1, 1, [90, 100], "c1", activation_steps=[]),
            ]
            control_rows = [
                game("arlene", 1, 0, [100, 90], "c0"),
                game("arlene", 1, 1, [90, 100], "c1"),
            ]
            unsafe_rows = list(control_rows)
            certified = report(rows, certified=True)
            certified["candidate"]["sha256"] = "e" * 64
            with self.assertRaisesRegex(
                CertifiedReportError, "wrapper SHA-256 mismatch"
            ):
                build_report(
                    self.write(root, "control.json", report(control_rows)),
                    self.write(root, "unsafe.json", report(unsafe_rows)),
                    self.write(root, "certified.json", certified),
                    source_seat=0,
                    capture_receipt_path=self.capture(root),
                )


if __name__ == "__main__":
    unittest.main()
