#!/usr/bin/env python3
"""Hermetic coverage for LotLens impact --paths summary (FORGE slice)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLI = ROOT / "lotlens" / "lotlens.py"
FIXTURE = ROOT / "lotlens" / "fixtures" / "synthetic_pilot"


class PathsSummaryTests(unittest.TestCase):
    def run_cli(self, *args):
        proc = subprocess.run(
            [sys.executable, str(CLI), *args],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def test_paths_summary_replaces_arrays_with_hop_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = str(Path(tmp) / "ws")
            self.run_cli("-w", ws, "import", str(FIXTURE), "--label", "pilot")
            out = self.run_cli(
                "-w",
                ws,
                "impact",
                "sup-acme/lot/LOT-CITRIC-01",
                "--brief",
                "--paths",
                "summary",
            )
            self.assertEqual(out.get("paths"), "summary")
            self.assertEqual(out["counts"]["KNOWN_AFFECTED"], 16)
            citric_a = next(a for a in out["affected"] if a["key"] == "sup-acme/lot/LOT-CITRIC-01A")
            self.assertNotIn("path", citric_a)
            self.assertEqual(len(citric_a["path_summary"]), 1)
            line = citric_a["path_summary"][0]
            self.assertIn("sup-acme/lot/LOT-CITRIC-01 -split-> sup-acme/lot/LOT-CITRIC-01A", line)
            self.assertRegex(line, r"splits\.csv:\d+")
            self.assertEqual(citric_a.get("material"), "citric acid")
            p4 = next(a for a in out["affected"] if a["key"] == "pilot-plant/batch/BATCH-P4")
            self.assertEqual(len(p4["path_summary"]), 4)
            self.assertTrue(
                p4["path_summary"][-1].startswith(
                    "pilot-plant/batch/BATCH-P3 -rework-> pilot-plant/batch/BATCH-P4"
                )
            )
            self.assertIn("rework.csv:2", p4["path_summary"][-1])
            full_brief = self.run_cli("-w", ws, "impact", "sup-acme/lot/LOT-CITRIC-01", "--brief")
            self.assertNotIn("paths", full_brief)
            self.assertNotIn("path_summary", full_brief["affected"][0])


if __name__ == "__main__":
    unittest.main()
