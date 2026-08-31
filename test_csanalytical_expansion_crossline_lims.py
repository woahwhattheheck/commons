#!/usr/bin/env python3
"""Binary acceptance for csanalytical-expansion-crossline-evidence-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter
from copy import deepcopy

import csanalytical_expansion_crossline_lims as gate


class CsAnalyticalExpansionCrosslineLimsTests(unittest.TestCase):
    def test_acceptance_fixture_is_120_frozen_submissions(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 120)
        holds = [row["expected_hold"] for row in rows]
        self.assertEqual(holds.count(None), 90)
        self.assertEqual(holds.count("DUPLICATE_ID"), 8)
        self.assertEqual(holds.count("WRONG_LINE"), 7)
        self.assertEqual(holds.count("MISSING_METADATA"), 5)
        self.assertEqual(holds.count("QC_FAIL"), 5)
        self.assertEqual(holds.count("SOURCE_HASH_MISMATCH"), 5)
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
        self.assertEqual(result["staged_reports"], 90)
        self.assertEqual(result["hold_code_set"], sorted(gate.HOLD_CODES))
        self.assertEqual(Counter(result["hold_codes"]), Counter(gate.HOLD_PLAN))

    def test_thirty_holds_use_predetermined_codes_and_ids(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 30)
        by_code = {code: [] for code in gate.HOLD_CODES}
        for item in result["holds"]:
            by_code[item["code"]].append(item)
        self.assertEqual(
            sorted(item["submission_id"] for item in by_code["DUPLICATE_ID"]),
            [gate.valid_submission_id(i) for i in range(1, 9)],
        )
        self.assertEqual(
            sorted(item["submission_id"] for item in by_code["WRONG_LINE"]),
            ["CSA-WL%02d" % i for i in range(1, 8)],
        )
        self.assertEqual(
            sorted(item["submission_id"] for item in by_code["MISSING_METADATA"]),
            ["CSA-MS%02d" % i for i in range(1, 6)],
        )
        self.assertEqual(
            sorted(item["submission_id"] for item in by_code["QC_FAIL"]),
            ["CSA-QC%02d" % i for i in range(1, 6)],
        )
        self.assertEqual(
            sorted(item["submission_id"] for item in by_code["SOURCE_HASH_MISMATCH"]),
            ["CSA-SH%02d" % i for i in range(1, 6)],
        )

    def test_intake_holds_schedule_nothing(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["intake_holds"], 20)
        self.assertEqual(result["intake_holds_scheduled"], 0)
        scheduled_ids = {item["submission_id"] for item in result["accessions"] if item["scheduled"]}
        for item in result["holds"]:
            if item["intake_hold"]:
                self.assertFalse(item["scheduled"])
                if item["code"] in {"WRONG_LINE", "MISSING_METADATA"}:
                    self.assertNotIn(item["submission_id"], scheduled_ids)

    def test_no_held_record_stages_or_releases_a_report(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["held_staged"], 0)
        self.assertEqual(result["held_released"], 0)
        for item in result["accessions"]:
            if item["state"] == "HOLD":
                self.assertFalse(item["staged"])
                self.assertIsNone(item["report"])
                self.assertFalse(item["released"])
        for item in result["holds"]:
            self.assertFalse(item["staged"])
            self.assertFalse(item["released"])

    def test_cross_line_misroute_blocks_ccit_vs_material_gas_micro(self) -> None:
        result = gate.run_gate()
        ready = [item for item in result["accessions"] if item["state"] == "READY"]
        self.assertEqual(len(ready), 90)
        self.assertEqual(sorted({item["line"] for item in ready}), sorted(gate.LINES))
        first = next(item for item in ready if item["submission_id"] == "CSA-V001")
        self.assertEqual(first["line"], "CCIT")
        self.assertEqual(first["method"], "VACUUM_DECAY")
        self.assertEqual(first["method_version"], "ASTM-F2338-09")
        self.assertEqual(first["instrument_id"], "PTI-VERIPAC-455")
        self.assertTrue(first["staged"])
        journal = gate.empty_journal()
        for spec in gate.WRONG_LINE_SPECS:
            row = next(item for item in gate.build_acceptance_fixture() if item["submission_id"] == spec["submission_id"])
            effect = gate.ingest_row(journal, row)
            self.assertEqual(effect["kind"], "HOLD")
            self.assertEqual(effect["code"], "WRONG_LINE")
            self.assertFalse(effect["scheduled"])
        self.assertEqual(journal["jobs"], {})
        self.assertEqual(len(journal["holds"]), 7)

    def test_method_instrument_value_unit_audit_source_hashes_match(self) -> None:
        rows = {row["submission_id"]: row for row in gate.build_acceptance_fixture()}
        result = gate.run_gate()
        self.assertTrue(result["hashes_match"])
        for item in result["accessions"]:
            expected = rows[item["submission_id"]]
            self.assertEqual(
                item["method_hash"],
                gate.method_hash(item["method"], item["method_version"], item["line"]),
            )
            self.assertEqual(
                item["instrument_hash"],
                gate.instrument_hash(item["instrument_id"], item["run_id"]),
            )
            self.assertEqual(item["value_hash"], gate.value_hash(item["value"]))
            self.assertEqual(item["unit_hash"], gate.unit_hash(item["unit"]))
            self.assertEqual(
                item["audit_hash"],
                gate.audit_hash(
                    item["submission_id"],
                    item["study_id"],
                    item["line"],
                    item["method"],
                    item["instrument_id"],
                    item["run_id"],
                ),
            )
            computed_source = gate.source_hash(
                item["study_id"],
                item["sample_id"],
                item["lot_id"],
                item["product_id"],
                item["package_component"],
            )
            self.assertEqual(item["computed_source_hash"], computed_source)
            if expected["expected_hold"] is None:
                self.assertEqual(item["source_hash"], expected["source_hash"])
                self.assertEqual(item["source_hash"], computed_source)
                self.assertEqual(item["method_hash"], expected["method_hash"])
                self.assertEqual(item["instrument_hash"], expected["instrument_hash"])
                self.assertEqual(item["value_hash"], expected["value_hash"])
                self.assertEqual(item["unit_hash"], expected["unit_hash"])
                self.assertEqual(item["audit_hash"], expected["audit_hash"])

    def test_replay_adds_zero_records(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["report_digest"], second["report_digest"])
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(first["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(first["report_digest"], gate.GOLDEN_REPORT_DIGEST)
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

    def test_human_only_release_and_held_records_cannot_release(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["released_reports"], 0)
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
        unnamed = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="")
        self.assertFalse(unnamed["ok"])
        self.assertEqual(unnamed["code"], "AUTONOMOUS_RELEASE_DENIED")
        system = gate.release_report(journal, acc_id, actor_role="SYSTEM", actor="bot")
        self.assertEqual(system["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(record["released"])
        human = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="brandon-zurawlow-reviewer")
        self.assertTrue(human["ok"])
        self.assertEqual(record["report_status"], "RELEASED")
        self.assertEqual(record["released_by"], "brandon-zurawlow-reviewer")

        blocked = gate.empty_journal()
        qc = next(item for item in gate.build_acceptance_fixture() if item["expected_hold"] == "QC_FAIL")
        mismatch = next(
            item for item in gate.build_acceptance_fixture() if item["expected_hold"] == "WRONG_LINE"
        )
        gate.ingest_row(blocked, qc)
        gate.ingest_row(blocked, mismatch)
        self.assertEqual(len(blocked["jobs"]), 1)
        held_id = next(iter(blocked["jobs"]))
        denied = gate.release_report(blocked, held_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "HELD_RECORD_NO_RELEASE")
        self.assertFalse(blocked["jobs"][held_id]["released"])
        self.assertIsNone(blocked["jobs"][held_id]["report"])

    def test_no_live_interfaces_or_compliance_decision(self) -> None:
        result = gate.run_gate()
        for item in result["accessions"]:
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            self.assertIsNone(item["compliance_decision"])
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertFalse(result["autonomous_certification"])
        self.assertFalse(result["autonomous_release"])
        self.assertFalse(result["compliance_decision"])
        self.assertEqual(result["compliance_decisions"], 0)
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["pre_sale_transport"], "NONE")


if __name__ == "__main__":
    unittest.main()
