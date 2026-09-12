#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import champion_floor as cf

V4_ARCHIVE = "4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b"
CANDIDATE_ARCHIVE = "1" * 64
CANDIDATE_ID = "v5c:" + "2" * 64
ENGINE = "official-engine:test"
PACK = "frontier:test"


def make_report(delta: int = 10) -> dict:
    cells = []
    for opponent in ("apex_v7", "arlene_v14"):
        for seed in (11, 22, 33, 44):
            for seat in (0, 1):
                champion_own = 1000 + seed + seat
                champion_rival = 900
                cells.append(
                    {
                        "opponent_id": opponent,
                        "seed": seed,
                        "seat": seat,
                        "champion_own": champion_own,
                        "champion_rival": champion_rival,
                        "candidate_own": champion_own + delta,
                        "candidate_rival": champion_rival,
                    }
                )
    return {
        "schema": cf.SCHEMA,
        "champion_source": cf.V31_SOURCE,
        "champion_submission_id": cf.V31_SUBMISSION_ID,
        "champion_archive_sha256": cf.V31_ARCHIVE_SHA256,
        "candidate_id": CANDIDATE_ID,
        "candidate_archive_sha256": CANDIDATE_ARCHIVE,
        "engine_id": ENGINE,
        "opponent_pack_id": PACK,
        "cells": sorted(cells, key=lambda row: (row["opponent_id"], row["seed"], row["seat"])),
    }


