#!/usr/bin/env python3
"""Binary acceptance for qlabs-qconnect-cutover-verification-lims-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNNER_PATH = ROOT / "revenue" / "qlabs_qconnect_cutover" / "runner.py"
SPEC = importlib.util.spec_from_file_location("qlabs_qconnect_cutover_runner", RUNNER_PATH)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gate)


class QLabsQConnectCutoverTests(unittest.TestCase):
    def test_acceptance_fixture_is_240_split_200_40(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 240)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "ACCESSION"), 200)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "HOLD"), 40)
        valid = [row for row in rows if row["expected_state"] == "ACCESSION"]
        self.assertEqual(sum(1 for row in valid if row["product_class"] == "personal_care"), 100)
        self.assertEqual(sum(1 for row in valid if row["product_class"] == "pharma"), 100)
        loaded = gate.load_fixture()
        self.assertEqual(len(loaded), 240)
        self.assertEqual(
            [row["case_id"] for row in loaded],
            [row["case_id"] for row in rows],
        )

    def test_pass_contract_exact_counts_routes_and_hashes(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.EXPECTED_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["manifest_sha256"], gate.GOLDEN_MANIFEST_SHA256)
        self.assertEqual(result["catalog_sha256"], gate.GOLDEN_CATALOG_SHA256)
        self.assertEqual(result["catalog_sha256"], gate.CATALOG_SHA256)
        self.assertEqual(len(result["audit_sha256"]), 64)

    def test_every_exception_stays_held_with_truth_set_reason(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {item["case_id"]: item for item in result["holds"]}
        self.assertEqual(len(holds), 40)
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["case_id"]]
            self.assertEqual(hold["code"], row["expected_hold_code"])
            self.assertEqual(hold["state"], "HOLD")
            self.assertFalse(hold["entered_testing"])
            self.assertIsNone(hold["test_job"])
        self.assertEqual(result["hold_code_counts"], gate.HOLD_FAMILY_COUNTS)
        accounted = {item["case_id"] for item in result["accessions"]} | set(holds)
        self.assertEqual(accounted, {row["case_id"] for row in rows})

    def test_valid_accessions_route_once_with_complete_provenance(self) -> None:
        result = gate.run_gate()
        self.assertTrue(result["provenance_complete"])
        self.assertEqual(len(set(result["accession_ids"])), 200)
        for item in result["accessions"]:
            self.assertEqual(item["state"], "ACCESSIONED")
            self.assertEqual(item["route"], item["department"] + ":" + item["product_class"] + ":" + item["test_code"])
            self.assertEqual(item["credential_kind"], "per_user")
            self.assertFalse(item["entered_testing"])
            self.assertEqual(item["test_job"]["state"], "ROUTED")
            self.assertFalse(item["test_job"]["entered_testing"])
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            prov = item["provenance"]
            self.assertEqual(len(prov["source_row_sha256"]), 64)
            self.assertEqual(prov["catalog_sha256"], gate.CATALOG_SHA256)
            self.assertEqual(prov["catalog_version"], gate.CATALOG_VERSION)
            self.assertEqual(set(prov["field_sha256"]), set(gate.REQUIRED_FIELDS))
            self.assertTrue(prov["user_id"])
            self.assertTrue(prov["account_id"])

    def test_obsolete_codes_never_enter_testing(self) -> None:
        result = gate.run_gate()
        obsolete = [item for item in result["holds"] if item["code"] == "OBSOLETE_CODE"]
        self.assertEqual(len(obsolete), 8)
        for item in obsolete:
            self.assertFalse(item["entered_testing"])
            self.assertIsNone(item["test_job"])
            self.assertIn(item["test_code"], gate.OBSOLETE)
        self.assertEqual(result["obsolete_in_testing"], 0)
        self.assertEqual(result["testing_entered"], 0)

    def test_shared_credentials_are_denied(self) -> None:
        result = gate.run_gate()
        shared = [item for item in result["holds"] if item["code"] == "SHARED_CREDENTIAL"]
        self.assertEqual(len(shared), 2)
        self.assertEqual(result["shared_credential_accessions"], 0)
        for item in shared:
            self.assertEqual(item["provenance"]["account_id"], gate.SHARED["account_id"])
            self.assertEqual(item["provenance"]["user_id"], gate.SHARED["user_id"])
        journal = gate.empty_journal()
        shared_row = {
            "case_id": "QCC-SHARED-PROBE",
            "submission_id": "SUB-SHARED-PROBE",
            "account_id": gate.SHARED["account_id"],
            "user_id": gate.SHARED["user_id"],
            "credential_kind": "shared",
            "catalog_version": gate.CATALOG_VERSION,
            "test_code": "QC-PC-ML61",
            "department": "MICROBIOLOGY",
            "product_class": "personal_care",
            "sample_id": "SYN-SHARED",
            "lot_id": "LOT-000",
            "product_name": "SYN-SHARED",
            "simulate_timeout": False,
        }
        effect = gate.ingest_row(journal, shared_row)
        self.assertEqual(effect["kind"], "HOLD")
        self.assertEqual(effect["code"], "SHARED_CREDENTIAL")
        self.assertEqual(len(journal["accessions"]), 0)

    def test_retries_create_zero_duplicates(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(first["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 200)
        self.assertEqual(len(journal["holds"]), 40)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["replay_noops"], 240)
        timeout = next(row for row in rows if row["expected_hold_code"] == "TIMEOUT_RETRY")
        again = gate.ingest_row(journal, timeout)
        self.assertEqual(again["kind"], "REPLAY_NOOP")
        self.assertEqual(len(journal["accessions"]), 200)

    def test_human_qa_releases_the_build_autonomous_denied(self) -> None:
        result = gate.run_gate()
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )
        self.assertEqual(result["autonomous_released"], 0)
        self.assertFalse(result["released"])
        self.assertEqual(result["build_state"], gate.TRUTH_GATE)
        journal = result["journal"]
        system_try = gate.release_build(journal, role_name="SYSTEM", releaser="automation")
        self.assertFalse(system_try["ok"])
        self.assertEqual(system_try["code"], "AUTONOMOUS_RELEASE_DENIED")
        other_try = gate.release_build(journal, role_name="HUMAN_QA", releaser="someone-else")
        self.assertEqual(other_try["code"], "NAMED_HUMAN_QA_REQUIRED")
        human = gate.release_build(journal, role_name="HUMAN_QA", releaser="SYN-QA-OFFICER")
        self.assertTrue(human["ok"])
        self.assertEqual(journal["build_state"], "HUMAN_QA_RELEASED")
        self.assertEqual(journal["released_by"], "SYN-QA-OFFICER")

    def test_no_live_interfaces_or_production_writes(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["shadowing"], "READ_ONLY")
        self.assertEqual(result["production_writes"], 0)
        self.assertFalse(result["outreach"])
        self.assertEqual(result["pre_sale_transport"], "NONE")
        self.assertEqual(result["cash_usd"], 0)
        for item in result["accessions"]:
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            self.assertFalse(item["released"])


if __name__ == "__main__":
    unittest.main()
