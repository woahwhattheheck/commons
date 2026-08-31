#!/usr/bin/env python3
"""Binary acceptance for preinnewhof-pfas-fieldblank-gate-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter

import preinnewhof_pfas_fieldblank_gate as gate


class PreinnewhofPfasFieldblankGateTests(unittest.TestCase):
    def test_acceptance_fixture_row_count_and_truth_set(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 150)
        truths = Counter(row["truth"] for row in rows)
        self.assertEqual(truths["VALID"], 120)
        for code in gate.HOLD_CODES:
            self.assertEqual(truths[code], 5, code)

    def test_pass_contract_exact_counts_and_holds(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 150)
        self.assertEqual(result["accessioned"], 120)
        self.assertEqual(result["held"], 30)
        self.assertEqual(result["hold_counts"], {code: 5 for code in gate.HOLD_CODES})
        self.assertEqual(len(set(result["accession_ids"])), 120)
        self.assertEqual(result["released_reports"], 0)
        self.assertEqual(result["blocked_reports"], 120)
        self.assertEqual(result["held_worksheets"], 0)
        self.assertEqual(result["held_portal_results"], 0)
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertFalse(result["autonomous_certification"])
        self.assertFalse(result["autonomous_release"])

    def test_valid_rows_accession_once_with_method_and_field_blank_parentage(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        valid = [row for row in rows if row["truth"] == "VALID"]
        self.assertEqual(len(valid), 120)
        bound = {item["sample_id"]: item for item in result["accessions"]}
        self.assertEqual(set(bound), {row["sample_id"] for row in valid})
        splits = {"GRAND_RAPIDS": 0, "HOLLAND": 0, "MUSKEGON": 0}
        for row in valid:
            item = bound[row["sample_id"]]
            self.assertEqual(item["method"], row["method"])
            self.assertEqual(item["location"], row["location"])
            self.assertEqual(item["field_blank_id"], row["field_blank_id"])
            expected = gate.field_blank_parentage(
                row["sample_id"], row["field_blank_id"], row["method"]
            )
            self.assertEqual(item["field_blank_parentage"], expected)
            self.assertEqual(
                item["accession_id"],
                gate.accession_id(row["location"], row["sample_id"], row["method"]),
            )
            self.assertEqual(item["worksheet_id"], f"WS-{item['accession_id']}")
            self.assertEqual(item["portal_result"], "STAGED")
            splits[row["location"]] += 1
        self.assertEqual(splits, {"GRAND_RAPIDS": 40, "HOLLAND": 40, "MUSKEGON": 40})

    def test_hold_codes_match_truth_set_exactly(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds_by_row = {item["row_id"]: item["code"] for item in result["holds"]}
        for row in rows:
            if row["truth"] == "VALID":
                self.assertNotIn(row["row_id"], holds_by_row)
                continue
            self.assertEqual(holds_by_row[row["row_id"]], row["truth"])

    def test_held_item_creates_no_worksheet_or_portal_result(self) -> None:
        result = gate.run_gate()
        accession_ids = set(result["accession_ids"])
        for item in result["holds"]:
            self.assertIsNone(item["worksheet_id"])
            self.assertIsNone(item["portal_result"])
            if item["sample_id"] and item["code"] != gate.HOLD_DUPLICATE_SAMPLE_ID:
                self.assertFalse(
                    any(
                        acc.startswith("PN-") and item["sample_id"] in acc
                        for acc in accession_ids
                    )
                )
        for item in result["accessions"]:
            self.assertTrue(item["worksheet_id"])
            self.assertEqual(item["portal_result"], "STAGED")

        journal = gate.empty_journal()
        hold = next(
            row
            for row in gate.build_acceptance_fixture()
            if row["truth"] == gate.HOLD_MISSING_FIELD_BLANK
        )
        effect = gate.ingest_row(journal, hold)
        self.assertEqual(effect["kind"], "HOLD")
        self.assertEqual(len(journal["accessions"]), 0)
        self.assertEqual(journal["worksheets"], {})
        self.assertEqual(journal["portal_results"], {})

    def test_source_hashes_and_custody_locations_reconcile(self) -> None:
        result = gate.run_gate()
        fixture = {
            row["sample_id"]: row
            for row in gate.build_acceptance_fixture()
            if row["truth"] == "VALID"
        }
        self.assertEqual(result["hashes_ok_count"], 120)
        self.assertEqual(result["custody_match_count"], 120)
        for item in result["accessions"]:
            row = fixture[item["sample_id"]]
            self.assertTrue(gate.hashes_reconcile(row))
            self.assertEqual(item["source_hash"], gate.source_hash(row))
            self.assertEqual(item["custody_hash"], gate.custody_hash(row))
            self.assertEqual(item["image_sha256"], gate.image_hash(row))
            self.assertEqual(item["custody_location"], item["location"])
            self.assertEqual(item["custody_location"], row["location"])

    def test_replay_creates_zero_records(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(len(first["manifest_sha256"]), 64)
        self.assertEqual(len(first["fixture_sha256"]), 64)

        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 120)
        self.assertEqual(len(journal["holds"]), 30)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["accession_count"], 120)
        self.assertEqual(replay["hold_count"], 30)
        self.assertEqual(replay["replay_noops"], 120)

    def test_human_review_controls_release(self) -> None:
        journal = gate.empty_journal()
        row = next(item for item in gate.build_acceptance_fixture() if item["truth"] == "VALID")
        gate.ingest_row(journal, row)
        acc_id = next(iter(journal["accessions"]))
        record = journal["accessions"][acc_id]
        self.assertEqual(gate.report_status(record), "STAGED_BLOCKED_MISSING_RESULT")
        self.assertEqual(record["portal_result"], "STAGED")

        denied = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "REPORT_BLOCKED")

        gate.attach_result(journal, acc_id, {"pfoa_ng_l": 2.1})
        self.assertEqual(record["report_status"], "STAGED_BLOCKED_MISSING_QC")
        gate.qc_signoff(journal, acc_id)
        self.assertEqual(record["report_status"], "STAGED_READY_FOR_HUMAN_RELEASE")

        autonomous = gate.release_report(journal, acc_id, actor_role="SYSTEM", actor="autonomous")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(record["released"])
        self.assertEqual(record["portal_result"], "STAGED")

        human = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertTrue(human["ok"])
        self.assertEqual(record["report_status"], "RELEASED")
        self.assertEqual(record["released_by"], "reviewer-1")
        self.assertEqual(record["portal_result"], "RELEASED")

    def test_classifier_matches_each_hold_defect_independently(self) -> None:
        rows = {
            row["truth"]: row
            for row in gate.build_acceptance_fixture()
            if row["truth"] != "VALID"
        }
        self.assertEqual(
            gate.classify_submission(rows[gate.HOLD_MISSING_FIELD_BLANK])["code"],
            gate.HOLD_MISSING_FIELD_BLANK,
        )
        self.assertEqual(
            gate.classify_submission(rows[gate.HOLD_BOTTLE_COC_MISMATCH])["code"],
            gate.HOLD_BOTTLE_COC_MISMATCH,
        )
        self.assertEqual(
            gate.classify_submission(rows[gate.HOLD_INVALID_RECEIPT_WINDOW])["code"],
            gate.HOLD_INVALID_RECEIPT_WINDOW,
        )
        self.assertEqual(
            gate.classify_submission(rows[gate.HOLD_WRONG_PRESERVATION])["code"],
            gate.HOLD_WRONG_PRESERVATION,
        )
        self.assertEqual(
            gate.classify_submission(rows[gate.HOLD_UNSUPPORTED_METHOD_LOCATION])["code"],
            gate.HOLD_UNSUPPORTED_METHOD_LOCATION,
        )
        first = next(row for row in gate.build_acceptance_fixture() if row["truth"] == "VALID")
        dup = next(
            row
            for row in gate.build_acceptance_fixture()
            if row["truth"] == gate.HOLD_DUPLICATE_SAMPLE_ID
        )
        self.assertEqual(dup["sample_id"], first["sample_id"])
        self.assertEqual(
            gate.classify_submission(dup, {first["sample_id"]})["code"],
            gate.HOLD_DUPLICATE_SAMPLE_ID,
        )

    def test_simulated_adapters_never_write_production(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["production_writes"], 0)
        for item in result["accessions"]:
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            self.assertFalse(item["production_write"])
            self.assertFalse(item["released"])
        self.assertTrue(
            all(
                item["code"] == "AUTONOMOUS_RELEASE_DENIED"
                for item in result["autonomous_release_effects"]
            )
        )


if __name__ == "__main__":
    unittest.main()
