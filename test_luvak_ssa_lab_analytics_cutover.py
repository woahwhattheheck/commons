#!/usr/bin/env python3
"""Binary acceptance for luvak-ssa-lab-analytics-cutover-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter
from copy import deepcopy

import luvak_ssa_lab_analytics_cutover as gate


class LuvakSsaLabAnalyticsCutoverTests(unittest.TestCase):
    def test_acceptance_fixture_row_count(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 100)

    def test_pass_contract_exact_ready_and_hold_counts(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 100)
        self.assertEqual(result["ready"], 80)
        self.assertEqual(result["hold"], 20)
        self.assertEqual(
            result["hold_counts"],
            {
                "MISSING_ACCEPTED_QUOTE": 8,
                "DUPLICATE_SAMPLE_ID": 4,
                "FORM_PACKAGE_MISMATCH": 4,
                "METHOD_REVISION_MISMATCH": 4,
            },
        )
        self.assertEqual(len(set(result["ready_ids"])), 80)
        self.assertEqual(len(set(result["accession_ids"])), 80)
        self.assertEqual(result["released_reports"], 0)
        self.assertEqual(result["staged_reports"], 80)
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["adapters"], "SYNTHETIC_READ_ONLY")
        self.assertFalse(result["autonomous_certification"])
        self.assertFalse(result["autonomous_release"])
        self.assertIsNone(result["qualification_decision"])
        self.assertTrue(result["materials_quality_evidence_only"])

    def test_hold_codes_are_exact(self) -> None:
        result = gate.run_gate()
        codes = [item["hold_code"] for item in result["holds"]]
        self.assertEqual(Counter(codes), Counter(result["hold_counts"]))
        missing = [item for item in result["holds"] if item["hold_code"] == "MISSING_ACCEPTED_QUOTE"]
        dups = [item for item in result["holds"] if item["hold_code"] == "DUPLICATE_SAMPLE_ID"]
        mismatches = [item for item in result["holds"] if item["hold_code"] == "FORM_PACKAGE_MISMATCH"]
        revisions = [item for item in result["holds"] if item["hold_code"] == "METHOD_REVISION_MISMATCH"]
        self.assertEqual(len(missing), 8)
        self.assertEqual(len(dups), 4)
        self.assertEqual(len(mismatches), 4)
        self.assertEqual(len(revisions), 4)
        self.assertEqual(
            [item["sample_id"] for item in dups],
            ["LVK-0001", "LVK-0002", "LVK-0003", "LVK-0004"],
        )

    def test_holds_create_no_test_or_report_stage(self) -> None:
        result = gate.run_gate()
        for hold in result["holds"]:
            self.assertEqual(hold["state"], "HOLD")
            self.assertIsNone(hold["test_stage"])
            self.assertIsNone(hold["report_stage"])
            self.assertIsNone(hold["result_hash"])
            self.assertIsNone(hold["report_hash"])

    def test_ready_records_preserve_quote_form_coc_method_result_report_hashes(self) -> None:
        result = gate.run_gate()
        with_coc = 0
        without_coc = 0
        for record in result["records"]:
            self.assertEqual(record["state"], "READY")
            for key in ("quote_hash", "form_hash", "method_hash", "result_hash", "report_hash"):
                self.assertEqual(len(record[key]), 64, key)
            if record["coc_hash"] is None:
                without_coc += 1
            else:
                self.assertEqual(len(record["coc_hash"]), 64)
                with_coc += 1
            self.assertEqual(record["test_stage"], "HASHED")
            self.assertEqual(record["report_stage"], "STAGED")
            self.assertIn(record["cutover_lane"], {"LUVAK_LEGACY", "SSA_LAB_ANALYTICS"})
            self.assertEqual(record["result"]["kind"], "MATERIALS_QUALITY_EVIDENCE")
            self.assertIsNone(record["qualification_decision"])
        self.assertGreater(with_coc, 0)
        self.assertGreater(without_coc, 0)

    def test_replay_identical_hashes_and_zero_duplicates(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(len(first["manifest_sha256"]), 64)

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["ready"]), 80)
        self.assertEqual(len(journal["holds"]), 20)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_ready_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["ready_count"], 80)
        self.assertEqual(replay["hold_count"], 20)
        self.assertEqual(replay["replay_noops"], 100)

    def test_named_human_release_only(self) -> None:
        journal = gate.empty_journal()
        row = next(item for item in gate.build_acceptance_fixture() if item["sample_id"] == "LVK-0001")
        gate.ingest_row(journal, row)
        record = journal["ready"]["LVK-0001"]
        self.assertEqual(record["report_stage"], "STAGED")
        self.assertFalse(record["released"])

        autonomous = gate.release_report(journal, "LVK-0001", actor_role="SYSTEM", actor="autonomous")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "NAMED_HUMAN_RELEASE_ONLY")
        self.assertFalse(record["released"])

        unnamed = gate.release_report(journal, "LVK-0001", actor_role="RELEASER", actor="")
        self.assertEqual(unnamed["code"], "NAMED_HUMAN_RELEASE_ONLY")

        machine = gate.release_report(journal, "LVK-0001", actor_role="RELEASER", actor="machine")
        self.assertEqual(machine["code"], "NAMED_HUMAN_RELEASE_ONLY")

        human = gate.release_report(journal, "LVK-0001", actor_role="RELEASER", actor="Dean Gaskill")
        self.assertTrue(human["ok"])
        self.assertEqual(record["report_stage"], "RELEASED")
        self.assertEqual(record["released_by"], "Dean Gaskill")
        self.assertEqual(len(record["report_hash"]), 64)

    def test_hold_cannot_be_released_even_by_named_human(self) -> None:
        journal = gate.empty_journal()
        missing = next(
            item
            for item in gate.build_acceptance_fixture()
            if not item["quote_accepted"]
        )
        gate.ingest_row(journal, missing)
        sample_id = missing["sample_id"]
        self.assertNotIn(sample_id, journal["ready"])
        denied = gate.release_report(
            journal, sample_id, actor_role="RELEASER", actor="Dean Gaskill"
        )
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "HOLD_HAS_NO_REPORT_STAGE")
        self.assertEqual(journal["holds"][0]["test_stage"], None)
        self.assertEqual(journal["holds"][0]["report_stage"], None)

    def test_isolated_hold_reasons(self) -> None:
        rows = gate.build_acceptance_fixture()
        missing = deepcopy(rows[80])
        self.assertFalse(missing["quote_accepted"])
        self.assertEqual(
            gate.classify_shipment(missing, set())["code"],
            "MISSING_ACCEPTED_QUOTE",
        )

        dup = deepcopy(rows[88])
        self.assertEqual(
            gate.classify_shipment(dup, {"LVK-0001"})["code"],
            "DUPLICATE_SAMPLE_ID",
        )

        mismatch = deepcopy(rows[92])
        self.assertNotEqual(mismatch["form_sample_id"], mismatch["package_sample_id"])
        self.assertEqual(
            gate.classify_shipment(mismatch, set())["code"],
            "FORM_PACKAGE_MISMATCH",
        )

        revision = deepcopy(rows[96])
        self.assertNotEqual(revision["quote_method_revision"], revision["form_method_revision"])
        self.assertEqual(
            gate.classify_shipment(revision, set())["code"],
            "METHOD_REVISION_MISMATCH",
        )

    def test_no_live_interfaces_or_qualification_decision(self) -> None:
        result = gate.run_gate()
        for record in result["records"]:
            self.assertEqual(record["interface_state"], "SIMULATED")
            self.assertFalse(record["interface_live"])
            self.assertEqual(record["adapters"], "SYNTHETIC_READ_ONLY")
            self.assertIsNone(record["qualification_decision"])
            self.assertFalse(record["released"])
        self.assertTrue(
            all(
                item["code"] in {"NAMED_HUMAN_RELEASE_ONLY", "HOLD_HAS_NO_REPORT_STAGE"}
                for item in result["autonomous_release_effects"]
            )
        )


if __name__ == "__main__":
    unittest.main()
