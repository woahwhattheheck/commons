#!/usr/bin/env python3
"""Binary acceptance for cornell-craft-beverage-intake-lims-01."""

from __future__ import annotations

import unittest
from copy import deepcopy

import cornell_craft_beverage_intake as gate


class CornellCraftBeverageIntakeTests(unittest.TestCase):
    def test_acceptance_fixture_row_count(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 8)

    def test_pass_contract_exact_counts_and_routes(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 8)
        self.assertEqual(result["accessioned"], 6)
        self.assertEqual(result["rejected"], 2)
        self.assertEqual(result["reject_codes"], ["MISSING_SAMPLE_ID", "UNDER_VOLUME"])
        self.assertEqual(
            result["routes"],
            {
                "CCB-C01": "CIDER_SINGLE",
                "CCB-J01": "JUICE_PANEL",
                "CCB-K01": "KOMBUCHA_ABV",
                "CCB-S01": "SPIRITS_ABV",
                "CCB-W01": "WINE_MULTI",
                "CCB-W02": "WINE_SINGLE",
            },
        )
        self.assertEqual(len(set(result["accession_ids"])), 6)
        self.assertEqual(result["released_reports"], 0)
        self.assertEqual(result["blocked_reports"], 6)
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertFalse(result["autonomous_certification"])
        self.assertFalse(result["autonomous_release"])

    def test_reject_codes_are_exact(self) -> None:
        result = gate.run_gate()
        codes = [item["code"] for item in result["rejects"]]
        self.assertEqual(sorted(codes), ["MISSING_SAMPLE_ID", "UNDER_VOLUME"])
        under = next(item for item in result["rejects"] if item["code"] == "UNDER_VOLUME")
        missing = next(item for item in result["rejects"] if item["code"] == "MISSING_SAMPLE_ID")
        self.assertEqual(under["sample_id"], "CCB-W03")
        self.assertIsNone(missing["sample_id"])

    def test_replay_identical_hashes_and_zero_new_accessions(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(len(first["manifest_sha256"]), 64)

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 6)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_rejects"], 0)
        self.assertEqual(replay["accession_count"], 6)
        self.assertEqual(replay["reject_count"], 2)
        self.assertEqual(replay["replay_noops"], 6)

    def test_frozen_juice_requires_both_flags_for_received(self) -> None:
        result = gate.run_gate()
        juice = next(item for item in result["accessions"] if item["sample_id"] == "CCB-J01")
        self.assertTrue(juice["frozen"])
        self.assertTrue(juice["next_day"])
        self.assertEqual(juice["state"], "RECEIVED")

        journal = gate.empty_journal()
        row = next(item for item in gate.build_acceptance_fixture() if item["sample_id"] == "CCB-J01")
        missing_next = deepcopy(row)
        missing_next["next_day"] = False
        missing_next["sample_id"] = "CCB-J02"
        missing_frozen = deepcopy(row)
        missing_frozen["frozen"] = False
        missing_frozen["sample_id"] = "CCB-J03"
        gate.ingest_row(journal, missing_next)
        gate.ingest_row(journal, missing_frozen)
        blocked = []
        for acc_id, record in journal["accessions"].items():
            reply = gate.receive(journal, acc_id)
            blocked.append(reply)
            self.assertEqual(record["state"], "ACCESSIONED")
            self.assertFalse(reply["ok"])
            self.assertEqual(reply["code"], "JUICE_REQUIRES_FROZEN_NEXT_DAY")
        self.assertEqual(len(blocked), 2)

    def test_reports_blocked_until_result_and_qc_then_human_release(self) -> None:
        journal = gate.empty_journal()
        wine = next(item for item in gate.build_acceptance_fixture() if item["sample_id"] == "CCB-W01")
        gate.ingest_row(journal, wine)
        acc_id = next(iter(journal["accessions"]))
        record = journal["accessions"][acc_id]
        self.assertEqual(gate.report_status(record), "BLOCKED_MISSING_RESULT")

        denied = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "REPORT_BLOCKED")

        gate.record_result(journal, acc_id, {"ethanol": 12.4})
        self.assertEqual(record["report_status"], "BLOCKED_MISSING_QC")
        still = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertEqual(still["code"], "REPORT_BLOCKED")

        gate.qc_signoff(journal, acc_id)
        self.assertEqual(record["report_status"], "READY_FOR_HUMAN_RELEASE")
        autonomous = gate.release_report(journal, acc_id, actor_role="SYSTEM", actor="bot")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(record["released"])

        human = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertTrue(human["ok"])
        self.assertEqual(record["report_status"], "RELEASED")
        self.assertEqual(record["released_by"], "reviewer-1")

    def test_one_order_per_analysis_is_the_panel_route(self) -> None:
        result = gate.run_gate()
        for item in result["accessions"]:
            self.assertEqual(item["route"], item["panel"])
            self.assertEqual(len(item["analyses"]) >= 1, True)
            if item["panel"] in {"WINE_SINGLE", "CIDER_SINGLE", "SPIRITS_ABV", "KOMBUCHA_ABV"}:
                self.assertEqual(item["analyses"], ["ethanol"])

    def test_volume_thresholds_match_public_lab_rules(self) -> None:
        self.assertEqual(gate.min_volume_ml("grape_wine", "WINE_MULTI"), 750)
        self.assertEqual(gate.min_volume_ml("grape_wine", "WINE_SINGLE"), 375)
        self.assertEqual(gate.min_volume_ml("distillate", "SPIRITS_ABV"), 100)
        self.assertEqual(gate.min_volume_ml("kombucha", "KOMBUCHA_ABV"), 100)
        self.assertEqual(gate.min_volume_ml("juice", "JUICE_PANEL"), 750)
        self.assertEqual(gate.min_volume_ml("cider", "CIDER_SINGLE"), 375)

    def test_no_live_interfaces_or_autonomous_certification(self) -> None:
        result = gate.run_gate()
        for item in result["accessions"]:
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            self.assertFalse(item["released"])
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )


if __name__ == "__main__":
    unittest.main()