class ChampionFloorTests(unittest.TestCase):
    def test_exact_champion_positive_panel_passes(self):
        receipt = cf.validate_report(make_report())
        self.assertTrue(receipt["promotion_ready"])
        self.assertEqual(receipt["champion_source"], cf.V31_SOURCE)
        self.assertEqual(receipt["champion_archive_sha256"], cf.V31_ARCHIVE_SHA256)
        self.assertEqual(receipt["opponent_ids"], ["apex_v7", "arlene_v14"])
        self.assertEqual(receipt["seed_ids"], [11, 22, 33, 44])
        self.assertEqual(receipt["cell_count"], 16)
        self.assertEqual(receipt["sum_margin_delta"], 160)
        self.assertRegex(receipt["topology_sha256"], r"^[0-9a-f]{64}$")

    def test_tie_is_non_regression(self):
        receipt = cf.validate_report(make_report(delta=0))
        self.assertEqual(receipt["sum_margin_delta"], 0)
        self.assertEqual(receipt["tied_cells"], 16)

    def test_negative_panel_rejected(self):
        with self.assertRaisesRegex(cf.ChampionFloorError, "regresses exact V3.1"):
            cf.validate_report(make_report(delta=-1))

    def test_v4_cannot_masquerade_as_champion(self):
        report = make_report()
        report["champion_archive_sha256"] = V4_ARCHIVE
        with self.assertRaisesRegex(cf.ChampionFloorError, "not exact submitted V3.1"):
            cf.validate_report(report)

    def test_wrong_champion_source_rejected(self):
        report = make_report()
        report["champion_source"] = "0" * 40
        with self.assertRaisesRegex(cf.ChampionFloorError, "champion_source"):
            cf.validate_report(report)

    def test_wrong_submission_rejected(self):
        report = make_report()
        report["champion_submission_id"] += 1
        with self.assertRaisesRegex(cf.ChampionFloorError, "champion_submission_id"):
            cf.validate_report(report)

    def test_candidate_cross_build_rejected(self):
        with self.assertRaisesRegex(cf.ChampionFloorError, "candidate_id"):
            cf.validate_report(make_report(), candidate_id="v5c:" + "3" * 64)
        with self.assertRaisesRegex(cf.ChampionFloorError, "candidate archive"):
            cf.validate_report(make_report(), candidate_archive_sha256="4" * 64)

    def test_engine_and_pack_authority_rejected_on_drift(self):
        with self.assertRaisesRegex(cf.ChampionFloorError, "engine_id"):
            cf.validate_report(make_report(), engine_id="other-engine")
        with self.assertRaisesRegex(cf.ChampionFloorError, "opponent_pack_id"):
            cf.validate_report(make_report(), opponent_pack_id="other-pack")

    def test_candidate_cannot_be_champion_archive(self):
        report = make_report()
        report["candidate_archive_sha256"] = cf.V31_ARCHIVE_SHA256
        with self.assertRaisesRegex(cf.ChampionFloorError, "must differ"):
            cf.validate_report(report)

    def test_requires_two_opponents(self):
        report = make_report()
        report["cells"] = [row for row in report["cells"] if row["opponent_id"] == "apex_v7"]
        with self.assertRaisesRegex(cf.ChampionFloorError, "at least 16 cells|at least 2 distinct opponents"):
            cf.validate_report(report)

    def test_requires_identical_seed_sets(self):
        report = make_report()
        report["cells"] = [
            row
            for row in report["cells"]
            if not (row["opponent_id"] == "arlene_v14" and row["seed"] == 44)
        ]
        for seat in (0, 1):
            report["cells"].append(
                {
                    "opponent_id": "arlene_v14",
                    "seed": 55,
                    "seat": seat,
                    "champion_own": 1000,
                    "champion_rival": 900,
                    "candidate_own": 1010,
                    "candidate_rival": 900,
                }
            )
        report["cells"].sort(key=lambda row: (row["opponent_id"], row["seed"], row["seat"]))
        with self.assertRaisesRegex(cf.ChampionFloorError, "identical seed sets"):
            cf.validate_report(report)

    def test_requires_both_seats(self):
        report = make_report()
        missing = report["cells"].pop()
        replacement = copy.deepcopy(missing)
        replacement["opponent_id"] = "zeta"
        report["cells"].append(replacement)
        report["cells"].sort(key=lambda row: (row["opponent_id"], row["seed"], row["seat"]))
        with self.assertRaises(cf.ChampionFloorError):
            cf.validate_report(report)

    def test_duplicate_cell_rejected(self):
        report = make_report()
        report["cells"][-1] = copy.deepcopy(report["cells"][-2])
        with self.assertRaisesRegex(cf.ChampionFloorError, "unique"):
            cf.validate_report(report)

    def test_unsorted_cells_rejected(self):
        report = make_report()
        report["cells"][0], report["cells"][1] = report["cells"][1], report["cells"][0]
        with self.assertRaisesRegex(cf.ChampionFloorError, "canonically sorted"):
            cf.validate_report(report)

    def test_exact_report_keys_required(self):
        report = make_report()
        report["claimed_mean"] = 999999
        with self.assertRaisesRegex(cf.ChampionFloorError, "keys mismatch"):
            cf.validate_report(report)

    def test_malformed_candidate_id_rejected(self):
        report = make_report()
        report["candidate_id"] = "v5c:nothex"
        with self.assertRaisesRegex(cf.ChampionFloorError, "v5c"):
            cf.validate_report(report)

    def test_strict_json_rejects_duplicate_keys_and_nan(self):
        with self.assertRaisesRegex(cf.ChampionFloorError, "duplicate JSON object key"):
            cf._loads_strict('{"a":1,"a":2}')
        with self.assertRaisesRegex(cf.ChampionFloorError, "non-finite"):
            cf._loads_strict('{"a":NaN}')

    def test_cli_writes_canonical_receipt_atomically(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report_path = root / "report.json"
            output_path = root / "receipt.json"
            report_path.write_text(json.dumps(make_report(), sort_keys=True))
            self.assertEqual(cf.main([str(report_path), "--output", str(output_path)]), 0)
            receipt = json.loads(output_path.read_text())
            self.assertEqual(receipt["classification"], "PASS")
            self.assertEqual(receipt["candidate_id"], CANDIDATE_ID)


if __name__ == "__main__":
    unittest.main()
