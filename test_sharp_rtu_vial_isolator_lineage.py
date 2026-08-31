#!/usr/bin/env python3
"""Binary acceptance for sharp-rtu-vial-isolator-lineage-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter

import sharp_rtu_vial_isolator_lineage as gate


class SharpRtuVialIsolatorLineageLimsTests(unittest.TestCase):
    def test_acceptance_fixture_is_120_frozen_records(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 120)
        holds = [row["expected_hold"] for row in rows]
        self.assertEqual(holds.count(None), 90)
        self.assertEqual(holds.count("DUPLICATE_COMPONENT_BATCH"), 8)
        self.assertEqual(holds.count("FORMAT_LINE_MISMATCH"), 7)
        self.assertEqual(holds.count("MISSING_METHOD_VERSION"), 5)
        self.assertEqual(holds.count("WEIGHT_SLOT_CONFLICT"), 5)
        self.assertEqual(holds.count("QC_STERILITY_FAIL"), 5)
        self.assertEqual(gate.fixture_manifest()["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)

    def test_pass_contract_exactly_90_ready_30_hold(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.GOLDEN_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["ready"], 90)
        self.assertEqual(result["held"], 30)
        self.assertEqual(result["jobs"], 100)
        self.assertEqual(result["staged_packs"], 90)
        self.assertEqual(result["hold_code_set"], sorted(gate.HOLD_CODES))
        self.assertEqual(Counter(result["hold_codes"]), Counter(gate.HOLD_PLAN))

    def test_thirty_holds_use_predetermined_codes_and_ids(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 30)
        by_code = {code: [] for code in gate.HOLD_CODES}
        for item in result["holds"]:
            by_code[item["code"]].append(item)
        self.assertEqual(
            sorted(item["submission_id"] for item in by_code["DUPLICATE_COMPONENT_BATCH"]),
            ["SHP-DB%02d" % i for i in range(1, 9)],
        )
        self.assertEqual(
            sorted(item["submission_id"] for item in by_code["FORMAT_LINE_MISMATCH"]),
            ["SHP-FM%02d" % i for i in range(1, 8)],
        )
        self.assertEqual(
            sorted(item["submission_id"] for item in by_code["MISSING_METHOD_VERSION"]),
            ["SHP-MV%02d" % i for i in range(1, 6)],
        )
        self.assertEqual(
            sorted(item["submission_id"] for item in by_code["WEIGHT_SLOT_CONFLICT"]),
            ["SHP-WS%02d" % i for i in range(1, 6)],
        )
        self.assertEqual(
            sorted(item["submission_id"] for item in by_code["QC_STERILITY_FAIL"]),
            ["SHP-QC%02d" % i for i in range(1, 6)],
        )
        fixture = gate.build_acceptance_fixture()
        for offset in range(8):
            original = fixture[offset]
            hold = next(
                item
                for item in by_code["DUPLICATE_COMPONENT_BATCH"]
                if item["submission_id"] == "SHP-DB%02d" % (offset + 1)
            )
            self.assertEqual(hold["component_id"], original["component_id"])
            self.assertEqual(hold["batch_id"], original["batch_id"])

    def test_intake_holds_schedule_no_line_jobs(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["intake_holds"], 20)
        self.assertEqual(result["intake_holds_scheduled"], 0)
        scheduled_ids = {item["submission_id"] for item in result["accessions"] if item["scheduled"]}
        for item in result["holds"]:
            if item["intake_hold"]:
                self.assertFalse(item["scheduled"])
                if item["code"] in {
                    "FORMAT_LINE_MISMATCH",
                    "MISSING_METHOD_VERSION",
                    "DUPLICATE_COMPONENT_BATCH",
                }:
                    self.assertNotIn(item["submission_id"], scheduled_ids)

    def test_no_held_record_stages_or_releases_evidence(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["held_staged"], 0)
        self.assertEqual(result["held_released"], 0)
        for item in result["accessions"]:
            if item["state"] == "HOLD":
                self.assertFalse(item["staged"])
                self.assertIsNone(item["evidence_pack"])
                self.assertFalse(item["released"])
        for item in result["holds"]:
            self.assertFalse(item["staged"])
            self.assertFalse(item["released"])

    def test_rtu_vial_isolator_and_lyo_routes_bind_valid_records(self) -> None:
        result = gate.run_gate()
        ready = [item for item in result["accessions"] if item["state"] == "READY"]
        self.assertEqual(len(ready), 90)
        self.assertEqual(sorted({item["line"] for item in ready}), sorted(gate.LINES))
        self.assertEqual(sorted({item["format"] for item in ready}), sorted(gate.FORMATS))
        first = next(item for item in ready if item["submission_id"] == "SHP-V001")
        self.assertEqual(first["line"], "ISOLATOR_FILL")
        self.assertEqual(first["format"], "RTU_2R")
        self.assertEqual(first["method"], "FILL_WEIGHT")
        self.assertEqual(first["method_version"], "FW-2R-v3")
        self.assertTrue(first["staged"])
        self.assertIsNotNone(first["evidence_pack"])
        journal = gate.empty_journal()
        for spec in gate.FORMAT_LINE_SPECS:
            row = next(
                item
                for item in gate.build_acceptance_fixture()
                if item["submission_id"] == spec["submission_id"]
            )
            effect = gate.ingest_row(journal, row)
            self.assertEqual(effect["kind"], "HOLD")
            self.assertEqual(effect["code"], "FORMAT_LINE_MISMATCH")
            self.assertFalse(effect["scheduled"])
        self.assertEqual(journal["jobs"], {})
        self.assertEqual(len(journal["holds"]), 7)

    def test_cycle_weight_result_unit_source_hashes_match(self) -> None:
        rows = {row["submission_id"]: row for row in gate.build_acceptance_fixture()}
        result = gate.run_gate()
        self.assertTrue(result["hashes_match"])
        for item in result["accessions"]:
            expected = rows[item["submission_id"]]
            self.assertEqual(
                item["cycle_hash"],
                gate.cycle_hash(
                    item["cycle_id"],
                    item["lyo_recipe"],
                    item["lyo_shelf"],
                    item["primary_drying_h"],
                    item["secondary_drying_h"],
                ),
            )
            self.assertEqual(
                item["weight_hash"],
                gate.weight_hash(item["fill_weight_mg"], item["format"], item["unit"]),
            )
            self.assertEqual(item["result_hash"], gate.result_hash(item["value"]))
            self.assertEqual(item["unit_hash"], gate.unit_hash(item["unit"]))
            computed_source = gate.source_hash(
                item["sponsor_id"],
                item["tech_transfer_id"],
                item["material_id"],
                item["batch_id"],
                item["component_id"],
            )
            self.assertEqual(item["computed_source_hash"], computed_source)
            if expected["expected_hold"] is None:
                self.assertEqual(item["source_hash"], expected["source_hash"])
                self.assertEqual(item["source_hash"], computed_source)
                self.assertEqual(item["cycle_hash"], expected["cycle_hash"])
                self.assertEqual(item["weight_hash"], expected["weight_hash"])
                self.assertEqual(item["result_hash"], expected["result_hash"])
                self.assertEqual(item["unit_hash"], expected["unit_hash"])

    def test_replay_adds_zero_records(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["evidence_digest"], second["evidence_digest"])
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(first["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(first["evidence_digest"], gate.GOLDEN_EVIDENCE_DIGEST)
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["jobs"]), 100)
        self.assertEqual(len(journal["holds"]), 30)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_job_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["job_count"], 100)
        self.assertEqual(replay["hold_count"], 30)

    def test_human_only_named_release_and_held_records_cannot_release(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["released_packs"], 0)
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )
        journal = gate.empty_journal()
        valid = next(item for item in gate.build_acceptance_fixture() if item["expected_hold"] is None)
        gate.ingest_row(journal, valid)
        acc_id = next(iter(journal["jobs"]))
        record = journal["jobs"][acc_id]
        self.assertEqual(record["state"], "READY")
        self.assertTrue(record["staged"])
        unnamed = gate.release_pack(journal, acc_id, actor_role="RELEASER", actor="")
        self.assertFalse(unnamed["ok"])
        self.assertEqual(unnamed["code"], "AUTONOMOUS_RELEASE_DENIED")
        system = gate.release_pack(journal, acc_id, actor_role="SYSTEM", actor="bot")
        self.assertEqual(system["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(record["released"])
        human = gate.release_pack(journal, acc_id, actor_role="RELEASER", actor="james-hamilton-qa")
        self.assertTrue(human["ok"])
        self.assertEqual(record["pack_status"], "RELEASED")
        self.assertEqual(record["released_by"], "james-hamilton-qa")

        blocked = gate.empty_journal()
        qc = next(item for item in gate.build_acceptance_fixture() if item["expected_hold"] == "QC_STERILITY_FAIL")
        mismatch = next(
            item for item in gate.build_acceptance_fixture() if item["expected_hold"] == "FORMAT_LINE_MISMATCH"
        )
        gate.ingest_row(blocked, qc)
        gate.ingest_row(blocked, mismatch)
        self.assertEqual(len(blocked["jobs"]), 1)
        held_id = next(iter(blocked["jobs"]))
        denied = gate.release_pack(blocked, held_id, actor_role="RELEASER", actor="james-hamilton-qa")
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "HELD_RECORD_NO_RELEASE")
        self.assertFalse(blocked["jobs"][held_id]["released"])
        self.assertIsNone(blocked["jobs"][held_id]["evidence_pack"])

    def test_no_live_interfaces_or_gmp_decision(self) -> None:
        result = gate.run_gate()
        for item in result["accessions"]:
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            self.assertIsNone(item["compliance_decision"])
            self.assertIsNone(item["gmp_decision"])
            self.assertIsNone(item["clinical_decision"])
            self.assertIsNone(item["public_health_decision"])
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertFalse(result["autonomous_certification"])
        self.assertFalse(result["autonomous_release"])
        self.assertFalse(result["compliance_decision"])
        self.assertFalse(result["gmp_decision"])
        self.assertFalse(result["clinical_decision"])
        self.assertFalse(result["public_health_decision"])
        self.assertEqual(result["compliance_decisions"], 0)
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["pre_sale_transport"], "NONE")
        self.assertEqual(result["cash_usd"], 0)


if __name__ == "__main__":
    unittest.main()
