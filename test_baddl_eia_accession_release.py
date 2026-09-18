#!/usr/bin/env python3
"""Binary acceptance for baddl-eia-accession-release-lims-01."""

from __future__ import annotations

import unittest

import baddl_eia_accession_release as gate


class BaddlEiaAccessionReleaseTests(unittest.TestCase):
    def test_acceptance_fixture_is_24_split_8_8_8(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 24)
        sources = [row["source"] for row in rows]
        self.assertEqual(sources.count("PAPER_VS1011"), 8)
        self.assertEqual(sources.count("VSPS"), 8)
        self.assertEqual(sources.count("GVL"), 8)

    def test_pass_contract_exact_state_counts(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(
            counts["expected"],
            {
                "input_rows": 24,
                "worklist": 22,
                "hold": 2,
                "negative": 19,
                "positive": 2,
                "invalid": 1,
                "human_releasable": 21,
                "human_released": 21,
                "invalid_hold": 1,
                "autonomous_released": 0,
            },
        )
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["hold_codes"], ["HOLD_DUPLICATE_TUBE_ID", "HOLD_UNSIGNED_FORM"])

    def test_unsigned_paper_and_duplicate_tube_are_the_two_holds(self) -> None:
        result = gate.run_gate()
        unsigned = next(item for item in result["holds"] if item["code"] == "HOLD_UNSIGNED_FORM")
        duplicate = next(item for item in result["holds"] if item["code"] == "HOLD_DUPLICATE_TUBE_ID")
        self.assertEqual(unsigned["row_id"], "P08")
        self.assertEqual(unsigned["source"], "PAPER_VS1011")
        self.assertEqual(duplicate["row_id"], "G08")
        self.assertEqual(duplicate["tube_id"], "SYN-EIA-G07")
        self.assertEqual(len(result["holds"]), 2)

    def test_simulated_results_are_19_2_1_and_invalid_stays_hold(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["negative"], 19)
        self.assertEqual(result["positive"], 2)
        self.assertEqual(result["invalid"], 1)
        positives = sorted(
            item["sample_id"] for item in result["accessions"] if item["simulated_result"] == "POSITIVE"
        )
        self.assertEqual(positives, ["SYN-EIA-G05", "SYN-EIA-G06"])
        invalid = next(item for item in result["accessions"] if item["sample_id"] == "SYN-EIA-G07")
        self.assertEqual(invalid["simulated_result"], "INVALID")
        self.assertFalse(invalid["released"])
        self.assertEqual(invalid["report_status"], "HOLD_INVALID_RESULT")
        self.assertEqual(result["human_released"], 21)
        self.assertEqual(result["invalid_hold"], 1)

    def test_autonomous_release_denied_then_named_human_releases_21(self) -> None:
        result = gate.run_gate()
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )
        self.assertEqual(sum(1 for item in result["human_release_effects"] if item.get("ok")), 21)
        denied = [item for item in result["human_release_effects"] if not item.get("ok")]
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0]["code"], "HOLD_INVALID_RESULT")

    def test_replay_adds_zero_accessions_and_hashes_match(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(len(first["audit_sha256"]), 64)
        self.assertEqual(gate.sha256_hex(first["audit"]), first["audit_sha256"])

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 22)
        self.assertEqual(len(journal["holds"]), 2)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["accession_count"], 22)
        self.assertEqual(replay["hold_count"], 2)
        self.assertEqual(replay["replay_noops"], 22)

    def test_sample_id_reconciliation_and_report_routes(self) -> None:
        result = gate.run_gate()
        for item in result["accessions"]:
            self.assertEqual(item["sample_id"], item["tube_id"])
            self.assertEqual(item["route"], "EIA_WORKLIST")
            self.assertEqual(item["assay"], "EIA")
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            if item["released"]:
                self.assertEqual(item["report_route"], gate.REPORT_ROUTES[item["source"]])
                self.assertEqual(item["provenance"]["report_route"], item["report_route"])
            self.assertIsNone(item["animal_status"])
            self.assertFalse(item["regulatory_submitted"])
            self.assertFalse(item["billed"])

    def test_no_live_adapters_or_status_mutation(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["animal_status_writes"], 0)
        self.assertEqual(result["regulatory_submits"], 0)
        self.assertEqual(result["billing_writes"], 0)
        self.assertFalse(result["autonomous_release"])
        self.assertEqual(result["audit"]["adapters"]["animal_status"], "NOT_WRITTEN")
        self.assertEqual(result["audit"]["adapters"]["regulatory_submit"], "NOT_SENT")
        self.assertEqual(result["audit"]["adapters"]["analyzer"], "SIMULATED")

    def test_human_cannot_release_before_result_or_when_invalid(self) -> None:
        journal = gate.empty_journal()
        paper = next(item for item in gate.build_acceptance_fixture() if item["row_id"] == "P01")
        gate.ingest_row(journal, paper)
        acc_id = next(iter(journal["accessions"]))
        blocked = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="releaser-1")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "REPORT_BLOCKED")
        gate.import_simulated_result(journal, acc_id)
        human = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="releaser-1")
        self.assertTrue(human["ok"])

        journal2 = gate.empty_journal()
        invalid_row = next(item for item in gate.build_acceptance_fixture() if item["sample_id"] == "SYN-EIA-G07")
        gate.ingest_row(journal2, invalid_row)
        inv_id = next(iter(journal2["accessions"]))
        gate.import_simulated_result(journal2, inv_id)
        still = gate.release_report(journal2, inv_id, actor_role="RELEASER", actor="releaser-1")
        self.assertFalse(still["ok"])
        self.assertEqual(still["code"], "HOLD_INVALID_RESULT")


if __name__ == "__main__":
    unittest.main()
