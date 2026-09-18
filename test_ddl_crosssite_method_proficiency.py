#!/usr/bin/env python3
"""Binary acceptance for ddl-crosssite-method-proficiency-lims-01.

Fail-closed. The runner is the product. HTML is not the proof.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import ddl_crosssite_method_proficiency as door

gate = door.MODULE
ROOT = Path(__file__).resolve().parent


class DdlCrosssiteMethodProficiencyTests(unittest.TestCase):
    def test_acceptance_fixture_is_160_split_120_40(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 160)
        self.assertEqual(sum(1 for row in rows if not row["block"]), 120)
        self.assertEqual(sum(1 for row in rows if row["block"]), 40)
        valid = [row for row in rows if not row["block"]]
        self.assertEqual(sum(1 for row in valid if (row["site_a"], row["site_b"]) == (gate.MN, gate.CA)), 40)
        self.assertEqual(sum(1 for row in valid if (row["site_a"], row["site_b"]) == (gate.CA, gate.NJ)), 40)
        self.assertEqual(sum(1 for row in valid if (row["site_a"], row["site_b"]) == (gate.MN, gate.NJ)), 40)
        holds = [row for row in rows if row["block"]]
        for code in gate.HOLD_CODES:
            self.assertEqual(sum(1 for row in holds if row["expected_hold_code"] == code), 8)

    def test_pass_contract_exact_160_120_40_and_locked_digest(self) -> None:
        result = gate.run_module(gate.build_acceptance_fixture())
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.EXPECTED_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        golden = gate.golden_audit_sha256()
        self.assertNotEqual(golden, "PIN_AFTER_FIRST_RUN")
        self.assertEqual(len(result["audit_sha256"]), 64)
        self.assertEqual(result["audit_sha256"], golden)
        self.assertEqual(result["replay_audit_sha256"], golden)
        self.assertTrue(result["ok"])

    def test_every_valid_study_gets_exact_controlled_method_version(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_module(rows)
        valid = [item for item in result["study_records"] if not item["block"]]
        self.assertEqual(len(valid), 120)
        self.assertEqual(result["exact_method_version"], 120)
        by_id = {row["study_id"]: row for row in rows if not row["block"]}
        for item in valid:
            src = by_id[item["study_id"]]
            controlled = gate.controlled_version(item["method_id"])
            self.assertEqual(item["method_id"], src["method_id"])
            self.assertEqual(item["method_version"], controlled)
            self.assertEqual(item["method_version"], src["expected_version"])
            self.assertEqual(item["method_version"], src["requested_version"])
            self.assertEqual(gate.METHODS[item["method_id"]]["program"], item["program"])
            self.assertEqual(item["state"], "HUMAN_RELEASED")

    def test_all_40_block_with_expected_reason(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_module(rows)
        holds = {item["study_id"]: item for item in result["hold_records"]}
        self.assertEqual(len(holds), 40)
        self.assertEqual(result["hold_code_counts"], gate.EXPECTED_HOLD_COUNTS)
        self.assertEqual(result["blocked_expected_reason"], 40)
        for row in rows:
            if not row["block"]:
                continue
            hold = holds[row["study_id"]]
            self.assertEqual(hold["code"], row["expected_hold_code"])
            verdict = gate.classify(row)
            self.assertFalse(verdict["ok"])
            self.assertEqual(verdict["code"], row["expected_hold_code"])
            self.assertFalse(hold["released"])
            self.assertFalse(hold["report_released"])
        accounted = {item["study_id"] for item in result["study_records"] if not item["block"]} | set(holds)
        self.assertEqual(accounted, {row["study_id"] for row in rows})

    def test_paired_site_results_reproduce_signed_truth_table(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_module(rows)
        self.assertEqual(result["paired_truth_table_match"], 120)
        self.assertEqual(result["truth_table_misses"], [])
        by_id = {row["study_id"]: row for row in rows if not row["block"]}
        comparisons = {item["study_id"]: item for item in result["comparison_records"]}
        self.assertEqual(len(comparisons), 120)
        for study_id, src in by_id.items():
            cmp_row = comparisons[study_id]
            self.assertEqual(cmp_row["result_a"], src["result_a"])
            self.assertEqual(cmp_row["result_b"], src["result_b"])
            self.assertEqual(cmp_row["flag"], src["expected_flag"])
            self.assertEqual(cmp_row["truth_table_flag"], src["expected_flag"])
            self.assertTrue(cmp_row["match"])
            recomputed = gate.compare_pair(
                src["method_id"],
                float(src["result_a"]),
                float(src["result_b"]),
                src.get("precision_tag"),
            )
            self.assertEqual(recomputed, src["expected_flag"])

    def test_comparison_flags_match_expected(self) -> None:
        result = gate.run_module(gate.build_acceptance_fixture())
        self.assertEqual(result["comparison_flags_expected"], 120)
        self.assertEqual(result["flag_misses"], [])
        self.assertEqual(result["flag_counts"], gate.EXPECTED_FLAG_COUNTS)
        self.assertEqual(result["program_counts"], gate.EXPECTED_PROGRAM_COUNTS)

    def test_every_result_links_facility_instrument_operator_method_report(self) -> None:
        result = gate.run_module(gate.build_acceptance_fixture())
        self.assertEqual(result["linkage_complete"], 120)
        valid = [item for item in result["study_records"] if not item["block"]]
        evidence = {item["study_id"]: item for item in result["evidence_records"]}
        self.assertEqual(len(evidence), 120)
        for item in valid:
            pack = evidence[item["study_id"]]
            self.assertTrue(gate.linkage_complete(item))
            self.assertEqual(pack["facility_a"], item["facility_a"])
            self.assertEqual(pack["facility_b"], item["facility_b"])
            self.assertEqual(pack["instrument_a"], item["instrument_a"])
            self.assertEqual(pack["instrument_b"], item["instrument_b"])
            self.assertEqual(pack["operator_a"], item["operator_a"])
            self.assertEqual(pack["operator_b"], item["operator_b"])
            self.assertEqual(pack["method_id"], item["method_id"])
            self.assertEqual(pack["method_version"], item["method_version"])
            self.assertEqual(pack["report_id"], item["report_id"])
            self.assertEqual(item["facility_a"], gate.SITE_NAMES[item["site_a"]])
            self.assertEqual(item["facility_b"], gate.SITE_NAMES[item["site_b"]])
            self.assertEqual(item["instrument_a"], gate.INSTRUMENTS[(item["site_a"], item["method_id"])])
            self.assertEqual(item["instrument_b"], gate.INSTRUMENTS[(item["site_b"], item["method_id"])])
            self.assertEqual(item["operator_a"], gate.OPERATORS[(item["site_a"], item["method_id"])])
            self.assertEqual(item["operator_b"], gate.OPERATORS[(item["site_b"], item["method_id"])])

    def test_replay_creates_zero_duplicate_study_or_evidence_events(self) -> None:
        first = gate.run_module(gate.build_acceptance_fixture())
        second = gate.run_module(gate.build_acceptance_fixture())
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(gate.sha256_hex(first["audit"]), first["audit_sha256"])
        self.assertEqual(first["replay"]["duplicate_study_events"], 0)
        self.assertEqual(first["replay"]["duplicate_evidence_events"], 0)
        self.assertEqual(first["replay"]["added_studies"], 0)
        self.assertEqual(first["replay"]["added_holds"], 0)
        self.assertEqual(first["replay"]["replay_noops"], 160)
        self.assertFalse(first["replay"]["state_changed"])
        self.assertEqual(first["replay_duplicate_study_events"], 0)
        self.assertEqual(first["replay_duplicate_evidence_events"], 0)

    def test_named_human_release_only(self) -> None:
        result = gate.run_module(gate.build_acceptance_fixture())
        self.assertTrue(all(not item.get("ok") for item in result["autonomous_release_effects"]))
        self.assertEqual(result["released_without_named_human"], 0)
        self.assertEqual(result["autonomous_released"], 0)
        self.assertEqual(sum(1 for item in result["human_release_effects"] if item.get("ok")), 120)
        denied = [item for item in result["human_release_effects"] if not item.get("ok")]
        self.assertEqual(len(denied), 40)
        self.assertTrue(all(item["code"] == "RELEASE_BLOCKED_OPEN_HOLD" for item in denied))
        self.assertEqual(result["released_after_named_human"], 120)
        self.assertEqual(result["blocked_released"], 0)

    def test_named_human_cannot_release_before_intake_or_on_hold(self) -> None:
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        clean = next(item for item in rows if not item["block"])
        hold = next(item for item in rows if item["block"])
        early = gate.release_report(journal, clean["study_id"], actor=gate.NAMED_ACTOR, actor_role=gate.NAMED_ROLE)
        self.assertFalse(early["ok"])
        self.assertEqual(early["code"], "UNKNOWN_STUDY")
        gate.intake_study(journal, hold)
        blocked = gate.release_report(journal, hold["study_id"], actor=gate.NAMED_ACTOR, actor_role=gate.NAMED_ROLE)
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "RELEASE_BLOCKED_OPEN_HOLD")
        gate.intake_study(journal, clean)
        auto = gate.release_report(journal, clean["study_id"], actor="SYSTEM", actor_role="SYSTEM")
        self.assertFalse(auto["ok"])
        self.assertEqual(auto["code"], "AUTONOMOUS_RELEASE_DENIED")
        human = gate.release_report(journal, clean["study_id"], actor=gate.NAMED_ACTOR, actor_role=gate.NAMED_ROLE)
        self.assertTrue(human["ok"])
        self.assertEqual(journal["studies"][clean["study_id"]]["released_by"], gate.NAMED_ACTOR)

    def test_official_command_exits_zero_and_prints_160_120_40(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "ddl_crosssite_method_proficiency.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["actual"]["studies"], 160)
        self.assertEqual(payload["actual"]["valid"], 120)
        self.assertEqual(payload["actual"]["blocked"], 40)
        self.assertEqual(payload["actual"]["exact_method_version"], 120)
        self.assertEqual(payload["actual"]["blocked_expected_reason"], 40)
        self.assertEqual(payload["actual"]["paired_truth_table_match"], 120)
        self.assertEqual(payload["actual"]["comparison_flags_expected"], 120)
        self.assertEqual(payload["actual"]["linkage_complete"], 120)
        self.assertEqual(payload["audit_sha256"], gate.golden_audit_sha256())


if __name__ == "__main__":
    unittest.main()
