#!/usr/bin/env python3
"""Binary acceptance for wadsworth-five-site-consolidation-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter

import wadsworth_five_site_consolidation_lims as gate


class WadsworthFiveSiteConsolidationLimsTests(unittest.TestCase):
    def test_acceptance_fixture_is_2000_split_1700_300(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 2000)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "READY"), 1700)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "HOLD"), 300)
        codes = [row["expected_hold"] for row in rows if row["expected_state"] == "HOLD"]
        self.assertEqual(codes.count("DUPLICATE_NAMESPACE_ID"), 100)
        self.assertEqual(codes.count("METHOD_VERSION_CONFLICT"), 80)
        self.assertEqual(codes.count("BROKEN_REFERENCE"), 60)
        self.assertEqual(codes.count("FACILITY_CUSTODY_MISMATCH"), 60)
        self.assertEqual(len({row["bundle_id"] for row in rows}), 2000)
        self.assertEqual(gate.fixture_manifest()["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)
        self.assertEqual(gate.CATALOG_SHA256, gate.GOLDEN_CATALOG_SHA256)

    def test_pass_contract_exactly_1700_ready_300_hold(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.EXPECTED_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["ready"], 1700)
        self.assertEqual(result["holds"], 300)
        self.assertEqual(result["mapped"], 13600)
        self.assertEqual(result["target_objects"], 13600)
        self.assertEqual(result["orphans"], 0)
        self.assertEqual(result["duplicates"], 0)
        self.assertEqual(result["released"], 0)
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
        self.assertEqual(Counter(result["hold_codes"]), Counter(gate.HOLD_FAMILY_COUNTS))

    def test_every_hold_receives_predetermined_code(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {item["bundle_id"]: item for item in result["hold_records"]}
        self.assertEqual(len(holds), 300)
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["bundle_id"]]
            self.assertEqual(hold["code"], row["expected_hold"])
            self.assertEqual(hold["state"], "HOLD")
            self.assertFalse(hold["mapped"])
        accounted = set(result["ready_ids"]) | set(holds)
        self.assertEqual(len(accounted), 2000)

    def test_every_valid_object_maps_once_with_originating_site_and_source_hashes(self) -> None:
        rows = {row["bundle_id"]: row for row in gate.build_acceptance_fixture()}
        result = gate.run_gate()
        self.assertEqual(len(result["mappings"]), 13600)
        self.assertEqual(len(set(result["mappings"].values())), 13600)
        self.assertEqual(len(set(result["namespace_ids"])), 13600)
        self.assertEqual(len(set(result["target_ids"])), 13600)
        self.assertEqual(result["orphans"], 0)
        self.assertEqual(result["duplicates"], 0)
        self.assertEqual(result["hold_mapped"], [])
        for record in result["ready_records"]:
            src = rows[record["bundle_id"]]
            self.assertTrue(record["mapped"])
            self.assertEqual(record["originating_site_hash"], src["originating_site_hash"])
            self.assertEqual(record["source_hash"], src["source_hash"])
            self.assertEqual(record["originating_site_hash"], gate.sha256_hex({
                "bundle_id": src["bundle_id"],
                "originating_site": src["originating_site"],
                "namespace_ids": [obj["namespace_id"] for obj in src["objects"]],
            }))
            self.assertEqual(record["source_hash"], gate.sha256_hex(gate._source_payload(src)))
            self.assertEqual(len(record["namespace_ids"]), 8)
            self.assertEqual(set(record["kinds"]), set(gate.OBJECT_KINDS))
            for namespace_id, target_id, kind, obj_hash in zip(
                record["namespace_ids"],
                record["target_ids"],
                record["kinds"],
                record["object_originating_site_hashes"],
            ):
                self.assertEqual(result["mappings"][namespace_id], target_id)
                src_obj = next(obj for obj in src["objects"] if obj["kind"] == kind)
                self.assertEqual(obj_hash, src_obj["originating_site_hash"])
                self.assertEqual(obj_hash, gate.sha256_hex(gate._originating_site_payload(src, src_obj)))
            self.assertIsNone(record["interpretation"])
            self.assertIsNone(record["public_health_call"])
            self.assertIsNone(record["diagnostic_call"])
            self.assertEqual(record["target_site"], gate.TARGET_SITE)
            self.assertFalse(record["interface_live"])

    def test_zero_orphans_and_duplicates_across_five_sites(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["orphans"], 0)
        self.assertEqual(result["duplicates"], 0)
        self.assertEqual(sum(result["site_counts"].values()), 1700)
        self.assertEqual(set(result["site_counts"]), set(gate.SITES))
        for site, count in result["site_counts"].items():
            self.assertGreater(count, 0)
            self.assertEqual(site.startswith("SYN-"), True)
        self.assertEqual(result["site_counts"]["SYN-ALB-AXELROD"], 340)
        self.assertEqual(result["site_counts"]["SYN-ALB-BIGGS"], 340)
        self.assertEqual(result["site_counts"]["SYN-GLD-GRIFFIN"], 340)
        self.assertEqual(result["site_counts"]["SYN-ALB-EMPIRE"], 340)
        self.assertEqual(result["site_counts"]["SYN-GLD-CULTURE"], 340)

    def test_replay_is_idempotent(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(len(first["manifest_sha256"]), 64)
        self.assertEqual(first["fixture_sha256"], second["fixture_sha256"])
        self.assertEqual(first["replay_added_mappings"], 0)
        self.assertEqual(first["replay_added_objects"], 0)
        self.assertEqual(first["replay_ingest_noops"], 1700)
        self.assertEqual(gate.sha256_hex(gate.cli_payload(first)), gate.sha256_hex(gate.cli_payload(second)))

        journal = gate.empty_journal()
        target = gate.SimulatedHarrimanNamespaceAdapter()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_bundle(journal, row)
        first_migrate = gate.migrate(journal, target)
        self.assertEqual(first_migrate["added_mappings"], 13600)
        replay = gate.migrate(journal, target)
        self.assertEqual(replay["added_mappings"], 0)
        self.assertEqual(replay["added_objects"], 0)
        self.assertEqual(replay["mapped"], 13600)
        self.assertEqual(len(target.objects), 13600)
        ingest_replay = [gate.ingest_bundle(journal, row) for row in rows]
        self.assertEqual(sum(1 for item in ingest_replay if item["kind"] == "REPLAY_NOOP"), 1700)
        self.assertEqual(len(journal["ready"]), 1700)
        self.assertEqual(len(journal["holds"]), 300)

    def test_rollback_restores_exact_baseline(self) -> None:
        rows = gate.build_acceptance_fixture()
        journal = gate.empty_journal()
        target = gate.SimulatedHarrimanNamespaceAdapter()
        target.put("SEED-KEEP", {"target_id": "SEED-KEEP", "marker": "baseline"})
        baseline = target.snapshot()
        self.assertEqual(target.baseline_hash(), baseline)
        for row in rows:
            gate.ingest_bundle(journal, row)
        moved = gate.migrate(journal, target)
        self.assertEqual(moved["added_objects"], 13600)
        self.assertEqual(len(target.objects), 13601)
        after = target.baseline_hash()
        self.assertNotEqual(after, baseline)
        restored = target.rollback(baseline)
        self.assertTrue(restored["ok"])
        self.assertEqual(target.baseline_hash(), baseline)
        self.assertEqual(set(target.objects), {"SEED-KEEP"})
        self.assertEqual(target.objects["SEED-KEEP"]["marker"], "baseline")

    def test_named_human_release_gate_denies_autonomous(self) -> None:
        rows = gate.build_acceptance_fixture()
        journal = gate.empty_journal()
        target = gate.SimulatedHarrimanNamespaceAdapter()
        gate.ingest_bundle(journal, rows[0])
        gate.migrate(journal, target)
        bundle_id = next(iter(journal["ready"]))
        record = journal["ready"][bundle_id]

        missing = gate.release_mapped(journal, target, bundle_id, named_approver="")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["code"], "MISSING_NAMED_APPROVAL")
        self.assertFalse(record["released"])

        auto = gate.release_mapped(journal, target, bundle_id, named_approver="SYSTEM")
        self.assertFalse(auto["ok"])
        self.assertEqual(auto["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(record["released"])

        named = gate.release_mapped(journal, target, bundle_id, named_approver=gate.HUMAN_APPROVER)
        self.assertTrue(named["ok"])
        self.assertEqual(record["released_by"], gate.HUMAN_APPROVER)
        self.assertTrue(record["released"])
        self.assertEqual(named["released_by"], gate.HUMAN_APPROVER)

    def test_source_adapter_is_read_only_target_is_simulated(self) -> None:
        adapter = gate.SimulatedFiveSiteSourceAdapter(gate.build_acceptance_fixture())
        self.assertEqual(adapter.mode, "READ_ONLY")
        self.assertFalse(adapter.live)
        self.assertEqual(len(adapter.list_bundles()), 2000)
        with self.assertRaises(RuntimeError):
            adapter.write({"bundle_id": "nope"})
        target = gate.SimulatedHarrimanNamespaceAdapter()
        self.assertEqual(target.mode, "SIMULATED")
        self.assertFalse(target.live)
        self.assertEqual(target.production_writes, 0)


if __name__ == "__main__":
    unittest.main()
