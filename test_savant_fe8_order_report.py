#!/usr/bin/env python3
"""Binary acceptance for savant-fe8-order-report-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter
from copy import deepcopy

import savant_fe8_order_report as gate


class SavantFe8OrderReportTests(unittest.TestCase):
    def test_acceptance_fixture_is_100_frozen_authorizations(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 100)
        holds = [row["expected_hold"] for row in rows]
        self.assertEqual(holds.count(None), 80)
        self.assertEqual(holds.count("MISSING_SDS"), 5)
        self.assertEqual(holds.count("MISSING_METADATA"), 5)
        self.assertEqual(holds.count("DUPLICATE_ID"), 5)
        self.assertEqual(holds.count("INVALID_METHOD"), 5)
        self.assertEqual(gate.fixture_manifest()["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)

    def test_pass_contract_expected_equals_actual(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.GOLDEN_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["hold_code_set"], sorted(gate.HOLD_CODES))
        self.assertEqual(
            Counter(result["hold_codes"]),
            Counter(
                {
                    "MISSING_SDS": 5,
                    "MISSING_METADATA": 5,
                    "DUPLICATE_ID": 5,
                    "INVALID_METHOD": 5,
                }
            ),
        )

    def test_twenty_holds_use_exact_truth_set_codes(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 20)
        by_code = {code: [] for code in gate.HOLD_CODES}
        for item in result["holds"]:
            by_code[item["code"]].append(item)
        self.assertEqual(sorted(item["auth_id"] for item in by_code["MISSING_SDS"]), [
            "FE8-HSDS01",
            "FE8-HSDS02",
            "FE8-HSDS03",
            "FE8-HSDS04",
            "FE8-HSDS05",
        ])
        self.assertEqual(sorted(item["auth_id"] for item in by_code["MISSING_METADATA"]), [
            "FE8-HMETA01",
            "FE8-HMETA02",
            "FE8-HMETA03",
            "FE8-HMETA04",
            "FE8-HMETA05",
        ])
        self.assertEqual(sorted(item["auth_id"] for item in by_code["DUPLICATE_ID"]), [
            "FE8-V001",
            "FE8-V002",
            "FE8-V003",
            "FE8-V004",
            "FE8-V005",
        ])
        self.assertEqual(sorted(item["auth_id"] for item in by_code["INVALID_METHOD"]), [
            "FE8-HMETHOD01",
            "FE8-HMETHOD02",
            "FE8-HMETHOD03",
            "FE8-HMETHOD04",
            "FE8-HMETHOD05",
        ])
        self.assertTrue(all(item["scheduled"] is False for item in result["holds"]))

    def test_valid_rows_bind_fe8_method_version_and_route(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["accessioned"], 80)
        self.assertEqual(len(set(result["accession_ids"])), 80)
        first = next(item for item in result["accessions"] if item["auth_id"] == "FE8-V001")
        self.assertEqual(first["method"], "FE8")
        self.assertEqual(first["method_version"], "DIN-51819-2022-SYN")
        self.assertEqual(first["route"], "FE8_WORKLIST")
        self.assertEqual(result["routes"]["FE8-V001"], "FE8_WORKLIST")
        self.assertEqual(result["routes"]["FE8-V080"], "FE8_WORKLIST")
        for item in result["accessions"]:
            self.assertEqual(item["method"], "FE8")
            self.assertEqual(item["method_version"], gate.METHOD_VERSION)
            self.assertTrue(item["scheduled"])
            self.assertFalse(item["interface_live"])
            self.assertEqual(item["interface_state"], "SIMULATED")

    def test_nothing_schedules_without_required_documents(self) -> None:
        journal = gate.empty_journal()
        row = next(item for item in gate.build_acceptance_fixture() if item["auth_id"] == "FE8-V010")
        bare = deepcopy(row)
        bare["sds_hash"] = ""
        bare["sds_present"] = False
        effect = gate.ingest_row(journal, bare)
        self.assertEqual(effect["kind"], "HOLD")
        self.assertEqual(effect["code"], "MISSING_SDS")
        self.assertEqual(len(journal["accessions"]), 0)
        schedules = gate.schedule_eligible(journal)
        self.assertEqual(schedules, [])

        journal = gate.empty_journal()
        missing_meta = deepcopy(row)
        missing_meta["customer_code"] = ""
        missing_meta["auth_id"] = "FE8-LOCAL-META"
        effect = gate.ingest_row(journal, missing_meta)
        self.assertEqual(effect["code"], "MISSING_METADATA")

        journal = gate.empty_journal()
        invalid = deepcopy(row)
        invalid["method"] = "FOUR_BALL"
        invalid["auth_id"] = "FE8-LOCAL-METHOD"
        effect = gate.ingest_row(journal, invalid)
        self.assertEqual(effect["code"], "INVALID_METHOD")

    def test_instrument_qc_and_report_digest_match_golden_set(self) -> None:
        result = gate.run_gate()
        first = next(item for item in result["accessions"] if item["auth_id"] == "FE8-V001")
        self.assertEqual(first["instrument"]["wear_ring_mg"], 3.0)
        self.assertEqual(first["instrument"]["wear_cage_mg"], 1.0)
        self.assertEqual(first["instrument"]["torque_nm"], 0.40)
        self.assertEqual(first["instrument"]["qc_check_std_wear_mg"], 8.0)
        self.assertTrue(first["instrument"]["qc_ok"])
        self.assertEqual(first["report"]["units"]["wear"], "mg")
        self.assertEqual(first["report"]["method"], "FE8")
        self.assertEqual(first["report_digest"], gate.sha256_hex(first["report"]))
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["report_digest"], gate.GOLDEN_REPORT_DIGEST)
        self.assertEqual(len(result["report_digests"]), 80)
        self.assertEqual(len(set(result["report_digests"])), 80)

    def test_replay_is_idempotent_and_adds_no_records(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["report_digest"], second["report_digest"])
        self.assertEqual(len(first["audit_sha256"]), 64)

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 80)
        self.assertEqual(len(journal["holds"]), 20)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["accession_count"], 80)
        self.assertEqual(replay["hold_count"], 20)
        self.assertEqual(replay["replay_noops"], 80)

    def test_named_reviewer_required_for_release(self) -> None:
        journal = gate.empty_journal()
        row = next(item for item in gate.build_acceptance_fixture() if item["auth_id"] == "FE8-V001")
        gate.ingest_row(journal, row)
        acc_id = next(iter(journal["accessions"]))
        record = journal["accessions"][acc_id]
        self.assertEqual(gate.report_status(record), "READY_FOR_HUMAN_RELEASE")

        autonomous = gate.release_report(journal, acc_id, actor_role="SYSTEM", actor="bot")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(record["released"])

        human = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertTrue(human["ok"])
        self.assertEqual(record["report_status"], "RELEASED")
        self.assertEqual(record["released_by"], "reviewer-1")
        again = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertTrue(again["ok"])
        self.assertTrue(again["duplicate"])

    def test_no_live_interfaces_or_production_writes(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertFalse(result["autonomous_certification"])
        self.assertFalse(result["autonomous_release"])
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["pre_sale_transport"], "NONE")
        self.assertEqual(result["cash_usd"], 0)
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )


if __name__ == "__main__":
    unittest.main()
