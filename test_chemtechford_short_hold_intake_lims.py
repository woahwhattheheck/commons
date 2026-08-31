#!/usr/bin/env python3
"""Binary acceptance for chemtechford-short-hold-intake-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter

import chemtechford_short_hold_intake_lims as clock


class ChemtechFordShortHoldIntakeLimsTests(unittest.TestCase):
    def test_acceptance_fixture_is_600_split_450_150(self) -> None:
        rows = clock.build_acceptance_fixture()
        self.assertEqual(len(rows), 600)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "ACCESSIONED"), 450)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "REJECTED"), 150)
        reasons = [row["expected_reason"] for row in rows if row["expected_state"] == "REJECTED"]
        self.assertEqual(reasons.count("TEMPERATURE"), 25)
        self.assertEqual(reasons.count("CONTAINER"), 25)
        self.assertEqual(reasons.count("PRESERVATION"), 25)
        self.assertEqual(reasons.count("SIGNATURE"), 25)
        self.assertEqual(reasons.count("DUPLICATE_ID"), 25)
        self.assertEqual(reasons.count("HOLDING_TIME"), 25)
        self.assertEqual(clock.fixture_manifest()["fixture_sha256"], clock.GOLDEN_FIXTURE_SHA256)
        self.assertEqual(clock.CATALOG_SHA256, clock.GOLDEN_CATALOG_SHA256)

    def test_pass_contract_exactly_450_accessioned_150_rejected(self) -> None:
        result = clock.run_gate()
        self.assertEqual(clock.pass_contract(result), [])
        counts = clock.expected_actual(result)
        self.assertEqual(counts["expected"], clock.EXPECTED_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["accessioned"], 450)
        self.assertEqual(result["rejected"], 150)
        self.assertEqual(result["duplicates"], 0)
        self.assertEqual(result["replay_added_accessions"], 0)
        self.assertEqual(result["reconcile_ok"], 450)
        self.assertEqual(result["reconcile_fail"], 0)
        self.assertEqual(result["released"], 0)
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["shadowing"], "READ_ONLY")
        self.assertFalse(result["autonomous_release"])
        self.assertEqual(result["fixture_sha256"], clock.GOLDEN_FIXTURE_SHA256)
        self.assertEqual(result["catalog_sha256"], clock.GOLDEN_CATALOG_SHA256)
        self.assertEqual(result["manifest_sha256"], clock.GOLDEN_MANIFEST_SHA256)
        self.assertEqual(result["signed_manifest_rollup"], clock.GOLDEN_SIGNED_MANIFEST_ROLLUP)
        self.assertEqual(Counter(result["reject_codes"]), Counter(clock.REJECT_FAMILY_COUNTS))

    def test_every_invalid_rejects_with_truth_set_reason(self) -> None:
        rows = clock.build_acceptance_fixture()
        result = clock.run_gate(rows)
        rejects = {(item["sample_id"], item["portal_record_id"]): item for item in result["reject_records"]}
        self.assertEqual(len(rejects), 150)
        for row in rows:
            if row["expected_state"] != "REJECTED":
                continue
            hold = rejects[(row["sample_id"], row["portal_record_id"])]
            self.assertEqual(hold["reason"], row["expected_reason"])
            self.assertEqual(hold["state"], "REJECTED")
        self.assertEqual(len(set(result["sample_ids"]) | {row["sample_id"] for row in rows if row["expected_reason"] != "DUPLICATE_ID" and row["expected_state"] == "REJECTED"}), 575)

    def test_valid_samples_create_exactly_one_accession_with_exact_timestamps(self) -> None:
        rows = {row["sample_id"]: row for row in clock.build_acceptance_fixture() if row["expected_state"] == "ACCESSIONED"}
        result = clock.run_gate()
        self.assertEqual(len(result["accessions"]), 450)
        self.assertEqual(len(set(result["accession_ids"])), 450)
        self.assertEqual(len(set(result["sample_ids"])), 450)
        for record in result["accessions"]:
            src = rows[record["sample_id"]]
            self.assertEqual(record["collected_at"], src["collected_at"])
            self.assertEqual(record["received_at"], src["received_at"])
            self.assertEqual(record["accessioned_at"], src["received_at"])
            self.assertEqual(record["clock_seconds"], src["clock_seconds"])
            self.assertEqual(record["matrix"], src["matrix"])
            self.assertEqual(record["method"], src["method"])
            self.assertFalse(record["released"])
            self.assertIsNone(record["released_by"])

    def test_six_hour_wastewater_and_24_hour_drinking_water_clocks_evaluate_exactly(self) -> None:
        rows = clock.build_acceptance_fixture()
        result = clock.run_gate(rows)
        ww_exact = [row for row in rows if row["expected_state"] == "ACCESSIONED" and row["matrix"] == "WASTEWATER" and row["clock_seconds"] == clock.WW_HOLDING_SECONDS]
        dw_exact = [row for row in rows if row["expected_state"] == "ACCESSIONED" and row["matrix"] == "DRINKING_WATER" and row["clock_seconds"] == clock.DW_HOLDING_SECONDS]
        self.assertEqual(len(ww_exact), 15)
        self.assertEqual(len(dw_exact), 15)
        accessioned = {item["sample_id"]: item for item in result["accessions"]}
        for row in ww_exact:
            self.assertEqual(accessioned[row["sample_id"]]["clock_seconds"], 6 * 3600)
            self.assertEqual(accessioned[row["sample_id"]]["holding_limit_seconds"], 6 * 3600)
        for row in dw_exact:
            self.assertEqual(accessioned[row["sample_id"]]["clock_seconds"], 24 * 3600)
            self.assertEqual(accessioned[row["sample_id"]]["holding_limit_seconds"], 24 * 3600)

        over = [row for row in rows if row["expected_reason"] == "HOLDING_TIME"]
        self.assertEqual(len(over), 25)
        ww_over = [row for row in over if row["matrix"] == "WASTEWATER"]
        dw_over = [row for row in over if row["matrix"] == "DRINKING_WATER"]
        self.assertEqual(len(ww_over), 13)
        self.assertEqual(len(dw_over), 12)
        self.assertTrue(all(row["clock_seconds"] == clock.WW_HOLDING_SECONDS + 1 for row in ww_over))
        self.assertTrue(all(row["clock_seconds"] == clock.DW_HOLDING_SECONDS + 1 for row in dw_over))
        reject_ids = {item["sample_id"] for item in result["reject_records"] if item["reason"] == "HOLDING_TIME"}
        self.assertEqual(reject_ids, {row["sample_id"] for row in over})

        under_one = next(row for row in rows if row["expected_state"] == "ACCESSIONED" and row["clock_seconds"] < row["holding_limit_seconds"])
        self.assertIn(under_one["sample_id"], accessioned)

    def test_retries_create_zero_duplicates(self) -> None:
        first = clock.run_gate()
        second = clock.run_gate()
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(len(first["manifest_sha256"]), 64)
        self.assertEqual(first["fixture_sha256"], second["fixture_sha256"])
        self.assertEqual(first["replay_added_accessions"], 0)
        self.assertEqual(first["replay_noops"], 600)
        self.assertEqual(clock.sha256_hex(clock.cli_payload(first)), clock.sha256_hex(clock.cli_payload(second)))

        rows = clock.build_acceptance_fixture()
        journal = clock.empty_journal()
        lims = clock.SimulatedLimsAdapter()
        portal = clock.ReadOnlyPortalAdapter(rows)
        coc = clock.ReadOnlyCocAdapter(rows)
        state = clock.ReadOnlyStateDeliveryAdapter(rows)
        instrument = clock.ReadOnlyInstrumentAdapter(rows)
        for portal_record in portal.list_submissions():
            coc_id = clock._pick(portal_record, clock.PORTAL_ALIASES["coc_id"])
            sample_id = clock._text(clock._pick(portal_record, clock.PORTAL_ALIASES["sample_id"]))
            clock.ingest_submission(journal, lims, portal_record, coc.get(clock._text(coc_id)) or {}, state.get(sample_id), instrument)
        self.assertEqual(len(journal["accessions"]), 450)
        self.assertEqual(len(journal["rejects"]), 150)
        replay = []
        for portal_record in portal.list_submissions():
            coc_id = clock._pick(portal_record, clock.PORTAL_ALIASES["coc_id"])
            sample_id = clock._text(clock._pick(portal_record, clock.PORTAL_ALIASES["sample_id"]))
            replay.append(
                clock.ingest_submission(journal, lims, portal_record, coc.get(clock._text(coc_id)) or {}, state.get(sample_id), instrument)
            )
        self.assertEqual(sum(1 for item in replay if item["kind"] == "REPLAY_NOOP"), 600)
        self.assertEqual(len(journal["accessions"]), 450)
        self.assertEqual(len(journal["rejects"]), 150)
        self.assertEqual(len(lims.accessions), 450)

    def test_portal_and_state_records_reconcile_to_signed_manifest(self) -> None:
        rows = clock.build_acceptance_fixture()
        result = clock.run_gate(rows)
        self.assertEqual(result["reconcile_ok"], 450)
        self.assertEqual(result["reconcile_fail"], 0)
        accessions = {item["sample_id"]: item for item in result["accessions"]}
        portal = clock.ReadOnlyPortalAdapter(rows)
        state = clock.ReadOnlyStateDeliveryAdapter(rows)
        for row in rows:
            if row["expected_state"] != "ACCESSIONED":
                continue
            record = accessions[row["sample_id"]]
            portal_record = next(
                item
                for item in portal.list_submissions()
                if clock._text(clock._pick(item, clock.PORTAL_ALIASES["portal_record_id"])) == row["portal_record_id"]
            )
            check = clock.reconcile_accession(
                {
                    **record,
                    "collected_at": record["collected_at"],
                    "received_at": record["received_at"],
                    "accessioned_at": record["accessioned_at"],
                    "clock_seconds": record["clock_seconds"],
                    "matrix": record["matrix"],
                    "method": record["method"],
                    "portal_hash": record["portal_hash"],
                    "state_hash": record["state_hash"],
                    "signed_manifest_sha256": record["signed_manifest_sha256"],
                    "accession_id": record["accession_id"],
                    "sample_id": record["sample_id"],
                },
                portal_record,
                state.get(row["sample_id"]) or {},
            )
            self.assertTrue(check["ok"], row["sample_id"])

        tampered = clock.reconcile_accession(
            result["accessions"][0],
            {"Sample ID": "TAMPER", "Date/Time Collected": "1999-01-01T00:00:00Z", "Date/Time Received": "1999-01-01T00:00:00Z", "Matrix": "Wastewater", "Method": "SYN-CFL-WW-FC", "Portal Record": "NOPE"},
            {"sample_id": "TAMPER", "collected_at": "1999-01-01T00:00:00Z", "received_at": "1999-01-01T00:00:00Z", "matrix": "WASTEWATER", "method": "SYN-CFL-WW-FC", "state_delivery_id": "NOPE"},
        )
        self.assertFalse(tampered["ok"])

    def test_named_human_release_gate_denies_autonomous(self) -> None:
        rows = clock.build_acceptance_fixture()
        journal = clock.empty_journal()
        lims = clock.SimulatedLimsAdapter()
        portal = clock.ReadOnlyPortalAdapter(rows[:1])
        coc = clock.ReadOnlyCocAdapter(rows[:1])
        state = clock.ReadOnlyStateDeliveryAdapter(rows[:1])
        instrument = clock.ReadOnlyInstrumentAdapter(rows[:1])
        portal_record = portal.list_submissions()[0]
        clock.ingest_submission(journal, lims, portal_record, coc.get(rows[0]["coc_id"]) or {}, state.get(rows[0]["sample_id"]), instrument)
        sample_id = rows[0]["sample_id"]
        record = journal["accessions"][sample_id]

        missing = clock.release_accession(journal, sample_id, named_approver="")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["code"], "MISSING_NAMED_APPROVAL")
        self.assertFalse(record["released"])

        auto = clock.release_accession(journal, sample_id, named_approver="SYSTEM")
        self.assertFalse(auto["ok"])
        self.assertEqual(auto["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(record["released"])

        bot = clock.release_accession(journal, sample_id, named_approver="AUTO")
        self.assertFalse(bot["ok"])
        self.assertEqual(bot["code"], "AUTONOMOUS_RELEASE_DENIED")

        named = clock.release_accession(journal, sample_id, named_approver=clock.HUMAN_APPROVER)
        self.assertTrue(named["ok"])
        self.assertEqual(record["released_by"], clock.HUMAN_APPROVER)
        self.assertTrue(record["released"])
        self.assertEqual(named["released_by"], clock.HUMAN_APPROVER)

    def test_adapters_are_read_only_or_simulated(self) -> None:
        rows = clock.build_acceptance_fixture()
        portal = clock.ReadOnlyPortalAdapter(rows)
        self.assertEqual(portal.mode, "READ_ONLY")
        self.assertFalse(portal.live)
        self.assertEqual(len(portal.list_submissions()), 600)
        with self.assertRaises(RuntimeError):
            portal.write({"sample_id": "nope"})
        for adapter in (
            clock.ReadOnlyCocAdapter(rows),
            clock.ReadOnlyStateDeliveryAdapter(rows),
            clock.ReadOnlyInstrumentAdapter(rows),
            clock.ReadOnlyDeliveryAdapter(rows),
        ):
            self.assertEqual(adapter.mode, "READ_ONLY")
            self.assertFalse(adapter.live)
            with self.assertRaises(RuntimeError):
                adapter.write({"sample_id": "nope"})
        lims = clock.SimulatedLimsAdapter()
        self.assertEqual(lims.mode, "SIMULATED")
        self.assertFalse(lims.live)
        self.assertEqual(lims.production_writes, 0)

    def test_normalize_maps_portal_and_coc_aliases(self) -> None:
        row = clock.build_acceptance_fixture()[0]
        canonical = clock.normalize_submission(clock._portal_view(row), clock._coc_view(row))
        self.assertEqual(canonical["sample_id"], row["sample_id"])
        self.assertEqual(canonical["matrix"], row["matrix"])
        self.assertEqual(canonical["method"], row["method"])
        self.assertEqual(canonical["container"], row["container"])
        self.assertEqual(canonical["preservation"], row["preservation"])
        self.assertEqual(canonical["collected_at"], row["collected_at"])
        self.assertEqual(canonical["received_at"], row["received_at"])
        self.assertEqual(canonical["clock_seconds"], row["clock_seconds"])


if __name__ == "__main__":
    unittest.main()
