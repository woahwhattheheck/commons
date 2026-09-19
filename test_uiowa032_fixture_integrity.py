"""Root-discovery bridge for the UIOWA-032 fixture-hygiene repair.

Child transcripts preserve optional PDF skips rather than calling them passes.
Production extraction stays with its existing source-fidelity carrier.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

LANE = Path(__file__).resolve().parent / "revenue" / "uiowa_rfq_18649_document_extraction"


class UIOWA032FixtureIntegrityTests(unittest.TestCase):
    def test_component_normal_and_optimized(self):
        for flags in ([], ["-O"]):
            with self.subTest(flags=flags):
                command = [sys.executable, *flags, "-m", "unittest", "-v",
                           "test_extract", "test_fixture_integrity"]
                result = subprocess.run(command, cwd=LANE, capture_output=True,
                                        text=True, encoding="utf-8", timeout=90)
                transcript = result.stdout + result.stderr
                print("UIOWA-032 mode=" + ("optimized" if flags else "normal"))
                print(transcript)
                self.assertEqual(result.returncode, 0, transcript)
                self.assertIn("Ran 16 tests", transcript)


if __name__ == "__main__":
    unittest.main()
