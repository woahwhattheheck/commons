#!/usr/bin/env python3
"""Binary acceptance for rmb-crosssite-courier-accession-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter
from copy import deepcopy

import rmb_crosssite_courier_accession as gate


class RmbCrosssiteCourierAccessionTests(unittest.TestCase):
    def test_acceptance_fixture_row_count_and_truth_set(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 300)
        truths = Counter(row["truth"] for row in rows)
        self.assertEqual(truths["VALID"], 240)
        for code in gate.HOLD_CODES:
            self.assertEqual(truths[code], 10, code)

    def test_pass_contract_exact_counts_and_holds(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 300)
        self.assertEqual(result["accessioned"], 240)
        self.assertEqual(result["held"], 60)
        self.assertEqual(result["hold_counts"], {code: 10 for code in gate.HOLD_CODES})
        self.assertEqual(len(set(result["incumbent_accession_ids"])), 240)
        self.assertEqual(result["released_reports"], 0)
        self.assertEqual(result["blocked_reports"], 240)
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "READ_ONLY_SHADOW")
        self.assertTrue(result["shadow_only"])
        self.assertEqual(result["incumbent_writes"], 0)
        self.assertEqual(result["production_writes"], 0)
        self.assertFalse(result["autonomous_certification"])
        self.assertFalse(result["autonomous_release"])

    def test_each_valid_row_maps_one_incumbent_accession_and_facility(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        valid_ids = [row["sample_id"] for row in rows if row["truth"] == "VALID"]
        self.assertEqual(len(valid_ids), 240)
        self.assertEqual(len(set(valid_ids)), 240)
        bound = {item["sample_id"]: item for item in result["accessions"]}
        self.assertEqual(set(bound), set(valid_ids))
        rmb = 0
        beckton = 0
        for row in rows:
            if row["truth"] != "VALID":
                continue
            item = bound[row["sample_id"]]
            self.assertEqual(item["facility"], row["facility"])
            self.assertEqual(
                item["incumbent_accession_id"],
                gate.incumbent_accession_id(row["facility"], row["sample_id"]),
            )
            if row["facility"] == "RMB_DETROIT_LAKES":
                rmb += 1
            else:
                beckton += 1
        self.assertEqual(rmb, 120)
        self.assertEqual(beckton, 120)

    def test_hold_codes_match_truth_set_exactly(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds_by_row = {item["row_id"]: item["code"] for item in result["holds"]}
        for row in rows:
            if row["truth"] == "VALID":
                self.assertNotIn(row["row_id"], holds_by_row)
                continue
            self.assertEqual(holds_by_row[row["row_id"]], row["truth"])

    def test_no_sample_or_result_crosses_client_site(self) -> None:
        result = gate.run_gate()
        seen = set()
        for item in result["accessions"]:
            key = (item["client_id"], item["site_id"], item["sample_id"])
            self.assertNotIn(key, seen)
            seen.add(key)
            ident = result["identities"][item["incumbent_accession_id"]]
            self.assertEqual(ident["client_id"], item["client_id"])
            self.assertEqual(ident["site_id"], item["site_id"])
            self.assertEqual(ident["sample_id"], item["sample_id"])

        journal = gate.empty_journal()
        valid = next(row for row in gate.build_acceptance_fixture() if row["truth"] == "VALID")
        gate.ingest_row(journal, valid)
        acc_id = next(iter(journal["accessions"]))
        denied = gate.attach_result(
            journal,
            acc_id,
            {"value": 1.2},
            client_id="OTHER-CLIENT",
            site_id=valid["site_id"],
        )
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "CLIENT_SITE_CROSS")
        allowed = gate.attach_result(
            journal,
            acc_id,
            {"value": 1.2},
            client_id=valid["client_id"],
            site_id=valid["site_id"],
        )
        self.assertTrue(allowed["ok"])

    def test_cert_scope_and_courier_timestamps_match_signed_manifest(self) -> None:
        result = gate.run_gate()
        fixture = {
            row["sample_id"]: row
            for row in gate.build_acceptance_fixture()
            if row["truth"] == "VALID"
        }
        self.assertEqual(result["hashes_ok_count"], 240)
        self.assertEqual(result["manifest_match_count"], 240)
        for item in result["accessions"]:
            row = fixture[item["sample_id"]]
            manifest = row["signed_manifest"]
            self.assertEqual(manifest["pickup_ts"], item["pickup_ts"])
            self.assertEqual(manifest["receipt_ts"], item["receipt_ts"])
            self.assertEqual(manifest["facility"], item["facility"])
            self.assertEqual(manifest["method"], item["method"])
            self.assertEqual(manifest["cert_scope"], item["cert_scope"])
            self.assertTrue(gate.hashes_reconcile(row))
            self.assertEqual(item["source_hash"], gate.source_hash(row))
            self.assertEqual(item["custody_hash"], gate.custody_hash(row))
            self.assertEqual(item["manifest_hash"], gate.manifest_hash(row))

    def test_replay_creates_zero_records(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(len(first["manifest_sha256"]), 64)
        self.assertEqual(len(first["fixture_sha256"]), 64)

        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 240)
        self.assertEqual(len(journal["holds"]), 60)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["accession_count"], 240)
        self.assertEqual(replay["hold_count"], 60)
        self.assertEqual(replay["replay_noops"], 240)

    def test_human_review_controls_release(self) -> None:
        journal = gate.empty_journal()
        row = next(item for item in gate.build_acceptance_fixture() if item["truth"] == "VALID")
        gate.ingest_row(journal, row)
        acc_id = next(iter(journal["accessions"]))
        record = journal["accessions"][acc_id]
        self.assertEqual(gate.report_status(record), "STAGED_BLOCKED_MISSING_RESULT")

        denied = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "REPORT_BLOCKED")

        gate.attach_result(
            journal,
            acc_id,
            {"value": 0.42},
            client_id=row["client_id"],
            site_id=row["site_id"],
        )
        self.assertEqual(record["report_status"], "STAGED_BLOCKED_MISSING_QC")
        gate.qc_signoff(journal, acc_id)
        self.assertEqual(record["report_status"], "STAGED_READY_FOR_HUMAN_RELEASE")

        autonomous = gate.release_report(journal, acc_id, actor_role="SYSTEM", actor="autonomous")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(record["released"])

        human = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertTrue(human["ok"])
        self.assertEqual(record["report_status"], "RELEASED")
        self.assertEqual(record["released_by"], "reviewer-1")

    def test_read_only_shadow_never_writes_incumbent_or_production(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["incumbent_writes"], 0)
        self.assertEqual(result["production_writes"], 0)
        self.assertTrue(result["incumbent_authoritative"])
        self.assertTrue(result["shadow_only"])
        for item in result["accessions"]:
            self.assertEqual(item["interface_state"], "READ_ONLY_SHADOW")
            self.assertFalse(item["interface_live"])
            self.assertFalse(item["incumbent_write"])
            self.assertFalse(item["production_write"])
            self.assertFalse(item["released"])
        self.assertTrue(
            all(
                item["code"] == "AUTONOMOUS_RELEASE_DENIED"
                for item in result["autonomous_release_effects"]
            )
        )

    def test_classifier_matches_each_hold_defect_independently(self) -> None:
        rows = {row["truth"]: row for row in gate.build_acceptance_fixture() if row["truth"] != "VALID"}
        self.assertEqual(gate.classify_submission(rows[gate.HOLD_RECEIPT_OVER_48H])["code"], gate.HOLD_RECEIPT_OVER_48H)
        self.assertEqual(gate.classify_submission(rows[gate.HOLD_MISSED_COURIER_CUTOFF])["code"], gate.HOLD_MISSED_COURIER_CUTOFF)
        self.assertEqual(gate.classify_submission(rows[gate.HOLD_BROKEN_COOLER_CUSTODY])["code"], gate.HOLD_BROKEN_COOLER_CUSTODY)
        self.assertEqual(
            gate.classify_submission(rows[gate.HOLD_FACILITY_METHOD_SCOPE_MISMATCH])["code"],
            gate.HOLD_FACILITY_METHOD_SCOPE_MISMATCH,
        )
        self.assertEqual(gate.classify_submission(rows[gate.HOLD_LEGACY_SITE_MAPPING])["code"], gate.HOLD_LEGACY_SITE_MAPPING)
        first = next(row for row in gate.build_acceptance_fixture() if row["truth"] == "VALID")
        dup = next(row for row in gate.build_acceptance_fixture() if row["truth"] == gate.HOLD_DUPLICATE_SAMPLE_ID)
        self.assertEqual(dup["sample_id"], first["sample_id"])
        self.assertEqual(
            gate.classify_submission(dup, {first["sample_id"]})["code"],
            gate.HOLD_DUPLICATE_SAMPLE_ID,
        )

    def test_held_row_never_creates_an_accession(self) -> None:
        journal = gate.empty_journal()
        hold = next(row for row in gate.build_acceptance_fixture() if row["truth"] == gate.HOLD_RECEIPT_OVER_48H)
        effect = gate.ingest_row(journal, hold)
        self.assertEqual(effect["kind"], "HOLD")
        self.assertEqual(len(journal["accessions"]), 0)
        self.assertEqual(journal["incumbent_writes"], 0)


if __name__ == "__main__":
    unittest.main()
