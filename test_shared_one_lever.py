#!/usr/bin/env python3
"""The shared-one lever is a measurement, not a Slack essay."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
from shared_one_lever import (
    EXCERPT_DIR,
    MLC_FILE_LEVELS,
    census,
    excerpt_kind,
    list_excerpts,
    measure_path,
)

LVIN = os.path.join(EXCERPT_DIR, "muhl_lvin.mno")
ESNR = os.path.join(EXCERPT_DIR, "muhl_esnr.mno")
IMMN = os.path.join(EXCERPT_DIR, "muhl_immn.mno")
HOPF_SDMK = os.path.join(EXCERPT_DIR, "muhl_chimera_hopf_sdmk.mno")

# Measured unique-byte counts for landed chimera slices. Padding any of
# these to 256 would fabricate MLC on a small excerpt. Do not remint.
CHIMERA_FILE_LEVELS = {
    "muhl_chimera_flow_stig.mno": 31,
    "muhl_chimera_grbn_socr.mno": 33,
    "muhl_chimera_hopf_sdmk.mno": 34,
    "muhl_chimera_immn_hdvs.mno": 32,
    "muhl_chimera_pots_dmb.mno": 33,
    "muhl_chimera_socr_stig.mno": 30,
    "muhl_chimera_tset_hdvs.mno": 36,
    "muhl_chimera_pred_rgcg.mno": 37,
    "muhl_chimera_lvin_synd.mno": 34,
}


class TestSharedOneLever(unittest.TestCase):
    def test_const1_is_a_written_one_on_every_excerpt(self):
        paths = list_excerpts(EXCERPT_DIR)
        self.assertGreaterEqual(len(paths), 19, "PLUMB 1-19 excerpts missing")
        data = census(paths)
        self.assertEqual(data["titan"], "NOT_WRITTEN")
        self.assertEqual(data["const1_written"], data["excerpts"])
        self.assertGreaterEqual(data["const1_shared"], 16)
        self.assertGreaterEqual(data["mlc_excerpts"], 19)
        for row in data["rows"]:
            self.assertEqual(row["const0_written"], 0, row["path"])
            self.assertEqual(row["const1_written"], 1, row["path"])
            self.assertTrue(row["unique_out_eq_gates"], row["path"])
            self.assertEqual(row["plane_levels"], 2, row["path"])
            self.assertGreater(row["share_factor"], 1.0, row["path"])
            name = os.path.basename(row["path"])
            kind = row.get("kind") or excerpt_kind(row["path"])
            if kind == "chimera":
                self.assertLess(row["file_levels"], MLC_FILE_LEVELS, name)
                self.assertGreater(row["file_levels"], 1, name)
                if name in CHIMERA_FILE_LEVELS:
                    self.assertEqual(
                        row["file_levels"],
                        CHIMERA_FILE_LEVELS[name],
                        "chimera %s was reminted or padded" % name,
                    )
            else:
                self.assertEqual(kind, "plumb_full", name)
                self.assertEqual(row["file_levels"], MLC_FILE_LEVELS, name)

    def test_organ21_hopf_sdmk_file_levels_is_34_not_256(self):
        self.assertTrue(os.path.isfile(HOPF_SDMK), "organ 21 excerpt missing")
        self.assertEqual(excerpt_kind(HOPF_SDMK), "chimera")
        row = measure_path(HOPF_SDMK)
        self.assertEqual(row["kind"], "chimera")
        self.assertEqual(row["n_gate"], 22)
        self.assertEqual(row["file_levels"], 34)
        self.assertNotEqual(row["file_levels"], MLC_FILE_LEVELS)
        self.assertEqual(row["plane_levels"], 2)
        self.assertEqual(row["const1_written"], 1)

    def test_lvin_one_written_one_feeds_1901_gates(self):
        self.assertTrue(os.path.isfile(LVIN), "muhl_lvin.mno is the densest shared-one excerpt")
        row = measure_path(LVIN)
        self.assertEqual(row["magic"], "MUHLLVIN")
        self.assertEqual(row["n_gate"], 2368)
        self.assertEqual(row["const1_addr"], 541)
        self.assertEqual(row["const1_written"], 1)
        self.assertEqual(row["share1"], 1901)
        self.assertGreater(row["share_factor"], 8.0)
        self.assertEqual(row["hottest_addr"], 541)
        self.assertEqual(row["hottest_fan"], 1901)
        self.assertEqual(row["kind"], "plumb_full")
        self.assertEqual(row["file_levels"], MLC_FILE_LEVELS)

    def test_esnr_and_immn_overlap_stay_on_the_written_charge(self):
        esnr = measure_path(ESNR)
        immn = measure_path(IMMN)
        self.assertEqual(esnr["share1"], 4132)
        self.assertEqual(esnr["share0"], 12288)
        self.assertEqual(immn["hottest_addr"], 36)
        self.assertEqual(immn["hottest_fan"], 14391)
        self.assertEqual(immn["share1"], 2249)


if __name__ == "__main__":
    unittest.main()
