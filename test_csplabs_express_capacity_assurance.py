#!/usr/bin/env python3
"""Binary acceptance for csplabs-express-capacity-assurance-lims-01."""

from __future__ import annotations

import unittest

import csplabs_express_capacity_assurance as gate


class CspLabsExpressCapacityAssuranceTests(unittest.TestCase):
    def test_acceptance_fixture_is_240_with_40_exceptions(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 240)
        exceptions = {
            "MISSING_PHOTO": 0,
            "SHIPMENT_BARCODE_MISMATCH": 0,
            "UNSUPPORTED_SAMPLE_TEST": 0,
            "INCOMPLETE_LABEL": 0,
        }
        valid = 0
        for row in rows:
            if row["exception_type"]:
                exceptions[row["exception_type"]] += 1
            else:
                valid += 1
                self.assertEqual(row["crop"], "strawberry")
                self.assertEqual(row["assays"], list(gate.ASSAYS))
                self.assertEqual(row["sample_barcode"], row["shipment_barcode"])
                self.assertTrue(row["photo_id"])
        self.assertEqual(valid, 200)
        self.assertEqual(
            exceptions,
            {
                "MISSING_PHOTO": 10,
                "SHIPMENT_BARCODE_MISMATCH": 10,
                "UNSUPPORTED_SAMPLE_TEST": 10,
                "INCOMPLETE_LABEL": 10,
            },
        )

    def test_pass_contract_200_accessions_800_jobs_40_holds(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(
            counts["expected"],
            {
                "input_rows": 240,
                "accessioned": 200,
                "test_jobs": 800,
                "blocked": 40,
                "sla_same_day": 120,
                "sla_next_business_day": 80,
                "staffing_jobs": 800,
                "held_batch_jobs": 20,
                "ready_for_reviewer": 780,
                "released": 0,
            },
        )
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(len(set(result["accession_ids"])), 200)
        self.assertEqual(len(set(result["job_ids"])), 800)

    def test_forty_exceptions_are_blocked_with_exact_codes(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 40)
        self.assertEqual(
            result["hold_counts"],
            {
                "HOLD_MISSING_PHOTO": 10,
                "HOLD_SHIPMENT_BARCODE_MISMATCH": 10,
                "HOLD_UNSUPPORTED_SAMPLE_TEST": 10,
                "HOLD_INCOMPLETE_LABEL": 10,
            },
        )
        self.assertTrue(all(item["jobs_created"] == 0 for item in result["holds"]))
        missing = next(item for item in result["holds"] if item["row_id"] == "R0201")
        mismatch = next(item for item in result["holds"] if item["row_id"] == "R0211")
        unsupported = next(item for item in result["holds"] if item["row_id"] == "R0221")
        incomplete = next(item for item in result["holds"] if item["row_id"] == "R0231")
        self.assertEqual(missing["code"], "HOLD_MISSING_PHOTO")
        self.assertEqual(mismatch["code"], "HOLD_SHIPMENT_BARCODE_MISMATCH")
        self.assertEqual(unsupported["code"], "HOLD_UNSUPPORTED_SAMPLE_TEST")
        self.assertEqual(incomplete["code"], "HOLD_INCOMPLETE_LABEL")

    def test_sla_follows_signed_receipt_verification_and_business_day(self) -> None:
        self.assertEqual(
            gate.sla_class("2026-08-24T08:00:00-07:00", "2026-08-24T09:00:00-07:00"),
            "SAME_DAY",
        )
        self.assertEqual(
            gate.sla_class("2026-08-24T10:00:00-07:00", "2026-08-24T14:00:00-07:00"),
            "NEXT_BUSINESS_DAY",
        )
        self.assertEqual(
            gate.sla_class("2026-08-22T09:00:00-07:00", "2026-08-22T10:00:00-07:00"),
            "NEXT_BUSINESS_DAY",
        )
        self.assertEqual(
            gate.sla_class("2026-08-22T16:00:00-07:00", "2026-08-24T09:30:00-07:00"),
            "SAME_DAY",
        )
        result = gate.run_gate()
        self.assertEqual(result["sla_accessions"], {"SAME_DAY": 120, "NEXT_BUSINESS_DAY": 80})
        same = next(item for item in result["accessions"] if item["order_id"] == "ORD-0001")
        after_cutoff = next(item for item in result["accessions"] if item["order_id"] == "ORD-0081")
        weekend = next(item for item in result["accessions"] if item["order_id"] == "ORD-0121")
        monday_verify = next(item for item in result["accessions"] if item["order_id"] == "ORD-0161")
        self.assertEqual(same["sla_class"], "SAME_DAY")
        self.assertEqual(after_cutoff["sla_class"], "NEXT_BUSINESS_DAY")
        self.assertEqual(weekend["sla_class"], "NEXT_BUSINESS_DAY")
        self.assertEqual(monday_verify["sla_class"], "SAME_DAY")
        for job in result["jobs"]:
            if job["order_id"] == "ORD-0001":
                self.assertEqual(job["sla_class"], "SAME_DAY")
            if job["order_id"] == "ORD-0081":
                self.assertEqual(job["sla_class"], "NEXT_BUSINESS_DAY")

    def test_staffing_counts_equal_accepted_job_manifest(self) -> None:
        result = gate.run_gate()
        staffing = result["staffing"]
        manifest = result["accepted_job_manifest"]
        self.assertTrue(result["staffing_matches_manifest"])
        self.assertEqual(staffing["accepted_jobs"], 800)
        self.assertEqual(staffing["accepted_accessions"], 200)
        self.assertEqual(staffing["analyst_slots"], 800)
        self.assertEqual(staffing["job_ids"], manifest["job_ids"])
        self.assertEqual(len(manifest["jobs"]), 800)
        self.assertEqual(staffing["jobs_by_assay"], {"FOF": 200, "MP": 200, "PHY": 200, "VD": 200})
        self.assertEqual(staffing["plates_required"], 40)

    def test_seeded_failed_negative_control_holds_entire_batch(self) -> None:
        result = gate.run_gate()
        plate = result["plates"][gate.SEEDED_FAILED_PLATE]
        self.assertEqual(plate["ntc"], "FAIL")
        self.assertEqual(plate["qc_status"], "HOLD_NTC_FAIL")
        self.assertEqual(len(plate["job_ids"]), 20)
        held = [job for job in result["jobs"] if job["job_id"] in plate["job_ids"]]
        self.assertEqual(len(held), 20)
        self.assertTrue(all(job["batch_hold"] for job in held))
        self.assertTrue(all(job["qc_status"] == "HOLD_NTC_FAIL" for job in held))
        self.assertTrue(all(job["report_status"] == "HOLD_BATCH_NTC_FAIL" for job in held))
        self.assertEqual(result["held_batch_jobs"], 20)
        passing = [job for job in result["jobs"] if job["plate_id"] != gate.SEEDED_FAILED_PLATE]
        self.assertEqual(len(passing), 780)
        self.assertTrue(all(job["qc_status"] == "QC_PASS" for job in passing))

    def test_dashboard_and_report_digests_reconcile(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["dashboard"], first["report"])
        self.assertEqual(first["dashboard_digest"], first["report_digest"])
        self.assertTrue(first["digests_reconcile"])
        self.assertEqual(len(first["dashboard_digest"]), 64)
        self.assertEqual(first["dashboard_digest"], second["dashboard_digest"])
        self.assertEqual(first["report_digest"], second["report_digest"])
        self.assertEqual(gate.sha256_hex(first["dashboard"]), first["dashboard_digest"])

    def test_release_is_reviewer_only_and_held_batch_stays_blocked(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["released"], 0)
        self.assertEqual(result["released_reports"], 0)
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )
        self.assertFalse(result["autonomous_release"])
        self.assertEqual(result["automatic_releases"], 0)

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        gate.assign_plates(journal)
        ready = next(jid for jid, job in journal["jobs"].items() if job["report_status"] == "READY_FOR_REVIEWER")
        held = next(jid for jid, job in journal["jobs"].items() if job["batch_hold"])
        autonomous = gate.release_job(journal, ready, actor_role="SYSTEM", actor="bot")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        blocked = gate.release_job(journal, held, actor_role="REVIEWER", actor="reviewer-01")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "HOLD_BATCH_NTC_FAIL")
        human = gate.release_job(journal, ready, actor_role="REVIEWER", actor="reviewer-01")
        self.assertTrue(human["ok"])
        self.assertEqual(journal["jobs"][ready]["released_by"], "reviewer-01")
        self.assertFalse(journal["jobs"][held]["released"])

    def test_replay_creates_zero_accessions_or_jobs(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(len(first["manifest_sha256"]), 64)

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 200)
        self.assertEqual(len(journal["jobs"]), 800)
        self.assertEqual(len(journal["holds"]), 40)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_jobs"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["accession_count"], 200)
        self.assertEqual(replay["job_count"], 800)
        self.assertEqual(replay["hold_count"], 40)
        self.assertEqual(replay["replay_noops"], 200)

    def test_no_live_adapters_or_automatic_release(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["automatic_releases"], 0)
        self.assertFalse(result["autonomous_release"])
        self.assertEqual(result["pre_sale_transport"], "NONE")
        self.assertEqual(result["cash_usd"], 0)
        for item in result["accessions"]:
            self.assertEqual(item["route"], "EXPRESS_FOUR_ASSAY")
            self.assertEqual(item["assays"], list(gate.ASSAYS))
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            self.assertFalse(item["released"])


if __name__ == "__main__":
    unittest.main()
