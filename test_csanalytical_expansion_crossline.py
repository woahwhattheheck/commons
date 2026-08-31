#!/usr/bin/env python3
"""Binary acceptance for csanalytical-expansion-crossline-evidence-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter
from copy import deepcopy

import csanalytical_expansion_crossline as gate


class CsAnalyticalExpansionCrosslineTests(unittest.TestCase):
    def test_acceptance_fixture_is_120_frozen_submissions(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 120)
        holds = [row["expected_hold"] for row in rows]
        self.assertEqual(holds.count(None), 90)
        self.assertEqual(holds.count("DUPLICATE_ID"), 8)
        self.assertEqual(holds.count("WRONG_LINE_METHOD"), 7)
        self.assertEqual(holds.count("MISSING_STUDY_PACKAGE"), 5)
        self.assertEqual(holds.count("INSTRUMENT_QC_FAILURE"), 5)
        self.assertEqual(holds.count("SOURCE_HASH_MISMATCH"), 5)
        self.assertEqual(gate.fixture_manifest()["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)

    def test_pass_contract_expected_equals_actual(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.GOLDEN_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["ready"], 90)
        self.assertEqual(result["held"], 30)
        self.assertEqual(result["scheduled_holds"], 0)
        self.assertEqual(result["held_reports_staged"], 0)
        self.assertEqual(Counter(result["hold_codes"]), Counter(gate.HOLD_PLAN))

    def test_thirty_holds_use_exact_truth_set_codes(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 30)
        by_code = {code: [] for code in gate.HOLD_CODES}
        for item in result["holds"]:
            by_code[item["code"]].append(item)
        self.assertEqual(len(by_code["DUPLICATE_ID"]), 8)
        self.assertEqual(len(by_code["WRONG_LINE_METHOD"]), 7)
        self.assertEqual(len(by_code["MISSING_STUDY_PACKAGE"]), 5)
        self.assertEqual(len(by_code["INSTRUMENT_QC_FAILURE"]), 5)
        self.assertEqual(len(by_code["SOURCE_HASH_MISMATCH"]), 5)
        self.assertTrue(all(item["state"] == "HOLD" for item in result["holds"]))
        self.assertTrue(all(not item["scheduled"] and item["report"] is None for item in result["holds"]))

    def test_valid_rows_route_to_prescribed_lines(self) -> None:
        result = gate.run_gate()
        first = next(item for item in result["accessions"] if item["study_id"] == "CSA-STU-001")
        self.assertEqual(first["line"], "CCIT")
        self.assertEqual(first["method"], "VACUUM-DECAY")
        self.assertEqual(first["route"], "CCIT_LINE")
        second = next(item for item in result["accessions"] if item["study_id"] == "CSA-STU-002")
        self.assertEqual(second["line"], "RAW_MATERIAL")
        self.assertEqual(second["route"], "RAW_MATERIAL_LINE")

    def test_method_instrument_value_unit_audit_source_hashes_match(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["lineage_sha256"], gate.GOLDEN_LINEAGE_SHA256)
        self.assertEqual(result["report_digest"], gate.GOLDEN_REPORT_DIGEST)
        for item in result["accessions"]:
            self.assertEqual(
                item["source_hash"],
                gate.source_hash(item["study_id"], item["sample_id"], item["lot_id"], item["package_id"]),
            )
            self.assertEqual(
                item["method_hash"],
                gate.method_hash(item["line"], item["method"], item["method_version"]),
            )
            self.assertEqual(
                item["instrument_hash"],
                gate.instrument_hash(item["raw"]["instrument_id"], item["raw"]["run_id"]),
            )
            self.assertEqual(item["value_hash"], gate.value_hash(item["raw"]))
            self.assertEqual(item["unit_hash"], gate.unit_hash(item["line"], item["method"]))
            self.assertEqual(
                item["audit_hash"],
                gate.audit_hash(item["study_id"], item["line"], item["method"], item["value_hash"]),
            )
            self.assertEqual(item["report"]["state"], "STAGED")
            self.assertFalse(item["released"])

    def test_replay_adds_zero_records(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 90)
        self.assertEqual(len(journal["holds"]), 30)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_record_count"], 0)
        self.assertEqual(replay["replay_noops"], 120)

    def test_named_human_release_only(self) -> None:
        journal = gate.empty_journal()
        row = next(item for item in gate.build_acceptance_fixture() if item["expected_hold"] is None)
        gate.ingest_row(journal, row)
        acc_id = next(iter(journal["accessions"]))
        autonomous = gate.release_report(journal, acc_id, actor_role="SYSTEM", actor="bot")
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        unnamed = gate.release_report(journal, acc_id, actor_role="APPROVER", actor="someone-else")
        self.assertEqual(unnamed["code"], "NAMED_HUMAN_REQUIRED")
        human = gate.release_report(journal, acc_id, actor_role="APPROVER", actor="brandon-zurawlow")
        self.assertTrue(human["ok"])
        self.assertEqual(journal["accessions"][acc_id]["released_by"], "brandon-zurawlow")

    def test_local_holds_match_predetermined_codes(self) -> None:
        valid = next(item for item in gate.build_acceptance_fixture() if item["study_id"] == "CSA-STU-001")
        journal = gate.empty_journal()
        gate.ingest_row(journal, valid)
        dup = deepcopy(valid)
        dup["row_id"] = "RLOCALDUP"
        self.assertEqual(gate.ingest_row(journal, dup)["code"], "DUPLICATE_ID")

        journal = gate.empty_journal()
        mis = deepcopy(valid)
        mis["row_id"] = "RLOCALMIS"
        mis["study_id"] = "CSA-STU-LOCAL-MIS"
        mis["sample_id"] = "CSA-SMP-LOCAL-MIS"
        mis["lot_id"] = "CSA-LOT-LOCAL-MIS"
        mis["method"] = "USP-71"
        self.assertEqual(gate.ingest_row(journal, mis)["code"], "WRONG_LINE_METHOD")

        journal = gate.empty_journal()
        missing = deepcopy(valid)
        missing["row_id"] = "RLOCALMETA"
        missing["study_id"] = "CSA-STU-LOCAL-META"
        missing["sample_id"] = "CSA-SMP-LOCAL-META"
        missing["lot_id"] = "CSA-LOT-LOCAL-META"
        missing["package_id"] = ""
        missing["source_hash"] = gate.source_hash(
            missing["study_id"], missing["sample_id"], missing["lot_id"], ""
        )
        self.assertEqual(gate.ingest_row(journal, missing)["code"], "MISSING_STUDY_PACKAGE")

    def test_no_live_interfaces_or_compliance_decision(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertFalse(result["autonomous_release"])
        self.assertFalse(result["compliance_decision"])
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["pre_sale_transport"], "NONE")
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )


if __name__ == "__main__":
    unittest.main()
