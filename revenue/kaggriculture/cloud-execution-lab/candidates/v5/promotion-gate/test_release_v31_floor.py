#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

import v31_floor_gate as floor_gate
from test_release_transaction import ReleaseTransactionTests, canon, sha


class ReleaseV31FloorTests(unittest.TestCase):
    def setUp(self):
        self.fx = ReleaseTransactionTests("test_pass_is_deterministic_and_binds_all_authorities")
        self.fx.setUp()
        cells = []
        for base in self.fx.economics["cells"]:
            candidate_margin = base["candidate_own"] - base["candidate_rival"]
            cells.append({
                "opponent_id": base["opponent_id"],
                "seed": base["seed"],
                "seat": base["seat"],
                "floor_own": candidate_margin - 1,
                "floor_rival": 0,
                "candidate_own": base["candidate_own"],
                "candidate_rival": base["candidate_rival"],
            })
        self.floor = {
            "schema": floor_gate.SCHEMA,
            "floor_id": floor_gate.FLOOR_ID,
            "candidate_id": self.fx.promotion["candidate_id"],
            "engine_id": self.fx.manifest["engine_id"],
            "opponent_pack_id": self.fx.manifest["opponent_pack_id"],
            "floor_archive_sha256": floor_gate.FLOOR_ARCHIVE_SHA256,
            "candidate_archive_sha256": self.fx.new["sha256"],
            "cells": cells,
        }
        self.floor_raw = canon(self.floor)

    def build_floor(self, **overrides):
        kwargs = {
            "v31_floor_raw": self.floor_raw,
            "v31_floor_builder": floor_gate.validate_report,
        }
        kwargs.update(overrides)
        return self.fx.build(**kwargs)

    def test_release_transaction_with_floor_is_v4_and_binds_exact_authority(self):
        receipt = self.build_floor()
        self.assertEqual(receipt["schema"], "titan-v5-release-transaction/v4")
        self.assertEqual(receipt["classification"], "PASS")
        self.assertEqual(receipt["v31_floor"]["floor_id"], floor_gate.FLOOR_ID)
        self.assertEqual(
            receipt["v31_floor"]["floor_archive_sha256"],
            floor_gate.FLOOR_ARCHIVE_SHA256,
        )
        self.assertEqual(receipt["v31_floor"]["report_sha256"], sha(self.floor_raw))
        self.assertGreater(receipt["v31_floor"]["sum_margin_delta_vs_v31"], 0)
        self.assertEqual(
            receipt["v31_floor"]["opponent_ids"], receipt["economics"]["opponent_ids"]
        )
        self.assertEqual(
            receipt["v31_floor"]["cell_count"], receipt["economics"]["cell_count"]
        )

    def test_generic_two_way_builder_remains_v3_subgate_compatible(self):
        receipt = self.fx.build()
        self.assertEqual(receipt["schema"], "titan-v5-release-transaction/v3")
        self.assertNotIn("v31_floor", receipt)

    def test_v4_plus_one_but_v31_minus_one_cannot_release(self):
        bad = copy.deepcopy(self.floor)
        for cell in bad["cells"]:
            cell["floor_own"] = cell["candidate_own"] + 1
            cell["floor_rival"] = cell["candidate_rival"]
        with self.assertRaisesRegex(
            Exception, "V3.1 floor gate replay failed.*strictly outperform"
        ):
            self.build_floor(v31_floor_raw=canon(bad))

    def test_stale_floor_archive_cannot_release(self):
        bad = copy.deepcopy(self.floor)
        bad["floor_archive_sha256"] = "0" * 64
        with self.assertRaisesRegex(Exception, "V3.1 floor gate replay failed"):
            self.build_floor(v31_floor_raw=canon(bad))

    def test_swapped_floor_identity_cannot_release(self):
        bad = copy.deepcopy(self.floor)
        bad["floor_id"] = "kaggle-submission:56182437"
        with self.assertRaisesRegex(Exception, "V3.1 floor gate replay failed"):
            self.build_floor(v31_floor_raw=canon(bad))

    def test_floor_topology_must_match_v4_control_panel(self):
        bad = copy.deepcopy(self.floor)
        bad["cells"][0]["seed"] += 1000
        with self.assertRaisesRegex(Exception, "V3.1 floor gate replay failed"):
            self.build_floor(v31_floor_raw=canon(bad))

    def test_floor_candidate_scores_must_match_v4_control_panel(self):
        bad = copy.deepcopy(self.floor)
        bad["cells"][0]["candidate_own"] += 1
        with self.assertRaisesRegex(Exception, "V3.1 floor gate replay failed"):
            self.build_floor(v31_floor_raw=canon(bad))

    def test_floor_bytes_are_transition_identity(self):
        first = self.build_floor()
        better_floor = copy.deepcopy(self.floor)
        better_floor["cells"][0]["floor_own"] -= 1
        second = self.build_floor(v31_floor_raw=canon(better_floor))
        self.assertNotEqual(
            first["v31_floor"]["report_sha256"], second["v31_floor"]["report_sha256"]
        )
        self.assertNotEqual(first["transition_id"], second["transition_id"])


if __name__ == "__main__":
    unittest.main()
