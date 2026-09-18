#!/usr/bin/env python3
"""Binary acceptance for agriseed-rush-work-allocator-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter

import agriseed_rush_work_allocator as gate


class AgriSeedRushWorkAllocatorTests(unittest.TestCase):
    def test_fixture_is_300_split_240_60(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 300)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "ACCESSIONED"), 240)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "HELD"), 60)
        reasons = [row["expected_reason"] for row in rows if row["expected_state"] == "HELD"]
        self.assertEqual(Counter(reasons), Counter({code: 12 for code in gate.HOLD_CODES}))
        manifest = gate.fixture_manifest(rows)
        self.assertEqual(manifest["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)
        self.assertEqual(manifest["catalog_sha256"], gate.GOLDEN_CATALOG_SHA256)
        self.assertEqual(gate.CATALOG_SHA256, gate.GOLDEN_CATALOG_SHA256)

    def test_pass_contract_exact_counts(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.EXPECTED_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["accessioned"], 240)
        self.assertEqual(result["held"], 60)
        self.assertEqual(result["duplicates"], 0)
        self.assertEqual(result["replay_added_accessions"], 0)
        self.assertEqual(result["released_after_named_human"], 240)
        self.assertEqual(result["released_without_named_human"], 0)
        self.assertEqual(result["held_released"], 0)
        self.assertEqual(result["production_writes"], 0)
        self.assertFalse(result["interface_live"])
        self.assertFalse(result["autonomous_release"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["shadowing"], "READ_ONLY")
        self.assertEqual(result["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)
        self.assertEqual(result["catalog_sha256"], gate.GOLDEN_CATALOG_SHA256)
        self.assertEqual(result["manifest_sha256"], gate.GOLDEN_MANIFEST_SHA256)
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(
            Counter(result["hold_codes"]),
            Counter({code: 12 for code in gate.HOLD_CODES}),
        )

    def test_every_hold_matches_truth_set_reason(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {item["submission_id"]: item for item in result["holds"]}
        self.assertEqual(len(holds), 60)
        for row in rows:
            if row["expected_state"] != "HELD":
                continue
            hold = holds[row["submission_id"]]
            self.assertEqual(hold["reason"], row["expected_reason"])
            self.assertEqual(hold["state"], "HELD")

    def test_valid_rows_accession_once_with_method_and_role(self) -> None:
        rows = {
            row["submission_id"]: row
            for row in gate.build_acceptance_fixture()
            if row["expected_state"] == "ACCESSIONED"
        }
        result = gate.run_gate()
        self.assertEqual(len(result["accessions"]), 240)
        self.assertEqual(len(set(result["accession_ids"])), 240)
        self.assertEqual(len(set(result["submission_ids"])), 240)
        for record in result["accessions"]:
            src = rows[record["submission_id"]]
            self.assertEqual(record["method"], src["method"])
            self.assertEqual(record["method_revision"], src["method_revision"])
            self.assertEqual(record["role"], src["role"])
            self.assertEqual(record["site"], src["site"])
            self.assertEqual(record["analyst_id"], src["analyst_id"])
            self.assertIn(record["role"], gate.ANALYSTS[record["analyst_id"]]["roles"])
            self.assertFalse(record["released"])
            self.assertIsNone(record["released_by"])

    def test_rush_never_shortens_regulated_duration(self) -> None:
        result = gate.run_gate()
        rush_rows = [a for a in result["accessions"] if a["rush"]]
        self.assertGreater(len(rush_rows), 0)
        for acc in result["accessions"]:
            self.assertGreaterEqual(
                acc["reported_duration_hours"],
                acc["regulated_biological_hours"],
            )
            self.assertFalse(acc["rush_shortened"])
        self.assertEqual(result["rush_never_shortened"], 240)

    def test_two_site_routing_uses_catalog_sites(self) -> None:
        result = gate.run_gate()
        sites = {a["site"] for a in result["accessions"]}
        self.assertEqual(sites, {gate.SITE_A, gate.SITE_B})
        frameworks = {a["framework"] for a in result["accessions"]}
        self.assertEqual(frameworks, {"AOSA", "CANADIAN", "ISTA"})

    def test_named_human_required_for_release(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["released"]), 240)
        for item in result["released"]:
            self.assertTrue(item["released"])
            self.assertEqual(item["released_by"], gate.HUMAN_APPROVER)
            self.assertEqual(item["released_role"], gate.HUMAN_ROLE)
        for hold in result["holds"]:
            self.assertFalse(hold["released"])

    def test_replay_adds_nothing(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["accession_ids"], second["accession_ids"])
        self.assertEqual(first["fixture_sha256"], second["fixture_sha256"])
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["replay_added_accessions"], 0)
        self.assertEqual(second["replay_added_accessions"], 0)

    def test_report_fields_match_manifest_digests(self) -> None:
        result = gate.run_gate()
        digests = [row["report_sha256"] for row in result["report_fields"]]
        self.assertEqual(digests, result["signed_manifest"]["report_digests"])
        self.assertEqual(len(digests), 240)
        self.assertEqual(len(set(digests)), 240)


if __name__ == "__main__":
    unittest.main()
