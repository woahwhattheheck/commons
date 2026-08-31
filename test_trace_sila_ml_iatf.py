#!/usr/bin/env python3
"""Binary acceptance for trace-sila-ml-iatf-lims-01."""

from __future__ import annotations

import unittest
from copy import deepcopy

import trace_sila_ml_iatf as gate


class TraceSilaMlIatfTests(unittest.TestCase):
    def test_acceptance_fixture_counts(self) -> None:
        fixture = gate.build_acceptance_fixture()
        self.assertEqual(fixture["fixture_id"], "SILA-ML-01")
        self.assertEqual(len(fixture["batches"]), 4)
        self.assertEqual(len(fixture["analytics"]), 13)
        unique_ids = [row["result_id"] for row in fixture["analytics"][:12]]
        self.assertEqual(len(set(unique_ids)), 12)
        self.assertEqual(fixture["analytics"][12]["result_id"], "B001-A01")

    def test_pass_contract_exact_counts_and_holds(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_analytics"], 13)
        self.assertEqual(result["canonical_results"], 12)
        self.assertEqual(result["duplicate_log"], 1)
        self.assertEqual(result["dossier_count"], 4)
        self.assertEqual(
            result["statuses"],
            {
                "B001": "REVIEW_READY",
                "B002": "HOLD_UNIT_MISMATCH",
                "B003": "HOLD_SPEC_OOS",
                "B004": "HOLD_GENEALOGY_GAP",
            },
        )
        self.assertEqual(result["duplicate_result_ids"], ["B001-A01"])
        self.assertEqual(len(set(result["result_ids"])), 12)
        self.assertEqual(result["released_dossiers"], 0)
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED_READONLY")
        self.assertFalse(result["adapter_writes"])
        self.assertFalse(result["recipes_mutated"])
        self.assertFalse(result["real_thresholds"])
        self.assertFalse(result["autonomous_certification"])
        self.assertFalse(result["autonomous_disposition"])
        self.assertTrue(result["human_disposition_mandatory"])
        self.assertTrue(result["incumbent_authoritative"])

    def test_hold_codes_and_owners_are_exact(self) -> None:
        result = gate.run_gate()
        by_batch = {item["batch_id"]: item for item in result["exceptions"]}
        self.assertEqual(by_batch["B002"]["code"], "HOLD_UNIT_MISMATCH")
        self.assertEqual(by_batch["B002"]["owner"], "QMS_METROLOGY")
        self.assertEqual(by_batch["B003"]["code"], "HOLD_SPEC_OOS")
        self.assertEqual(by_batch["B003"]["owner"], "QUALITY_ENGINEER")
        self.assertEqual(by_batch["B004"]["code"], "HOLD_GENEALOGY_GAP")
        self.assertEqual(by_batch["B004"]["owner"], "MES_GENEALOGY")
        self.assertNotIn("B001", by_batch)
        b002 = next(item for item in result["results"] if item["result_id"] == "B002-A03")
        self.assertEqual(b002["unit"], "wt_pct")
        self.assertEqual(b002["expected_unit"], "ppm")
        b003 = next(item for item in result["results"] if item["result_id"] == "B003-A03")
        self.assertEqual(b003["value"], 88.0)
        b004 = next(item for item in result["dossiers"] if item["batch_id"] == "B004")
        self.assertIsNone(b004["parent_lot"])

    def test_replay_identical_hashes_and_zero_new_results(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["dossier_hashes"], second["dossier_hashes"])
        self.assertEqual(len(first["manifest_sha256"]), 64)

        journal = gate.empty_journal()
        adapters = gate.bind_adapters()
        gate.ingest_fixture(journal, None, adapters)
        self.assertEqual(len(journal["results"]), 12)
        self.assertEqual(len(journal["duplicates"]), 1)
        replay = gate.replay_into(journal, None, adapters)
        self.assertEqual(replay["added_result_count"], 0)
        self.assertEqual(replay["added_duplicates"], 0)
        self.assertEqual(replay["canonical_results"], 12)
        self.assertEqual(replay["duplicate_count"], 1)

    def test_read_only_adapters_deny_writes_and_recipes(self) -> None:
        adapters = gate.bind_adapters()
        journal = gate.empty_journal()
        denials = gate.attempt_adapter_writes(adapters, journal)
        self.assertGreaterEqual(len(denials), 3)
        self.assertTrue(all(item["code"] == "ADAPTER_WRITE_DENIED" for item in denials))
        self.assertTrue(all(item["live"] is False for item in denials))
        self.assertFalse(adapters["mes"].live)
        self.assertEqual(len(adapters["mes"].export()), 4)
        self.assertEqual(len(adapters["analytics"].export()), 13)

    def test_human_disposition_required_and_autonomous_denied(self) -> None:
        journal = gate.empty_journal()
        adapters = gate.bind_adapters()
        gate.ingest_fixture(journal, None, adapters)
        for batch_id in ("B001", "B002", "B003", "B004"):
            denied = gate.release_dossier(
                journal, batch_id, actor_role="SYSTEM", actor="bot"
            )
            self.assertFalse(denied["ok"])
            self.assertEqual(denied["code"], "AUTONOMOUS_DISPOSITION_DENIED")
            self.assertFalse(journal["dossiers"][batch_id]["released"])

        hold = gate.release_dossier(
            journal, "B002", actor_role="HUMAN_DISPOSITION", actor="reviewer-1"
        )
        self.assertFalse(hold["ok"])
        self.assertEqual(hold["code"], "HUMAN_DISPOSITION_REQUIRED")
        self.assertFalse(journal["dossiers"]["B002"]["released"])

        human = gate.release_dossier(
            journal, "B001", actor_role="HUMAN_DISPOSITION", actor="reviewer-1"
        )
        self.assertTrue(human["ok"])
        self.assertEqual(journal["dossiers"]["B001"]["released_by"], "reviewer-1")
        self.assertEqual(journal["dossiers"]["B001"]["disposition_state"], "RELEASED")

    def test_fixture_only_thresholds_are_not_live_qms(self) -> None:
        self.assertEqual(gate.METHODS["IMPURITY_NA"]["threshold_source"], "FIXTURE_ONLY")
        result = gate.run_gate()
        self.assertEqual(result["threshold_source"], "FIXTURE_ONLY")
        for item in result["results"]:
            self.assertEqual(item["threshold_source"], "FIXTURE_ONLY")
            self.assertFalse(item["interface_live"])

    def test_no_live_interfaces_or_production_writes(self) -> None:
        result = gate.run_gate()
        for item in result["dossiers"]:
            self.assertFalse(item["interface_live"])
            self.assertTrue(item["incumbent_authoritative"])
            self.assertFalse(item["released"])
        self.assertTrue(
            all(
                item["code"] == "AUTONOMOUS_DISPOSITION_DENIED"
                for item in result["autonomous_disposition_effects"]
            )
        )
        self.assertTrue(
            all(item["code"] == "ADAPTER_WRITE_DENIED" for item in result["write_denials"])
        )

    def test_complete_audit_export_is_deterministic(self) -> None:
        journal = gate.empty_journal()
        adapters = gate.bind_adapters()
        gate.ingest_fixture(journal, None, adapters)
        first = gate.audit_export(journal)
        second = gate.audit_export(journal)
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(len(first["results"]), 12)
        self.assertEqual(len(first["duplicates"]), 1)
        self.assertEqual(len(first["dossiers"]), 4)
        self.assertGreaterEqual(len(first["events"]), 13)


if __name__ == "__main__":
    unittest.main()
