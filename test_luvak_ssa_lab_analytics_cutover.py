#!/usr/bin/env python3
"""Binary acceptance for luvak-ssa-lab-analytics-cutover-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter
from copy import deepcopy

import luvak_ssa_lab_analytics_cutover as gate


class LuvakSsaLabAnalyticsCutoverTests(unittest.TestCase):
    def test_acceptance_fixture_is_100_frozen_shipments(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 100)
        holds = [row["expected_hold"] for row in rows]
        self.assertEqual(holds.count(None), 80)
        self.assertEqual(holds.count("MISSING_ACCEPTED_QUOTE"), 8)
        self.assertEqual(holds.count("DUPLICATE_SAMPLE_ID"), 4)
        self.assertEqual(holds.count("FORM_PACKAGE_MISMATCH"), 4)
        self.assertEqual(holds.count("METHOD_REVISION_MISMATCH"), 4)
        self.assertEqual(gate.fixture_manifest()["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)

    def test_pass_contract_expected_equals_actual(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.GOLDEN_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["ready"], 80)
        self.assertEqual(result["held"], 20)
        self.assertEqual(result["held_test_stages"], 0)
        self.assertEqual(result["held_report_stages"], 0)
        self.assertEqual(Counter(result["hold_codes"]), Counter(gate.HOLD_PLAN))

    def test_twenty_holds_use_exact_truth_set_codes(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 20)
        by_code = {code: [] for code in gate.HOLD_CODES}
        for item in result["holds"]:
            by_code[item["code"]].append(item)
        self.assertEqual(
            [item["sample_id"] for item in by_code["MISSING_ACCEPTED_QUOTE"]],
            ["LVK-SMP-HQ%02d" % n for n in range(1, 9)],
        )
        self.assertEqual(
            [item["sample_id"] for item in by_code["DUPLICATE_SAMPLE_ID"]],
            ["LVK-SMP-%03d" % n for n in range(1, 5)],
        )
        self.assertEqual(
            [item["sample_id"] for item in by_code["FORM_PACKAGE_MISMATCH"]],
            ["LVK-SMP-HFP%02d" % n for n in range(1, 5)],
        )
        self.assertEqual(
            [item["sample_id"] for item in by_code["METHOD_REVISION_MISMATCH"]],
            ["LVK-SMP-HREV%02d" % n for n in range(1, 5)],
        )
        self.assertTrue(all(item["test_stage"] is None and item["report_stage"] is None for item in result["holds"]))

    def test_quote_form_coc_method_result_report_hashes_match(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["lineage_sha256"], gate.GOLDEN_LINEAGE_SHA256)
        self.assertEqual(result["report_digest"], gate.GOLDEN_REPORT_DIGEST)
        for item in result["accessions"]:
            self.assertEqual(item["quote_hash"], gate.quote_hash(item["quote_id"]))
            self.assertEqual(item["form_hash"], gate.form_hash(item["form_id"], item["sample_id"]))
            self.assertEqual(item["coc_hash"], gate.coc_hash(item["coc_id"], item["sample_id"]))
            self.assertEqual(item["method_hash"], gate.method_hash(item["method"], item["method_version"]))
            self.assertEqual(item["result_hash"], gate.result_hash(item["raw"]))
            self.assertEqual(item["report_hash"], gate.report_hash(item["sample_id"], item["result_hash"]))
            self.assertEqual(item["cutover_site"], "SSA")
            self.assertEqual(item["report"]["state"], "STAGED")
            self.assertFalse(item["released"])

    def test_replay_produces_zero_duplicates(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 80)
        self.assertEqual(len(journal["holds"]), 20)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_record_count"], 0)
        self.assertEqual(replay["replay_noops"], 100)

    def test_named_human_release_only(self) -> None:
        journal = gate.empty_journal()
        row = next(item for item in gate.build_acceptance_fixture() if item["expected_hold"] is None)
        gate.ingest_row(journal, row)
        acc_id = next(iter(journal["accessions"]))
        autonomous = gate.release_report(journal, acc_id, actor_role="SYSTEM", actor="bot")
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        unnamed = gate.release_report(journal, acc_id, actor_role="APPROVER", actor="someone-else")
        self.assertEqual(unnamed["code"], "NAMED_HUMAN_REQUIRED")
        human = gate.release_report(journal, acc_id, actor_role="APPROVER", actor="dean-gaskill")
        self.assertTrue(human["ok"])
        self.assertEqual(journal["accessions"][acc_id]["released_by"], "dean-gaskill")

    def test_local_holds_match_predetermined_codes(self) -> None:
        valid = next(item for item in gate.build_acceptance_fixture() if item["sample_id"] == "LVK-SMP-001")
        journal = gate.empty_journal()
        missing = deepcopy(valid)
        missing["row_id"] = "RLOCALQ"
        missing["sample_id"] = "LVK-SMP-LOCAL-Q"
        missing["quote_id"] = ""
        self.assertEqual(gate.ingest_row(journal, missing)["code"], "MISSING_ACCEPTED_QUOTE")

        journal = gate.empty_journal()
        gate.ingest_row(journal, valid)
        dup = deepcopy(valid)
        dup["row_id"] = "RLOCALDUP"
        dup["quote_id"] = "LVK-Q-LOCAL-DUP"
        self.assertEqual(gate.ingest_row(journal, dup)["code"], "DUPLICATE_SAMPLE_ID")

        journal = gate.empty_journal()
        mismatch = deepcopy(valid)
        mismatch["row_id"] = "RLOCALFP"
        mismatch["sample_id"] = "LVK-SMP-LOCAL-FP"
        mismatch["quote_id"] = "LVK-Q-LOCAL-FP"
        mismatch["form_package_id"] = "PKG-OTHER"
        self.assertEqual(gate.ingest_row(journal, mismatch)["code"], "FORM_PACKAGE_MISMATCH")

        journal = gate.empty_journal()
        rev = deepcopy(valid)
        rev["row_id"] = "RLOCALREV"
        rev["sample_id"] = "LVK-SMP-LOCAL-REV"
        rev["quote_id"] = "LVK-Q-LOCAL-REV"
        rev["method_version"] = "IGA-O-2018-LEGACY"
        self.assertEqual(gate.ingest_row(journal, rev)["code"], "METHOD_REVISION_MISMATCH")

    def test_no_live_interfaces_or_materials_qualification_decision(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertFalse(result["autonomous_release"])
        self.assertFalse(result["materials_qualification_decision"])
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["pre_sale_transport"], "NONE")
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )


if __name__ == "__main__":
    unittest.main()
