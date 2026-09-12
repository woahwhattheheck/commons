#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import current_wheat_buy_census
import townprocure_current_subsumption as sut


class TimingMathTests(unittest.TestCase):
    def test_first_center_after_due_is_456(self):
        self.assertEqual(sut._first_multiple_at_or_after(455, 24), 456)
        self.assertEqual(sut._first_multiple_at_or_after(456, 24), 456)

    def test_next_shop_cadence_can_be_same_callback(self):
        self.assertEqual(sut._first_multiple_at_or_after(455, 4), 456)
        self.assertEqual(sut._first_multiple_at_or_after(460, 4), 460)

    def test_invalid_interval_fails_closed(self):
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    sut._first_multiple_at_or_after(455, value)

    def test_invalid_step_fails_closed(self):
        for value in (-1, True, 455.0):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    sut._first_multiple_at_or_after(value, 24)


class SnapshotCustodyTests(unittest.TestCase):
    def test_theorem_source_semantics_stay_bound_after_path_swap(self):
        original = b"AUTHENTICATED_ANCHOR = True\n"
        swapped = b"ATTACKER_BYTES = True\n"
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "main.py"
            source.write_bytes(original)
            pin = sut._git_blob_bytes(original)
            with mock.patch.dict(sut.PINS, {"main.py": pin}, clear=True):
                snapshots, observed = sut._capture_pinned_sources({"main.py": source})
            self.assertEqual(observed, {"main.py": pin})

            # Deterministic predecessor: mutate the pathname *after* identity auth.
            source.write_bytes(swapped)
            semantic_source = sut._snapshot_text(snapshots["main.py"], "main.py")
            self.assertIn("AUTHENTICATED_ANCHOR", semantic_source)
            self.assertNotIn("ATTACKER_BYTES", semantic_source)
            self.assertEqual(sut._git_blob_bytes(snapshots["main.py"]), pin)

    def test_vendor_exec_uses_authenticated_snapshot_after_path_swap(self):
        original = (
            b"def routes():\n"
            b"    return {'auth': [{'market': [['BUY_PRODUCT', 'WHEAT', 2]]}]}\n"
        )
        swapped = b"def routes():\n    return {'attacker': []}\n"
        expected_blob = current_wheat_buy_census._git_blob_bytes(original)
        original_loader = current_wheat_buy_census._load_vendor_snapshot

        with tempfile.TemporaryDirectory() as td:
            lab = Path(td) / "lab"
            vendor = lab / "reference" / "next-panel" / "vendor" / "arlene.py"
            vendor.parent.mkdir(parents=True)
            vendor.write_bytes(original)

            def swap_then_execute(snapshot, source_path):
                # This hook runs after census authenticated `snapshot` and before
                # its semantic execution. Reopening source_path would execute poison.
                source_path.write_bytes(swapped)
                return original_loader(snapshot, source_path)

            with mock.patch.object(current_wheat_buy_census, "_lab_root", return_value=lab), mock.patch.object(
                current_wheat_buy_census,
                "_load_vendor_snapshot",
                side_effect=swap_then_execute,
            ):
                result = current_wheat_buy_census.census(
                    expected_vendor_blob=expected_blob
                )

        self.assertEqual(result["vendor_git_blob"], expected_blob)
        self.assertEqual(result["vendor_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(result["route_count"], 1)
        self.assertEqual(result["routes_with_wheat_buys"], ["auth"])
        self.assertEqual(result["wheat_buy_row_count"], 1)
        self.assertEqual(result["wheat_buy_quantities"], [2])


class CurrentSourceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = sut.audit()

    def test_current_sources_are_exactly_bound(self):
        self.assertEqual(self.result["engine_git_blob"], sut.ENGINE_BLOB)
        self.assertEqual(self.result["arlene_git_blob"], sut.ARLENE_BLOB)
        self.assertEqual(self.result["source_git_blobs"], sut.PINS)

    def test_dynamic_constructor_is_current_crop_repair(self):
        dynamic = self.result["dynamic_crop_repair"]
        self.assertEqual(dynamic["constructor"], "crop_release.propose_input_repair")
        self.assertEqual(dynamic["obligation_units"], 3)
        self.assertEqual(dynamic["first_due_step"], 455)
        self.assertEqual(dynamic["first_post_due_town_center_step"], 456)
        self.assertTrue(dynamic["market_precedes_same_callback_town"])
        self.assertTrue(dynamic["reconciles_prior_receipt_before_next_proposal"])

    def test_disposition_tracks_complete_route_census(self):
        rows = self.result["route_wheat_buy_row_count"]
        if rows:
            self.assertEqual(
                self.result["decision"],
                "ROUTE_WHEAT_BUYS_REQUIRE_SEPARATE_TIMING_GATE",
            )
            self.assertTrue(self.result["route_wheat_buy_steps"])
            self.assertTrue(self.result["route_wheat_buy_quantities"])
        else:
            self.assertEqual(self.result["decision"], "SUBSUMED_NO_LAWFUL_RETIME")
            self.assertEqual(self.result["route_wheat_buy_steps"], [])
            self.assertEqual(self.result["route_wheat_buy_quantities"], [])

    def test_audit_is_deterministic_within_process(self):
        again = sut.audit()
        self.assertEqual(again["result_sha256"], self.result["result_sha256"])
        self.assertEqual(again["decision"], self.result["decision"])


if __name__ == "__main__":
    unittest.main()
