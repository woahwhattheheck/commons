#!/usr/bin/env python3
"""Binary acceptance for slo-cls-cutover-evidence-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter
from copy import deepcopy

import slo_cls_cutover_evidence as gate


class SloClsCutoverEvidenceTests(unittest.TestCase):
    def test_acceptance_fixture_is_1000_frozen_bundles(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 1000)
        holds = [row["expected_hold"] for row in rows]
        self.assertEqual(holds.count(None), 850)
        self.assertEqual(holds.count("DUPLICATE_ID"), 50)
        self.assertEqual(holds.count("BROKEN_SAMPLE_TEST_REF"), 40)
        self.assertEqual(holds.count("METHOD_VERSION_CONFLICT"), 30)
        self.assertEqual(holds.count("REPORT_RESULT_HASH_MISMATCH"), 30)
        self.assertEqual(gate.fixture_manifest()["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)

    def test_pass_contract_expected_equals_actual(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.GOLDEN_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["ready"], 850)
        self.assertEqual(result["held"], 150)
        self.assertEqual(result["mapped_once"], 850)
        self.assertEqual(result["orphans"], 0)
        self.assertEqual(result["duplicate_mappings"], 0)
        self.assertEqual(result["rollback_restored"], 1)
        self.assertEqual(Counter(result["hold_codes"]), Counter(gate.HOLD_PLAN))

    def test_one_hundred_fifty_holds_use_exact_truth_set_codes(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 150)
        by_code = {code: [] for code in gate.HOLD_CODES}
        for item in result["holds"]:
            by_code[item["code"]].append(item)
        self.assertEqual(len(by_code["DUPLICATE_ID"]), 50)
        self.assertEqual(len(by_code["BROKEN_SAMPLE_TEST_REF"]), 40)
        self.assertEqual(len(by_code["METHOD_VERSION_CONFLICT"]), 30)
        self.assertEqual(len(by_code["REPORT_RESULT_HASH_MISMATCH"]), 30)
        self.assertTrue(all(item["state"] == "HOLD" for item in result["holds"]))
        self.assertTrue(all(item["mapped"] is False and item["cls_id"] is None for item in result["holds"]))

    def test_every_valid_object_maps_once_with_unique_cls_ids(self) -> None:
        result = gate.run_gate()
        incumbents = [item["incumbent_id"] for item in result["accessions"]]
        cls_ids = [item["cls_id"] for item in result["accessions"]]
        self.assertEqual(len(incumbents), 850)
        self.assertEqual(len(set(incumbents)), 850)
        self.assertEqual(len(set(cls_ids)), 850)
        self.assertTrue(all(item.startswith("CLS-") for item in cls_ids))
        self.assertEqual(result["mappings"][gate.incumbent_id(1)], result["accessions"][0]["cls_id"])

    def test_source_method_result_report_hashes_match(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["lineage_sha256"], gate.GOLDEN_LINEAGE_SHA256)
        self.assertEqual(result["baseline_sha256"], gate.GOLDEN_BASELINE_SHA256)
        for item in result["accessions"]:
            self.assertEqual(
                item["source_hash"],
                gate.source_hash(item["accession_id"], item["sample_id"], item["test_id"]),
            )
            self.assertEqual(item["method_hash"], gate.method_hash(item["method"], item["method_version"]))
            self.assertEqual(item["result_hash"], gate.result_hash(item["raw"]))
            self.assertEqual(item["report_hash"], gate.report_hash(item["accession_id"], item["result_hash"]))
            self.assertEqual(item["report"]["state"], "STAGED")
            self.assertFalse(item["released"])

    def test_replay_creates_nothing(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["lineage_sha256"], second["lineage_sha256"])
        self.assertEqual(first["baseline_sha256"], second["baseline_sha256"])
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 850)
        self.assertEqual(len(journal["holds"]), 150)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_record_count"], 0)
        self.assertEqual(replay["accession_count"], 850)
        self.assertEqual(replay["hold_count"], 150)
        self.assertEqual(replay["replay_noops"], 1000)

    def test_rollback_restores_exact_baseline(self) -> None:
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        baseline = gate.snapshot_baseline(journal)
        self.assertEqual(baseline, gate.GOLDEN_BASELINE_SHA256)
        gate.migrate(journal)
        self.assertEqual(len(journal["mappings"]), 850)
        self.assertTrue(journal["migrated"])
        rolled = gate.rollback(journal)
        self.assertTrue(rolled["ok"])
        self.assertEqual(rolled["restored_sha256"], baseline)
        self.assertEqual(journal["mappings"], {})
        self.assertFalse(journal["migrated"])
        self.assertTrue(all(item["cls_id"] is None for item in journal["accessions"].values()))

    def test_named_human_release_only(self) -> None:
        journal = gate.empty_journal()
        row = next(item for item in gate.build_acceptance_fixture() if item["expected_hold"] is None)
        gate.ingest_row(journal, row)
        acc_id = next(iter(journal["accessions"]))
        autonomous = gate.release_report(journal, acc_id, actor_role="SYSTEM", actor="bot")
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        unnamed = gate.release_report(journal, acc_id, actor_role="APPROVER", actor="someone-else")
        self.assertEqual(unnamed["code"], "NAMED_HUMAN_REQUIRED")
        human = gate.release_report(journal, acc_id, actor_role="APPROVER", actor="glen-m-miller")
        self.assertTrue(human["ok"])
        self.assertEqual(journal["accessions"][acc_id]["released_by"], "glen-m-miller")

    def test_no_live_interfaces_or_public_health_decision(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertFalse(result["autonomous_release"])
        self.assertFalse(result["public_health_decision"])
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["pre_sale_transport"], "NONE")
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )


if __name__ == "__main__":
    unittest.main()
