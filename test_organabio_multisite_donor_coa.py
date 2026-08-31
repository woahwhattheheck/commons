#!/usr/bin/env python3
"""Binary acceptance for organabio-multisite-donor-coa-lims-01."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import organabio_multisite_donor_coa as gate

FIXTURE = Path("revenue/organabio_multisite_donor_coa/fixture.json")


class OrganabioMultisiteDonorCoaTests(unittest.TestCase):
    def test_acceptance_numbers_240_1200_24_40(self) -> None:
        rows = gate.build_acceptance_fixture()
        valid = [row for row in rows if row["kind"] == "COLLECTION"]
        failures = [row for row in rows if row["kind"] == "FAILURE"]
        recalls = [row for row in valid if row["recall"]]
        self.assertEqual(len(valid), 240)
        self.assertEqual(len(failures), 24)
        self.assertEqual(len(recalls), 40)
        self.assertEqual(240 * gate.ALIQUOTS_PER_COLLECTION, 1200)
        by_site = {code: 0 for code in gate.SITES}
        for row in valid:
            by_site[row["site"]] += 1
        self.assertEqual(by_site, {code: 48 for code in gate.SITES})

    def test_fixture_json_encodes_the_same_acceptance_numbers(self) -> None:
        self.assertTrue(FIXTURE.is_file())
        doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
        expected = doc["expected"]
        self.assertEqual(expected["valid_collections"], 240)
        self.assertEqual(expected["aliquots"], 1200)
        self.assertEqual(expected["failures"], 24)
        self.assertEqual(expected["recalls"], 40)
        seed = doc["seed"]
        self.assertEqual(sum(1 for row in seed if row["kind"] == "COLLECTION"), 240)
        self.assertEqual(sum(1 for row in seed if row["kind"] == "FAILURE"), 24)
        self.assertEqual(sum(1 for row in seed if row.get("recall")), 40)
        self.assertEqual(doc["demand_id"], "organabio-multisite-donor-coa-lims-01")
        self.assertEqual(doc["cash_usd"], 0)
        self.assertFalse(doc["live_lims"])
        self.assertFalse(doc["production_deployment"])

    def test_pass_contract_and_expected_actual_match(self) -> None:
        result = gate.run_federation()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(
            counts["expected"],
            {
                "valid_collections": 240,
                "aliquots": 1200,
                "failures": 24,
                "recalls": 40,
                "human_released": 1200,
                "autonomous_released": 0,
                "recall_aliquots": 200,
            },
        )
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])

    def test_every_valid_aliquot_has_exactly_one_immutable_lineage(self) -> None:
        result = gate.run_federation()
        self.assertEqual(result["aliquots"], 1200)
        self.assertTrue(result["one_lineage_per_aliquot"])
        hashes = [item["lineage_hash"] for item in result["aliquot_records"]]
        self.assertEqual(len(hashes), 1200)
        self.assertEqual(len(set(hashes)), 1200)
        self.assertEqual(len(result["lineages"]), 1200)
        sample = result["aliquot_records"][0]
        mutated = gate.mutate_lineage(
            {
                "lineages": {sample["aliquot_id"]: result["lineages"][sample["aliquot_id"]]},
                "aliquots": {},
            },
            sample["aliquot_id"],
            "SYN-OBA-MIA-DNR-99",
        )
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        target = next(iter(journal["aliquots"]))
        blocked = gate.mutate_lineage(journal, target, "SYN-FORGED-DONOR")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "IMMUTABLE_LINEAGE")
        self.assertEqual(mutated["code"], "IMMUTABLE_LINEAGE")

    def test_site_namespaces_never_collide(self) -> None:
        result = gate.run_federation()
        self.assertEqual(result["namespace_collisions"], [])
        self.assertEqual(result["site_counts"], {code: 48 for code in gate.SITES})
        prefixes = [gate.site_namespace(code) for code in gate.SITES]
        self.assertEqual(len(set(prefixes)), 5)
        for item in result["aliquot_records"]:
            self.assertTrue(item["aliquot_id"].startswith(item["namespace"] + "-"))
            self.assertTrue(item["donor_id"].startswith("SYN-" + item["namespace"] + "-"))
        excellos = [key for key in result["legacy_map"] if key.startswith("EXL-")]
        self.assertEqual(len(excellos), 48)
        self.assertTrue(all(value.startswith("OBA-SDG-") for value in result["legacy_map"].values()))
        federated = set(result["legacy_map"].values())
        self.assertEqual(len(federated), 48)

    def test_invalid_collections_block_with_exact_reason(self) -> None:
        result = gate.run_federation()
        self.assertEqual(len(result["failure_records"]), 24)
        self.assertEqual(
            result["failure_code_counts"],
            {
                "BLOCK_CONSENT_MISSING": 6,
                "BLOCK_CONSENT_WITHDRAWN": 6,
                "BLOCK_ELIGIBILITY_INFECTIOUS": 6,
                "BLOCK_ELIGIBILITY_TRAVEL": 6,
            },
        )
        for item in result["failure_records"]:
            self.assertEqual(item["state"], "BLOCKED")
            self.assertEqual(item["aliquots"], 0)
            self.assertIsNone(item["lineage"])
            self.assertIn(item["code"], gate.FAILURE_CODES)

    def test_recall_returns_all_and_only_expected_aliquots(self) -> None:
        result = gate.run_federation()
        self.assertEqual(result["recalls"], 40)
        self.assertTrue(result["recall"]["ok"])
        self.assertEqual(result["recall"]["aliquot_count"], 200)
        self.assertEqual(result["recall"]["extras"], [])
        self.assertEqual(result["recall"]["missing"], [])
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        donor = "SYN-OBA-MIA-DNR-01"
        one = gate.recall_donor(journal, donor)
        self.assertTrue(one["ok"])
        self.assertTrue(one["exact"])
        self.assertEqual(len(one["aliquot_ids"]), 5)
        self.assertEqual(one["aliquot_ids"], one["expected"])
        stranger = gate.recall_donor(journal, "SYN-OBA-MIA-DNR-09")
        self.assertFalse(stranger["ok"])
        self.assertEqual(stranger["code"], "NOT_A_RECALL_DONOR")

    def test_coa_and_lineage_digests_match_golden(self) -> None:
        result = gate.run_federation()
        self.assertEqual(result["coa_sha256"], gate.GOLDEN_COA_SHA256)
        self.assertEqual(result["lineage_sha256"], gate.GOLDEN_LINEAGE_SHA256)
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["coa_sha256"], "3f3f9ab647c6d7e34cce48fc002c86150b3d83285b78de30e5ff25a0a845db01")
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["expected"]["coa_sha256"], result["coa_sha256"])
        self.assertEqual(fixture["expected"]["lineage_sha256"], result["lineage_sha256"])
        self.assertEqual(fixture["expected"]["audit_sha256"], result["audit_sha256"])

    def test_replay_is_idempotent(self) -> None:
        first = gate.run_federation()
        second = gate.run_federation()
        self.assertEqual(first["coa_sha256"], second["coa_sha256"])
        self.assertEqual(first["lineage_sha256"], second["lineage_sha256"])
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        journal = gate.empty_journal()
        seed = gate.build_acceptance_fixture()
        for row in seed:
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["collections"]), 240)
        self.assertEqual(len(journal["aliquots"]), 1200)
        self.assertEqual(len(journal["failures"]), 24)
        replay = gate.replay_into(journal, seed)
        self.assertEqual(replay["added_collection_count"], 0)
        self.assertEqual(replay["added_aliquots"], 0)
        self.assertEqual(replay["added_failures"], 0)
        self.assertEqual(replay["collection_count"], 240)
        self.assertEqual(replay["aliquot_count"], 1200)
        self.assertEqual(replay["failure_count"], 24)
        self.assertEqual(replay["replay_noops"], 264)

    def test_no_material_disposition_without_named_human_quality_release(self) -> None:
        journal = gate.empty_journal()
        raw = next(item for item in gate.build_acceptance_fixture() if item["kind"] == "COLLECTION")
        gate.ingest_row(journal, raw)
        alq = next(iter(journal["aliquots"]))
        blocked = gate.dispose_material(journal, alq, actor_role="QA_RELEASER", actor="qa-human-01")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "HUMAN_RELEASE_REQUIRED")
        autonomous = gate.release_aliquot(journal, alq, actor_role="SYSTEM", actor="bot")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        still = gate.dispose_material(journal, alq, actor_role="SYSTEM", actor="bot")
        self.assertEqual(still["code"], "HUMAN_RELEASE_REQUIRED")
        result = gate.run_federation()
        self.assertEqual(result["human_released"], 1200)
        self.assertEqual(result["autonomous_released"], 0)
        self.assertEqual(result["material_disposition"], 0)
        self.assertEqual(result["live_movement"], 0)
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["cash_usd"], 0)
        released_alq = result["aliquot_records"][0]["aliquot_id"]
        live = gate.dispose_material(
            {
                "aliquots": {released_alq: result["aliquot_records"][0]},
                "events": [],
            },
            released_alq,
            actor_role="QA_RELEASER",
            actor="qa-human-01",
        )
        self.assertFalse(live["ok"])
        self.assertEqual(live["code"], "SIMULATED_ONLY_NO_LIVE_MOVEMENT")


if __name__ == "__main__":
    unittest.main()
