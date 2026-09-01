#!/usr/bin/env python3
"""Acceptance tests for kca-ky-medical-cannabis-intake-lims-01."""

from __future__ import annotations

import unittest
from copy import deepcopy

import kca_ky_medical_cannabis_intake_lims as gate


class KcaKyMedicalCannabisIntakeLimsTests(unittest.TestCase):
    def test_frozen_fixture_is_100_with_exact_75_25_oracle(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 100)
        self.assertEqual(
            sum(row["expected_state"] == "READY" for row in rows), 75
        )
        self.assertEqual(
            sum(row["expected_state"] == "HOLD" for row in rows), 25
        )
        counts = {
            code: sum(row["expected_hold"] == code for row in rows)
            for code in gate.HOLD_CODES
        }
        self.assertEqual(counts, gate.HOLD_COUNTS)
        self.assertEqual(
            gate.fixture_sha256(rows), gate.GOLDEN_FIXTURE_SHA256
        )

    def test_contract_is_exactly_75_ready_and_25_hold(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 100)
        self.assertEqual(result["ready"], 75)
        self.assertEqual(result["holds"], 25)
        self.assertEqual(result["accessions"], 75)
        self.assertEqual(result["work_orders"], 75)
        self.assertEqual(result["draft_coas_staged"], 75)
        self.assertEqual(result["coas_released"], 0)
        self.assertEqual(result["hold_counts"], gate.HOLD_COUNTS)

    def test_every_predetermined_hold_schedules_zero_work(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {
            item["row_id"]: item for item in result["hold_records"]
        }
        self.assertEqual(len(holds), 25)
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["row_id"]]
            self.assertEqual(hold["code"], row["expected_hold"])
            self.assertEqual(hold["state"], "HOLD")
            self.assertEqual(hold["accessions_created"], 0)
            self.assertEqual(hold["work_orders_created"], 0)
            self.assertEqual(hold["results_created"], 0)
            self.assertEqual(hold["draft_coas_staged"], 0)
            self.assertEqual(hold["coas_released"], 0)

    def test_license_portal_coc_physical_and_matrix_stay_bound(self) -> None:
        rows = gate.build_acceptance_fixture()
        by_order = {
            row["order_id"]: row
            for row in rows
            if row["expected_state"] == "READY"
        }
        result = gate.run_gate(rows)
        self.assertEqual(len(result["accession_records"]), 75)
        for accession in result["accession_records"]:
            source = by_order[accession["order_id"]]
            self.assertEqual(accession["portal_order_id"], source["portal_order_id"])
            self.assertEqual(accession["license_number"], source["license_number"])
            self.assertEqual(accession["coc_form_id"], source["coc_form_id"])
            self.assertEqual(accession["physical_receipt_id"], source["physical_receipt_id"])
            self.assertEqual(accession["package_tag"], source["package_tag"])
            self.assertEqual(accession["manifest_id"], source["manifest_id"])
            self.assertEqual(accession["sample_id"], source["sample_id"])
            self.assertEqual(accession["matrix"], source["matrix"])
            self.assertEqual(accession["received_weight_g"], source["received_weight_g"])
            self.assertEqual(
                accession["source_sha256"],
                source["golden_hashes"]["source_sha256"],
            )

    def test_every_partner_result_carries_lab_method_source_hash(self) -> None:
        result = gate.run_gate()
        results_by_id = {res["result_id"]: res for res in result["result_records"]}
        
        partner_results = [
            res for res in result["result_records"]
            if res["lab_role"] == "PARTNER"
        ]
        self.assertGreater(len(partner_results), 0)
        
        for res in partner_results:
            self.assertTrue(res["lab_id"].startswith("SYN-PARTNER-"))
            self.assertTrue(len(res["method"]) > 0)
            self.assertTrue(len(res["method_version"]) > 0)
            self.assertTrue(res["source_uri"].startswith("synthetic://partner-lab-transfer/"))
            self.assertEqual(len(res["source_raw_hash"]), 64)
            self.assertEqual(len(res["provenance_hash"]), 64)
            
            # Recalculate provenance hash
            expected_prov = gate._calculate_provenance_hash(res)
            self.assertEqual(res["provenance_hash"], expected_prov)

    def test_coa_is_draft_stage_only_and_hash_is_golden(self) -> None:
        result = gate.run_gate()
        for coa in result["coa_records"]:
            self.assertEqual(coa["stage"], "DRAFT")
            self.assertFalse(coa["released"])
            self.assertIsNone(coa["released_by"])
            self.assertEqual(len(coa["coa_sha256"]), 64)

    def test_replay_adds_zero_and_changed_payload_conflicts(self) -> None:
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_order(journal, row)

        replay = gate.replay_into(journal, rows)
        self.assertEqual(
            replay,
            {
                "added_accessions": 0,
                "added_work_orders": 0,
                "added_results": 0,
                "added_coas": 0,
                "added_holds": 0,
                "replay_noops": 100,
                "replay_conflicts": 0,
            },
        )

        changed = deepcopy(rows[0])
        changed["received_weight_g"] = 99.99
        before = gate.canonical_json(journal)
        conflict = gate.ingest_order(journal, changed)
        self.assertEqual(conflict["kind"], "REPLAY_CONFLICT")
        self.assertEqual(conflict["code"], "REPLAY_PAYLOAD_CONFLICT")
        self.assertEqual(gate.canonical_json(journal), before)

    def test_release_requires_authorized_named_human_reviewer(self) -> None:
        journal = gate.empty_journal()
        ready = gate.ingest_order(
            journal, gate.build_acceptance_fixture()[0]
        )
        coa_id = ready["coa_id"]
        before = gate.canonical_json(journal)

        # Automation or empty identity denied
        for auto_id in ("", "SYSTEM", "AUTO", "METRC_SYNC"):
            with self.subTest(auto_id=auto_id):
                denied = gate.release_draft_coa(
                    journal, coa_id, reviewer_id=auto_id
                )
                self.assertEqual(
                    denied, {"ok": False, "code": "AUTONOMOUS_RELEASE_DENIED"}
                )
                self.assertEqual(gate.canonical_json(journal), before)

        # Unauthorized self-asserted reviewer denied
        unknown = gate.release_draft_coa(
            journal, coa_id, reviewer_id="self-asserted-analyst"
        )
        self.assertEqual(
            unknown, {"ok": False, "code": "UNAUTHORIZED_REVIEWER"}
        )
        self.assertEqual(gate.canonical_json(journal), before)

        # Authorized named human release succeeds
        released = gate.release_draft_coa(
            journal,
            coa_id,
            reviewer_id="SYN-HUMAN-KCA-REVIEWER-01",
        )
        self.assertTrue(released["ok"])
        self.assertEqual(released["status"], "RELEASED")
        self.assertEqual(
            journal["draft_coas"][coa_id]["released_by"]["display_name"],
            "Dr. Richard Sams (Synthetic Principal Reviewer)",
        )

    def test_invalid_and_non_synthetic_orders_fail_closed(self) -> None:
        journal = gate.empty_journal()
        baseline = gate.canonical_json(journal)
        for malformed in ("garbage", [1], 1, True, None):
            with self.subTest(malformed=repr(malformed)):
                result = gate.ingest_order(journal, malformed)  # type: ignore[arg-type]
                self.assertEqual(result["kind"], "REJECT")
                self.assertEqual(result["code"], "REJECT_INVALID_INPUT")
                self.assertEqual(gate.canonical_json(journal), baseline)

        non_synthetic = deepcopy(gate.build_acceptance_fixture()[0])
        non_synthetic["synthetic"] = False
        held = gate.ingest_order(journal, non_synthetic)
        self.assertEqual(held["kind"], "HOLD")
        self.assertEqual(held["code"], "HOLD_TRUTH_BOUNDARY")
        self.assertEqual(len(journal["accessions"]), 0)
        self.assertEqual(len(journal["draft_coas"]), 0)

    def test_adapter_is_synthetic_read_only_and_forbids_state_metrc_writes(
        self,
    ) -> None:
        adapter = gate.SyntheticReadOnlyOrderAdapter(
            gate.build_acceptance_fixture()
        )
        self.assertEqual(adapter.mode, "SYNTHETIC_READ_ONLY")
        self.assertFalse(adapter.live)
        self.assertEqual(adapter.writes, 0)
        with self.assertRaises(RuntimeError):
            adapter.write({"order_id": "nope"})


if __name__ == "__main__":
    unittest.main()
