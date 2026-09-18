#!/usr/bin/env python3
"""Binary acceptance for slo-cls-cutover-evidence-lims-01."""

from __future__ import annotations

import unittest
from copy import deepcopy

import slo_cls_cutover_evidence as gate


class SloClsCutoverEvidenceTests(unittest.TestCase):
    def test_acceptance_fixture_is_1000_split_850_150(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 1000)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "READY"), 850)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "HOLD"), 150)
        holds = [row for row in rows if row["expected_state"] == "HOLD"]
        codes = [row["expected_hold"] for row in holds]
        self.assertEqual(codes.count("DUPLICATE_ID"), 50)
        self.assertEqual(codes.count("BROKEN_SAMPLE_TEST_REF"), 40)
        self.assertEqual(codes.count("METHOD_VERSION_CONFLICT"), 30)
        self.assertEqual(codes.count("HASH_MISMATCH"), 30)
        self.assertEqual(len({row["bundle_id"] for row in rows}), 1000)

    def test_pass_contract_exact_counts_and_integrity(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.EXPECTED_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["ready"], 850)
        self.assertEqual(result["holds"], 150)
        self.assertEqual(result["mapped"], 850)
        self.assertEqual(result["orphans"], 0)
        self.assertEqual(result["duplicates"], 0)
        self.assertEqual(result["released_results"], 0)
        self.assertEqual(result["released_reports"], 0)
        self.assertTrue(result["rollback_restored_baseline"])
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["shadowing"], "READ_ONLY")
        self.assertFalse(result["public_health_interpretation"])
        self.assertFalse(result["autonomous_release"])
        self.assertEqual(result["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)
        self.assertEqual(result["catalog_sha256"], gate.GOLDEN_CATALOG_SHA256)
        self.assertEqual(result["manifest_sha256"], gate.GOLDEN_MANIFEST_SHA256)
        self.assertEqual(result["baseline_hash"], gate.GOLDEN_BASELINE_SHA256)
        self.assertEqual(result["restored_hash"], gate.GOLDEN_BASELINE_SHA256)

    def test_every_hold_receives_predetermined_code(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {item["bundle_id"]: item for item in result["hold_records"]}
        self.assertEqual(len(holds), 150)
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["bundle_id"]]
            self.assertEqual(hold["code"], row["expected_hold"])
            self.assertEqual(hold["state"], "HOLD")
            self.assertFalse(hold["mapped"])
        accounted = {item["legacy_id"] for item in result["ready_records"]} | {
            item["bundle_id"] for item in result["hold_records"]
        }
        self.assertEqual(len(accounted), 1000)

    def test_every_valid_object_maps_once_with_zero_orphans(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["mappings"]), 850)
        self.assertEqual(len(set(result["mappings"].values())), 850)
        self.assertEqual(len(set(result["ready_ids"])), 850)
        self.assertEqual(len(set(result["cls_ids"])), 850)
        self.assertEqual(result["orphans"], 0)
        self.assertEqual(result["duplicates"], 0)
        self.assertEqual(result["hold_mapped"], [])
        for record in result["ready_records"]:
            self.assertTrue(record["mapped"])
            self.assertEqual(result["mappings"][record["legacy_id"]], record["cls_id"])
            self.assertEqual(record["interface_state"], "SIMULATED")
            self.assertFalse(record["interface_live"])
            self.assertIsNone(record["interpretation"])
            self.assertIsNone(record["report"]["public_health_call"])
            self.assertIsNone(record["report"]["interpretation"])
            self.assertNotIn("call", record["result"])
            self.assertNotIn("detected", record["result"])

    def test_replay_creates_nothing_and_hashes_match(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(len(first["manifest_sha256"]), 64)
        self.assertEqual(first["fixture_sha256"], second["fixture_sha256"])
        self.assertEqual(first["replay_added_mappings"], 0)
        self.assertEqual(first["replay_added_objects"], 0)
        self.assertEqual(first["replay_ingest_noops"], 850)

        journal = gate.empty_journal()
        cls_adapter = gate.SimulatedClsAdapter()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_bundle(journal, row)
        first_migrate = gate.migrate(journal, cls_adapter)
        self.assertEqual(first_migrate["added_mappings"], 850)
        replay = gate.migrate(journal, cls_adapter)
        self.assertEqual(replay["added_mappings"], 0)
        self.assertEqual(replay["added_objects"], 0)
        self.assertEqual(replay["mapped"], 850)
        self.assertEqual(len(cls_adapter.objects), 850)
        ingest_replay = [gate.ingest_bundle(journal, row) for row in rows]
        self.assertEqual(sum(1 for item in ingest_replay if item["kind"] == "REPLAY_NOOP"), 850)
        self.assertEqual(len(journal["ready"]), 850)
        self.assertEqual(len(journal["holds"]), 150)

    def test_rollback_restores_exact_baseline(self) -> None:
        rows = gate.build_acceptance_fixture()
        journal = gate.empty_journal()
        cls_adapter = gate.SimulatedClsAdapter()
        cls_adapter.put("SEED-KEEP", {"cls_id": "SEED-KEEP", "marker": "baseline"})
        baseline = cls_adapter.snapshot()
        self.assertEqual(cls_adapter.baseline_hash(), baseline)
        for row in rows:
            gate.ingest_bundle(journal, row)
        moved = gate.migrate(journal, cls_adapter)
        self.assertEqual(moved["added_objects"], 850)
        self.assertEqual(len(cls_adapter.objects), 851)
        after = cls_adapter.baseline_hash()
        self.assertNotEqual(after, baseline)
        restored = cls_adapter.rollback(baseline)
        self.assertTrue(restored["ok"])
        self.assertEqual(cls_adapter.baseline_hash(), baseline)
        self.assertEqual(set(cls_adapter.objects), {"SEED-KEEP"})
        self.assertEqual(cls_adapter.objects["SEED-KEEP"]["marker"], "baseline")

    def test_no_result_or_report_release_without_named_approval(self) -> None:
        rows = gate.build_acceptance_fixture()
        journal = gate.empty_journal()
        cls_adapter = gate.SimulatedClsAdapter()
        gate.ingest_bundle(journal, rows[0])
        gate.migrate(journal, cls_adapter)
        legacy_id = next(iter(journal["ready"]))
        record = journal["ready"][legacy_id]

        missing = gate.release_result(journal, cls_adapter, legacy_id, named_approver="")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["code"], "MISSING_NAMED_APPROVAL")
        self.assertFalse(record["released_result"])

        auto = gate.release_result(journal, cls_adapter, legacy_id, named_approver="SYSTEM")
        self.assertFalse(auto["ok"])
        self.assertEqual(auto["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(record["released_result"])

        report_first = gate.release_report(journal, cls_adapter, legacy_id, named_approver=gate.HUMAN_APPROVER)
        self.assertFalse(report_first["ok"])
        self.assertEqual(report_first["code"], "RESULT_NOT_RELEASED")
        self.assertFalse(record["released_report"])

        named = gate.release_result(journal, cls_adapter, legacy_id, named_approver=gate.HUMAN_APPROVER)
        self.assertTrue(named["ok"])
        self.assertEqual(record["released_by"], gate.HUMAN_APPROVER)
        report = gate.release_report(journal, cls_adapter, legacy_id, named_approver=gate.HUMAN_APPROVER)
        self.assertTrue(report["ok"])
        self.assertTrue(record["released_report"])

    def test_incumbent_adapter_is_read_only(self) -> None:
        adapter = gate.SimulatedIncumbentAdapter(gate.build_acceptance_fixture())
        self.assertEqual(adapter.mode, "READ_ONLY")
        self.assertFalse(adapter.live)
        self.assertEqual(len(adapter.list_bundles()), 1000)
        with self.assertRaises(RuntimeError):
            adapter.write({"bundle_id": "nope"})

    def test_accession_channels_and_panther_catalog(self) -> None:
        result = gate.run_gate()
        channels = result["accession_channels"]
        self.assertEqual(channels["REQUISITION"] + channels["PORTAL"], 850)
        self.assertGreater(channels["REQUISITION"], 0)
        self.assertGreater(channels["PORTAL"], 0)
        for record in result["ready_records"]:
            spec = gate.PANTHER_FUSION_CATALOG[record["method"]]
            self.assertIn(record["method_version"], spec["versions"])
            self.assertEqual(record["sample_test_ref"], f"{record['sample_id']}->{record['test_id']}")
            self.assertEqual(gate.sha256_hex(record["result"]), record["result_hash"])
            self.assertEqual(gate.sha256_hex(record["report"]), record["report_hash"])
            self.assertEqual(gate.sha256_hex(record["source"]), record["source_hash"])


if __name__ == "__main__":
    unittest.main()
