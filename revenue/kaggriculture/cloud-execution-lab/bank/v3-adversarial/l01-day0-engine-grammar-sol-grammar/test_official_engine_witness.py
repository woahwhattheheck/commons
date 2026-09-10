# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import official_engine_witness as witness  # noqa: E402


class OfficialEngineWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        override = os.environ.get("TITAN_ARCHIVE")
        cls.archive = Path(override) if override else witness.default_archive()
        if not cls.archive.is_file():
            raise unittest.SkipTest(f"TITAN archive unavailable: {cls.archive}")
        cls.result = witness.run_witness(cls.archive)

    def test_exact_engine_bytes_are_bound(self):
        self.assertEqual(self.result["engine_sha256"], dict(sorted(witness.ENGINE_SHA256.items())))

    def test_control_executes_wheat_thirteen(self):
        self.assertEqual(self.result["control"]["money"], 2643)
        self.assertEqual(self.result["control"]["shed"], {"WHEAT": 13})
        self.assertEqual(self.result["control"]["wheat_market_inventory"], 9986)

    def test_shipped_basket_executes_only_wheat_two(self):
        self.assertEqual(self.result["shipped"]["money"], 2948)
        self.assertEqual(self.result["shipped"]["shed"], {"WHEAT": 2})
        self.assertEqual(self.result["shipped"]["seeds"], {})
        self.assertEqual(self.result["shipped"]["wheat_market_inventory"], 9997)
        self.assertEqual(self.result["control_minus_shipped_wheat"], 11)

    def test_source_certificate_names_exact_five_noops(self):
        issues = self.result["source_certificate"]["issues"]
        unsupported = [row for row in issues if row["code"] == "unsupported_product"]
        self.assertEqual(len(unsupported), 5)
        self.assertEqual([row["index"] for row in unsupported], [0, 1, 2, 3, 4])

    def test_witness_is_deterministic(self):
        again = witness.run_witness(self.archive)
        self.assertEqual(self.result, again)


if __name__ == "__main__":
    unittest.main(verbosity=2)
