# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from certified_report import build_report


def report(rows):
    return {"games": rows}


def game(opponent, seed, seat, scores, trace):
    return {
        "status": "complete",
        "failure": None,
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "scores": scores,
        "trace_sha256": trace,
    }


class CertifiedReportTests(unittest.TestCase):
    def write(self, root, name, rows):
        path = root / name
        path.write_text(json.dumps(report(rows)))
        return path

    def test_rejects_transplant_when_certified_is_exact_control(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control_rows = [
                game("arlene", 1, 0, [100, 90], "c0"),
                game("arlene", 1, 1, [90, 100], "c1"),
            ]
            unsafe_rows = [
                game("arlene", 1, 0, [120, 90], "u0"),
                game("arlene", 1, 1, [90, 120], "u1"),
            ]
            result = build_report(
                self.write(root, "control.json", control_rows),
                self.write(root, "unsafe.json", unsafe_rows),
                self.write(root, "certified.json", control_rows),
                source_seat=0,
            )
            self.assertEqual(result["verdict"], "CERTIFICATE_REJECTS_TRANSPLANT")
            self.assertTrue(result["off_seat_exact_fallback"])

    def test_source_seat_safe_activation_survives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control_rows = [
                game("arlene", 1, 0, [100, 90], "c0"),
                game("arlene", 1, 1, [90, 100], "c1"),
            ]
            unsafe_rows = [
                game("arlene", 1, 0, [120, 90], "u0"),
                game("arlene", 1, 1, [90, 120], "u1"),
            ]
            certified_rows = [
                game("arlene", 1, 0, [110, 90], "g0"),
                game("arlene", 1, 1, [90, 100], "c1"),
            ]
            result = build_report(
                self.write(root, "control.json", control_rows),
                self.write(root, "unsafe.json", unsafe_rows),
                self.write(root, "certified.json", certified_rows),
                source_seat=0,
            )
            self.assertEqual(result["verdict"], "CERTIFIED_SURVIVOR")
            self.assertTrue(result["source_seat_activated"])


if __name__ == "__main__":
    unittest.main()
