#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "_titan_v5_plantquorum_runner", HERE / "plantquorum_census.py"
)
census = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(census)


class PlantQuorumCurrentNativeRunnerTests(unittest.TestCase):
    def test_source_pins_match_single_observer_and_current_package_contract(self):
        for path, expected, label in (
            (census.OBSERVER, census.OBSERVER_GIT_BLOB, "census.py"),
            (census.PLANTQUORUM, census.PLANTQUORUM_GIT_BLOB, "plant_quorum_admission.py"),
            (census.NATIVE_CENSUS, census.NATIVE_CENSUS_GIT_BLOB, "native_census.py"),
            (census.UNITPIPE, census.UNITPIPE_GIT_BLOB, "unit_pipeline_admission.py"),
        ):
            with self.subTest(label=label):
                data = census._capture_pinned(path, expected, label)
                self.assertEqual(census.git_blob_sha(data), expected)
        pointer = census._pointer_contract()
        self.assertEqual(pointer["sha256"], census.ARCHIVE_SHA256)
        self.assertEqual(pointer["bytes"], census.ARCHIVE_BYTES)
        self.assertEqual(pointer["source_manifest_sha256"], census.SOURCE_SHA256)
        self.assertEqual(pointer["runtime_files"], census.RUNTIME_FILES)

    @staticmethod
    def _cell(seed, seat, engagements=0):
        return {
            "schema": census.CELL_SCHEMA,
            "source": copy.deepcopy(census.EXPECTED_SOURCE),
            "archive_receipt": {
                "sha256": census.ARCHIVE_SHA256,
                "bytes": census.ARCHIVE_BYTES,
                "members": census.RUNTIME_FILES + 1,
            },
            "seed": seed,
            "seat": seat,
            "callbacks": census.EXPECTED_CALLBACKS,
            "engagements": engagements,
            "candidate_applied_to_gameplay": False,
            "examples": ([{"step": 9, "changed": True}] if engagements else []),
            "scores": [100, 90],
        }

    def test_zero_engagement_panel_is_only_starter_no_engagement(self):
        cells = [
            self._cell(seed, seat)
            for seed in census.PANEL_SEEDS
            for seat in census.PANEL_SEATS
        ]
        panel = census.aggregate_cells(cells)
        self.assertEqual(panel["cells"], 16)
        self.assertEqual(panel["callbacks"], 16 * census.EXPECTED_CALLBACKS)
        self.assertEqual(panel["engagements"], 0)
        self.assertEqual(panel["verdict"], "NO_STARTER_ENGAGEMENT")
        self.assertIn("widen natural census", panel["interpretation"])
        self.assertIs(panel["candidate_applied_to_gameplay"], False)

    def test_engaged_panel_routes_to_economics_without_ev_claim(self):
        cells = [
            self._cell(seed, seat)
            for seed in census.PANEL_SEEDS
            for seat in census.PANEL_SEATS
        ]
        cells[0] = self._cell(census.PANEL_SEEDS[0], 0, engagements=2)
        panel = census.aggregate_cells(cells)
        self.assertEqual(panel["engagements"], 2)
        self.assertEqual(panel["engaged_cells"], 1)
        self.assertEqual(panel["verdict"], "ENGAGED_CURRENT_NATIVE_STARTER")
        self.assertIn("OFF/ON economics", panel["interpretation"])
        self.assertIs(panel["candidate_applied_to_gameplay"], False)

    def test_panel_rejects_duplicate_coordinate(self):
        cells = [
            self._cell(seed, seat)
            for seed in census.PANEL_SEEDS
            for seat in census.PANEL_SEATS
        ]
        cells[-1] = copy.deepcopy(cells[0])
        with self.assertRaisesRegex(ValueError, "duplicate panel coordinate"):
            census.aggregate_cells(cells)

    def test_panel_rejects_bool_counter_alias(self):
        cells = [
            self._cell(seed, seat)
            for seed in census.PANEL_SEEDS
            for seat in census.PANEL_SEATS
        ]
        cells[0]["engagements"] = True
        cells[0]["examples"] = [{"step": 1}]
        with self.assertRaisesRegex(ValueError, "exact integer"):
            census.aggregate_cells(cells)

    def test_panel_rejects_archive_receipt_drift(self):
        cells = [
            self._cell(seed, seat)
            for seed in census.PANEL_SEEDS
            for seat in census.PANEL_SEATS
        ]
        cells[0]["archive_receipt"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "archive receipt mismatch"):
            census.aggregate_cells(cells)

    def test_strict_json_rejects_duplicate_keys_and_nonfinite(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            census._strict_json_bytes(b'{"a":1,"a":2}', "dup")
        with self.assertRaisesRegex(ValueError, "non-finite"):
            census._strict_json_bytes(b'{"a":NaN}', "nan")

    def test_archive_member_path_custody(self):
        self.assertEqual(
            census._safe_member("checks/reference/engine/kaggriculture.py").as_posix(),
            "checks/reference/engine/kaggriculture.py",
        )
        for poisoned in ("/abs", "../escape", "a/../b", "a\\b", ""):
            with self.subTest(poisoned=poisoned):
                with self.assertRaises(ValueError):
                    census._safe_member(poisoned)


if __name__ == "__main__":
    unittest.main(verbosity=2)
