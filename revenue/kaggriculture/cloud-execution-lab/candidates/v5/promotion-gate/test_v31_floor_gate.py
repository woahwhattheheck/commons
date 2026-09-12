#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

import v31_floor_gate as gate

CID = "v5c:" + "c" * 64
CONTROL = "v5c:" + "a" * 64
CAND_ARCHIVE = "d" * 64
ENGINE = "engine-pinned"
PACK = "frontier-pack"


def panels(*, control_delta: int = 1, floor_delta: int = 2):
    economics_cells = []
    floor_cells = []
    for opponent in ("apex", "arlene"):
        for seed in (101, 102, 103, 104):
            for seat in (0, 1):
                control_margin = 1000 + seed + seat
                candidate_margin = control_margin + control_delta
                floor_margin = candidate_margin - floor_delta
                economics_cells.append({
                    "opponent_id": opponent, "seed": seed, "seat": seat,
                    "control_own": control_margin, "control_rival": 0,
                    "candidate_own": candidate_margin, "candidate_rival": 0,
                })
                floor_cells.append({
                    "opponent_id": opponent, "seed": seed, "seat": seat,
                    "floor_own": floor_margin, "floor_rival": 0,
                    "candidate_own": candidate_margin, "candidate_rival": 0,
                })
    economics = {
        "schema": "titan-v5-paired-economics/v3",
        "control_id": CONTROL,
        "candidate_id": CID,
        "engine_id": ENGINE,
        "opponent_pack_id": PACK,
        "control_archive_sha256": "b" * 64,
        "candidate_archive_sha256": CAND_ARCHIVE,
        "cells": economics_cells,
    }
    floor = {
        "schema": gate.SCHEMA,
        "floor_id": gate.FLOOR_ID,
        "candidate_id": CID,
        "engine_id": ENGINE,
        "opponent_pack_id": PACK,
        "floor_archive_sha256": gate.FLOOR_ARCHIVE_SHA256,
        "candidate_archive_sha256": CAND_ARCHIVE,
        "cells": floor_cells,
    }
    return economics, floor


class V31FloorGateTests(unittest.TestCase):
    def validate(self, economics, floor):
        return gate.validate_report(
            floor,
            economics,
            candidate_id=CID,
            engine_id=ENGINE,
            opponent_pack_id=PACK,
            candidate_archive_sha256=CAND_ARCHIVE,
        )

    def test_valid_exact_floor_passes_and_binds_topology(self):
        economics, floor = panels()
        receipt = self.validate(economics, floor)
        self.assertEqual(receipt["classification"], "PASS")
        self.assertTrue(receipt["release_ready"])
        self.assertEqual(receipt["floor_id"], gate.FLOOR_ID)
        self.assertEqual(receipt["floor_archive_sha256"], gate.FLOOR_ARCHIVE_SHA256)
        self.assertEqual(receipt["sum_margin_delta_vs_v31"], 32)
        self.assertEqual(receipt["opponent_count"], 2)
        self.assertEqual(receipt["cell_count"], 16)

    def test_candidate_can_beat_v4_and_still_fail_v31_floor(self):
        economics, floor = panels(control_delta=1, floor_delta=-1)
        with self.assertRaisesRegex(gate.FloorError, "strictly outperform submitted V3.1"):
            self.validate(economics, floor)

    def test_tie_with_v31_is_not_enough(self):
        economics, floor = panels(control_delta=10, floor_delta=0)
        with self.assertRaisesRegex(gate.FloorError, "strictly outperform submitted V3.1"):
            self.validate(economics, floor)

    def test_stale_floor_archive_rejected(self):
        economics, floor = panels()
        floor["floor_archive_sha256"] = "0" * 64
        with self.assertRaisesRegex(gate.FloorError, "exact submitted authority"):
            self.validate(economics, floor)

    def test_swapped_floor_identity_rejected(self):
        economics, floor = panels()
        floor["floor_id"] = "kaggle-submission:56182437"
        with self.assertRaisesRegex(gate.FloorError, "floor_id must be exact authority"):
            self.validate(economics, floor)

    def test_omitted_floor_score_rejected(self):
        economics, floor = panels()
        del floor["cells"][0]["floor_own"]
        with self.assertRaisesRegex(gate.FloorError, "exact raw score keys"):
            self.validate(economics, floor)

    def test_topology_mismatch_rejected(self):
        economics, floor = panels()
        floor["cells"][0]["seed"] += 999
        with self.assertRaisesRegex(gate.FloorError, "topology differs"):
            self.validate(economics, floor)

    def test_candidate_score_mismatch_rejected(self):
        economics, floor = panels()
        floor["cells"][0]["candidate_own"] += 1
        with self.assertRaisesRegex(gate.FloorError, "candidate scores differ"):
            self.validate(economics, floor)

    def test_candidate_archive_mismatch_rejected(self):
        economics, floor = panels()
        floor["candidate_archive_sha256"] = "e" * 64
        with self.assertRaisesRegex(gate.FloorError, "approved-new"):
            self.validate(economics, floor)

    def test_unsorted_or_duplicate_cells_rejected(self):
        economics, floor = panels()
        floor["cells"][0], floor["cells"][1] = floor["cells"][1], floor["cells"][0]
        with self.assertRaisesRegex(gate.FloorError, "topology differs"):
            self.validate(economics, floor)

    def test_input_is_not_mutated(self):
        economics, floor = panels()
        before_e = copy.deepcopy(economics)
        before_f = copy.deepcopy(floor)
        self.validate(economics, floor)
        self.assertEqual(economics, before_e)
        self.assertEqual(floor, before_f)


if __name__ == "__main__":
    unittest.main()
