#!/usr/bin/env python3
"""Acceptance tests for ward-feed-nirs-intake-validator-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter
from copy import deepcopy

import ward_feed_nirs_intake_validator as gate


class WardFeedNirsIntakeValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = gate.build_acceptance_fixture()
        cls.result = gate.run_gate(cls.rows)

    def test_fixture_is_400_with_exact_hold_mix(self) -> None:
        self.assertEqual(len(self.rows), 400)
        holds = [row["expected_hold"] for row in self.rows]
        self.assertEqual(holds.count(None), 320)
        self.assertEqual(
            Counter(h for h in holds if h is not None),
            Counter(gate.HOLD_DISTRIBUTION),
        )

    def test_pass_contract_is_clean(self) -> None:
        failures = gate.pass_contract(self.result)
        self.assertEqual(failures, [])
        self.assertTrue(self.result["ok"] if "ok" in self.result else True)
        ea = gate.expected_actual(self.result)
        self.assertTrue(ea["match"])

    def test_routes_and_counts(self) -> None:
        self.assertEqual(self.result["accessioned"], 320)
        self.assertEqual(self.result["held"], 80)
        self.assertEqual(self.result["worksheet_count"], 320)
        self.assertEqual(self.result["routes"][gate.ROUTE_NIRS], 240)
        self.assertEqual(self.result["routes"][gate.ROUTE_WET_CHEM], 80)

    def test_holds_never_get_worksheets(self) -> None:
        self.assertEqual(self.result["held_with_worksheet"], 0)
        for hold in self.result["hold_rows"]:
            self.assertFalse(hold.get("worksheet"))
            self.assertFalse(hold.get("scheduled"))

    def test_source_coords_and_hashes_persist(self) -> None:
        for acc in self.result["accession_rows"]:
            self.assertTrue(acc["source_hash"])
            self.assertIn("lat", acc["source_coords"])
            self.assertIn("lon", acc["source_coords"])

    def test_replay_creates_no_accession_or_worksheet(self) -> None:
        self.assertEqual(self.result["replay_new_accessions"], 0)
        self.assertEqual(self.result["replay_new_worksheets"], 0)

    def test_time_window_hold_uses_exact_code(self) -> None:
        codes = [h["code"] for h in self.result["hold_rows"]]
        self.assertEqual(codes.count(gate.HOLD_TIME_WINDOW_VIOLATION), 13)
        timed = [
            row
            for row in self.rows
            if row["expected_hold"] == gate.HOLD_TIME_WINDOW_VIOLATION
        ]
        for row in timed:
            self.assertGreater(
                row["receipt_hours"], gate.MAX_RECEIPT_HOURS[gate.ROUTE_NIRS]
            )

    def test_named_human_release_required(self) -> None:
        self.assertTrue(self.result["autonomous_release_denied"])
        journal = gate.run_once(self.rows[:1])
        denied = gate.release_report(
            journal, journal["accessions"][0]["accession_id"], "AUTONOMOUS"
        )
        self.assertFalse(denied["ok"])
        ok = gate.release_report(
            journal,
            journal["accessions"][0]["accession_id"],
            gate.HUMAN_RELEASER,
        )
        self.assertTrue(ok["ok"])

    def test_desc_calibration_conflict_on_wet_matrix_nirs_request(self) -> None:
        row = next(
            r
            for r in self.rows
            if r["expected_hold"] == gate.HOLD_DESC_CALIBRATION_CONFLICT
        )
        journal = gate.empty_journal()
        effect = gate.ingest_row(journal, row)
        self.assertEqual(effect["kind"], "HOLD")
        self.assertEqual(effect["code"], gate.HOLD_DESC_CALIBRATION_CONFLICT)
        self.assertEqual(len(journal["worksheets"]), 0)

    def test_duplicate_bag_label_hold(self) -> None:
        valid = next(r for r in self.rows if r["expected_hold"] is None)
        dup = next(
            r for r in self.rows if r["expected_hold"] == gate.HOLD_DUPLICATE_BAG_LABEL
        )
        journal = gate.empty_journal()
        gate.ingest_row(journal, valid)
        effect = gate.ingest_row(journal, dup)
        self.assertEqual(effect["code"], gate.HOLD_DUPLICATE_BAG_LABEL)
        self.assertEqual(len(journal["accessions"]), 1)

    def test_mutating_fixture_row_is_isolated(self) -> None:
        row = deepcopy(self.rows[0])
        row["prep_status"] = "WHOLE_BAG_UNGROUND"
        journal = gate.empty_journal()
        effect = gate.ingest_row(journal, row)
        self.assertEqual(effect["code"], gate.HOLD_INSUFFICIENT_PREP)


if __name__ == "__main__":
    unittest.main()
