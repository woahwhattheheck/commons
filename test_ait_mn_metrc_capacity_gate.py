#!/usr/bin/env python3
"""Binary acceptance for ait-mn-metrc-capacity-gate-lims-01."""

from __future__ import annotations

import unittest

import ait_mn_metrc_capacity_gate as gate


class AitMnMetrcCapacityGateTests(unittest.TestCase):
    def test_acceptance_fixture_row_mix(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 120)
        kinds = [item["kind"] for item in rows]
        self.assertEqual(kinds.count("VALID_COMPLIANCE"), 80)
        self.assertEqual(kinds.count("VALID_RND"), 20)
        self.assertEqual(kinds.count("MISSING_LICENSE"), 4)
        self.assertEqual(kinds.count("INVALID_LICENSE"), 4)
        self.assertEqual(kinds.count("DUPLICATE"), 6)
        self.assertEqual(kinds.count("DESIGNATION_MISMATCH"), 6)

    def test_pass_contract_exact_counts_and_queues(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 120)
        self.assertEqual(result["accessioned"], 100)
        self.assertEqual(result["held"], 20)
        self.assertEqual(result["compliance_queue"], 80)
        self.assertEqual(result["rnd_queue"], 20)
        self.assertEqual(result["compliance_release_queue"], 0)
        self.assertEqual(result["rnd_in_compliance_release"], 0)
        self.assertEqual(result["hold_code_counts"]["INVALID_OR_MISSING_LICENSE"], 8)
        self.assertEqual(result["hold_code_counts"]["DUPLICATE_PACKAGE_OR_SAMPLE"], 6)
        self.assertEqual(result["hold_code_counts"]["DESIGNATION_MISMATCH"], 6)
        self.assertEqual(len(set(result["accession_ids"])), 100)
        self.assertEqual(result["released_coas"], 0)
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "READ_ONLY")
        self.assertFalse(result["metrc_write"])
        self.assertFalse(result["autonomous_release"])

    def test_every_record_has_immutable_source_pointers(self) -> None:
        result = gate.run_gate()
        records = list(result["accessions"]) + list(result["holds"])
        self.assertEqual(len(records), 120)
        hashes = []
        for record in records:
            self.assertTrue(gate._has_provenance(record))
            pointers = record["source_pointers"]
            self.assertEqual(pointers["qbench"]["adapter"], "qbench")
            self.assertEqual(pointers["metrc"]["adapter"], "metrc")
            self.assertEqual(pointers["physical"]["adapter"], "physical")
            hashes.append(record["provenance_sha256"])
        self.assertEqual(len(set(hashes)), 120)

    def test_rnd_stays_segregated_from_compliance_release(self) -> None:
        result = gate.run_gate()
        rnd = [item for item in result["accessions"] if item["designation"] == "R_AND_D"]
        self.assertEqual(len(rnd), 20)
        self.assertTrue(all(item["queue"] == "rnd" for item in rnd))
        self.assertTrue(all(item["released"] is False for item in rnd))
        self.assertEqual(len(result["rnd_release_effects"]), 20)
        self.assertTrue(all(item["code"] == "RND_SEGREGATED" for item in result["rnd_release_effects"]))

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        rnd_id = journal["rnd_queue"][0]
        staged = gate.stage_for_release(journal, rnd_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertFalse(staged["ok"])
        self.assertEqual(staged["code"], "RND_SEGREGATED")
        released = gate.release_to_compliance(journal, rnd_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertFalse(released["ok"])
        self.assertEqual(released["code"], "RND_SEGREGATED")
        self.assertEqual(journal["compliance_release_queue"], [])
        self.assertEqual(journal["accessions"][rnd_id]["queue"], "rnd")

    def test_replay_identical_hashes_and_zero_new_records(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(len(first["manifest_sha256"]), 64)

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 100)
        self.assertEqual(len(journal["holds"]), 20)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["accession_count"], 100)
        self.assertEqual(replay["hold_count"], 20)
        self.assertEqual(replay["replay_noops"], 100)

    def test_named_human_release_after_reviewer_staging(self) -> None:
        journal = gate.empty_journal()
        compliance = next(item for item in gate.build_acceptance_fixture() if item["kind"] == "VALID_COMPLIANCE")
        gate.ingest_row(journal, compliance)
        acc_id = next(iter(journal["accessions"]))

        autonomous = gate.release_to_compliance(journal, acc_id, actor_role="SYSTEM", actor="bot")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")

        unnamed = gate.stage_for_release(journal, acc_id, actor_role="RELEASER", actor="")
        self.assertEqual(unnamed["code"], "NAMED_HUMAN_REQUIRED")
        unstaged = gate.release_to_compliance(journal, acc_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertEqual(unstaged["code"], "NOT_STAGED")

        staged = gate.stage_for_release(journal, acc_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertTrue(staged["ok"])
        human = gate.release_to_compliance(journal, acc_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertTrue(human["ok"])
        record = journal["accessions"][acc_id]
        self.assertEqual(record["released_by"], "reviewer-1")
        self.assertFalse(record["coa_released"])
        self.assertEqual(journal["compliance_release_queue"], [acc_id])

    def test_read_only_adapters_refuse_writes(self) -> None:
        row = gate.build_acceptance_fixture()[0]
        qbench = gate.ReadOnlyQBenchAdapter()
        metrc = gate.ReadOnlyMetrcAdapter()
        physical = gate.ReadOnlyPhysicalAdapter()
        self.assertEqual(qbench.fetch_order(row)["mode"], "READ_ONLY")
        self.assertEqual(metrc.fetch_package(row)["mode"], "READ_ONLY")
        self.assertEqual(physical.fetch_accession(row)["mode"], "READ_ONLY")
        with self.assertRaises(gate.AdapterWriteDenied):
            qbench.write({"order": "nope"})
        with self.assertRaises(gate.AdapterWriteDenied):
            metrc.write({"package": "nope"})
        with self.assertRaises(gate.AdapterWriteDenied):
            metrc.submit_result({"coa": "nope"})
        with self.assertRaises(gate.AdapterWriteDenied):
            physical.write({"accession": "nope"})

    def test_duplicate_and_mismatch_codes_are_exact(self) -> None:
        result = gate.run_gate()
        dups = [item for item in result["holds"] if item["code"] == "DUPLICATE_PACKAGE_OR_SAMPLE"]
        mismatches = [item for item in result["holds"] if item["code"] == "DESIGNATION_MISMATCH"]
        licenses = [item for item in result["holds"] if item["code"] == "INVALID_OR_MISSING_LICENSE"]
        self.assertEqual(len(dups), 6)
        self.assertEqual(len(mismatches), 6)
        self.assertEqual(len(licenses), 8)
        first_pkg = next(item["package_id"] for item in result["accessions"] if item["row_id"] == "C001")
        self.assertTrue(any(item["package_id"] == first_pkg for item in dups))

    def test_no_automatic_coa_or_live_metrc(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["released_coas"], 0)
        self.assertFalse(result["metrc_write"])
        self.assertFalse(result["state_write"])
        for item in result["accessions"]:
            self.assertEqual(item["interface_state"], "READ_ONLY")
            self.assertFalse(item["interface_live"])
            self.assertFalse(item["coa_released"])
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )


if __name__ == "__main__":
    unittest.main()
