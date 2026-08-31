#!/usr/bin/env python3
"""Binary acceptance for ace-qat-thermal-rheology-capacity-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter
from copy import deepcopy

import ace_qat_thermal_rheology_capacity as gate


class AceQatThermalRheologyCapacityTests(unittest.TestCase):
    def test_acceptance_fixture_is_120_frozen_orders(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 120)
        holds = [row["expected_hold"] for row in rows]
        self.assertEqual(holds.count(None), 90)
        self.assertEqual(holds.count("CAPABILITY_MISMATCH"), 10)
        self.assertEqual(holds.count("QC_FAIL"), 10)
        self.assertEqual(holds.count("DUPLICATE_ID"), 10)
        if gate.GOLDEN_FIXTURE_SHA256 != "PENDING":
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
        self.assertEqual(result["hold_code_set"], sorted(gate.HOLD_CODES))
        self.assertEqual(
            Counter(result["hold_codes"]),
            Counter({"DUPLICATE_ID": 10, "CAPABILITY_MISMATCH": 10, "QC_FAIL": 10}),
        )

    def test_thirty_holds_use_predetermined_codes_and_ids(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 30)
        by_code = {code: [] for code in gate.HOLD_CODES}
        for item in result["holds"]:
            by_code[item["code"]].append(item)
        self.assertEqual(
            sorted(item["order_id"] for item in by_code["DUPLICATE_ID"]),
            [gate.valid_order_id(i) for i in range(1, 11)],
        )
        self.assertEqual(
            sorted(item["order_id"] for item in by_code["CAPABILITY_MISMATCH"]),
            ["AQ-CM%02d" % i for i in range(1, 11)],
        )
        self.assertEqual(
            sorted(item["order_id"] for item in by_code["QC_FAIL"]),
            ["AQ-QC%02d" % i for i in range(1, 11)],
        )

    def test_router_binds_ace_qat_provenance_and_six_methods(self) -> None:
        result = gate.run_gate()
        ready = [item for item in result["accessions"] if item["state"] == "READY"]
        self.assertEqual(len(ready), 90)
        methods = sorted({item["method"] for item in ready})
        self.assertEqual(methods, sorted(gate.METHODS))
        first = next(item for item in ready if item["order_id"] == "AQ-V001")
        self.assertEqual(first["method"], "DSC")
        self.assertEqual(first["method_version"], "ASTM-D3418-21")
        self.assertEqual(first["source"], "ACE")
        self.assertEqual(first["instrument_id"], "DSC-Q2000")
        self.assertEqual(first["route"], "ACE_DSC")
        self.assertEqual(first["site"], "ACE-THERMAL-01")
        rheo = next(item for item in ready if item["order_id"] == "AQ-V006")
        self.assertEqual(rheo["method"], "AR-G2")
        self.assertEqual(rheo["source"], "QAT")
        self.assertEqual(rheo["route"], "QAT_RHEOLOGY")
        for item in ready:
            spec = gate.lookup_capability(
                item["method"], item["method_version"], item["source"], item["instrument_id"]
            )
            self.assertIsNotNone(spec)
            self.assertEqual(item["route"], spec["route"])
            self.assertFalse(item["interface_live"])
            self.assertEqual(item["interface_state"], "SIMULATED")

    def test_instrument_method_source_hashes_match_fixture(self) -> None:
        rows = {row["order_id"]: row for row in gate.build_acceptance_fixture()}
        result = gate.run_gate()
        self.assertTrue(result["hashes_match"])
        self.assertEqual(len(result["hash_matches"]), 100)
        for item in result["accessions"]:
            expected = rows[item["order_id"]]
            self.assertEqual(item["source_hash"], expected["source_hash"])
            self.assertEqual(item["method_hash"], expected["method_hash"])
            self.assertEqual(item["instrument_hash"], expected["instrument_hash"])
            self.assertEqual(item["source_hash"], gate.source_hash(item["source"], item["order_id"]))
            self.assertEqual(
                item["method_hash"],
                gate.method_hash(item["method"], item["method_version"]),
            )
            self.assertEqual(item["instrument_hash"], gate.instrument_hash(item["instrument_id"]))

    def test_replay_adds_zero_jobs_and_zero_holds(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["report_digest"], second["report_digest"])
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
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

    def test_zero_reports_release_without_named_approval(self) -> None:
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
        self.assertEqual(gate.report_status(record), "READY")
        unnamed = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="")
        self.assertFalse(unnamed["ok"])
        self.assertEqual(unnamed["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(record["released"])
        system = gate.release_report(journal, acc_id, actor_role="SYSTEM", actor="bot")
        self.assertEqual(system["code"], "AUTONOMOUS_RELEASE_DENIED")
        human = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="erick-sharp-reviewer")
        self.assertTrue(human["ok"])
        self.assertEqual(record["report_status"], "RELEASED")
        self.assertEqual(record["released_by"], "erick-sharp-reviewer")

    def test_qc_fail_and_mismatch_cannot_release(self) -> None:
        journal = gate.empty_journal()
        qc = next(item for item in gate.build_acceptance_fixture() if item["expected_hold"] == "QC_FAIL")
        mismatch = next(
            item for item in gate.build_acceptance_fixture() if item["expected_hold"] == "CAPABILITY_MISMATCH"
        )
        gate.ingest_row(journal, qc)
        gate.ingest_row(journal, mismatch)
        self.assertEqual(len(journal["jobs"]), 1)
        acc_id = next(iter(journal["jobs"]))
        blocked = gate.release_report(journal, acc_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "REPORT_BLOCKED")
        self.assertFalse(journal["jobs"][acc_id]["released"])

    def test_capability_mismatch_does_not_create_a_job(self) -> None:
        journal = gate.empty_journal()
        row = deepcopy(
            next(item for item in gate.build_acceptance_fixture() if item["order_id"] == "AQ-CM01")
        )
        effect = gate.ingest_row(journal, row)
        self.assertEqual(effect["kind"], "HOLD")
        self.assertEqual(effect["code"], "CAPABILITY_MISMATCH")
        self.assertEqual(journal["jobs"], {})
        self.assertEqual(journal["holds"][0]["source"], "QAT")
        self.assertEqual(journal["holds"][0]["method"], "DSC")

    def test_no_live_interfaces_or_autonomous_certification(self) -> None:
        result = gate.run_gate()
        for item in result["accessions"]:
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            self.assertFalse(item["released"])
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertFalse(result["autonomous_certification"])
        self.assertFalse(result["autonomous_release"])
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["pre_sale_transport"], "NONE")


if __name__ == "__main__":
    unittest.main()
