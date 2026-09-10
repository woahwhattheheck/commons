# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from materialize_pressure_certificate import git_blob_sha1
from official_plateau_witness import SCHEMA, build_witness


MECHANICS = '''def market_price(item, inventory, params=None):
    del params
    curves = {
        "TOMATO": {9999: 60, 10000: 60, 10001: 57},
        "MILK": {9999: 169, 10000: 160, 10001: 158},
    }
    return curves[item][inventory]
'''


class OfficialPlateauWitnessTests(unittest.TestCase):
    def test_exact_lockstep_witness(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "mechanics.py"
            path.write_text(MECHANICS, encoding="utf-8")
            witness = build_witness(
                path,
                expected_git_blob_sha1=git_blob_sha1(path.read_bytes()),
            )
        self.assertEqual(witness["schema"], SCHEMA)
        self.assertEqual(witness["proxy_order"], ["MILK", "TOMATO"])
        self.assertEqual(witness["certified_order"], ["TOMATO", "MILK"])
        self.assertEqual(
            witness["proxy_effect"],
            {"own": -3, "rival": 3, "margin": -6},
        )
        self.assertEqual(
            [row["status"] for row in witness["certificates"]],
            ["EXPOSED", "EXPOSED"],
        )

    def test_mechanics_blob_drift_rejects(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "mechanics.py"
            path.write_text(MECHANICS, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mechanics git blob drift"):
                build_witness(path, expected_git_blob_sha1="0" * 40)

    def test_curve_drift_rejects(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "mechanics.py"
            path.write_text(MECHANICS.replace("10001: 57", "10001: 58"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "public curve witness drifted"):
                build_witness(
                    path,
                    expected_git_blob_sha1=git_blob_sha1(path.read_bytes()),
                )


if __name__ == "__main__":
    unittest.main()
