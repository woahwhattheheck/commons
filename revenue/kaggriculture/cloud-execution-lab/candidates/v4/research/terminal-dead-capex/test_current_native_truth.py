#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import current_native_truth as truth
import deadcap_oracle as donor

CLOUD = HERE.parents[3]
TAPES = CLOUD / "candidates" / "v4" / "donor" / "overlay" / "r01_tapes.py"
ENGINE = CLOUD / "reference" / "engine" / "kaggriculture.py"


class DeadcapCurrentNativeTruthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tapes = donor.load_tapes(TAPES)
        cls.engine = donor.load_engine(ENGINE)

    def test_current_sources_are_authenticated_before_probe(self):
        receipt = truth.authenticated_single_cell_probe(
            CLOUD, self.engine, self.tapes, seed=0, rival_tape=0
        )
        self.assertEqual(receipt["source_auth"], {
            "main_blob": donor.CURRENT_MAIN_BLOB,
            "runtime_blob": donor.CURRENT_RUNTIME_BLOB,
            "config_blob": donor.CURRENT_CONFIG_BLOB,
        })
        self.assertFalse(receipt["general_dead_seed_engagement_cold_proven"])
        self.assertEqual(
            receipt["disposition"],
            "ONE_CELL_DONOR_WITNESS_ABSENT_GENERAL_ENGAGEMENT_UNMEASURED",
        )
        self.assertFalse(receipt["probe"]["emits_witness"])

    def test_truth_scope_names_exact_measured_cell(self):
        receipt = truth.authenticated_single_cell_probe(
            CLOUD, self.engine, self.tapes, seed=0, rival_tape=0
        )
        self.assertEqual(receipt["scope"], {
            "seat": 0,
            "seed": 0,
            "rival_tape": 0,
            "step": 284,
            "detection": "exact donor row equality only",
        })

    def test_runtime_drift_fails_before_replay(self):
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            for name in ("main.py", "titan_runtime.py", "TITAN-CONFIG.json"):
                shutil.copyfile(CLOUD / name, tmp / name)
            with (tmp / "main.py").open("ab") as fh:
                fh.write(b"\n# deliberate DEADCAP custody drift\n")
            with self.assertRaisesRegex(RuntimeError, "current production drift"):
                # engine/tapes are deliberately unusable sentinels: exact-source
                # authentication must reject before inherited replay touches them.
                truth.authenticated_single_cell_probe(tmp, object(), object())


if __name__ == "__main__":
    unittest.main(verbosity=2)
