#!/usr/bin/env python3
"""Fail-closed binary for aquatrace-work-order-c-reporting-offline-20260831-01.

The runner is the product. HTML is a window, not the proof.
Do not weaken recover / HOLD / export-hash / replay / human-release gates.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import aquatrace_work_order_c_reporting_offline as door

gate = door.MODULE
ROOT = Path(__file__).resolve().parent


class AquatraceReportingOfflineTests(unittest.TestCase):
    def test_acceptance_fixture_is_80_split_60_recover_20_hold(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 80)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "RECOVER"), 60)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "HOLD"), 20)
        loaded = gate.load_fixture()
        self.assertEqual(len(loaded), 80)
        self.assertEqual(
            [row["event_id"] for row in loaded],
            [row["event_id"] for row in rows],
        )
        codes = [row["expected_hold_code"] for row in rows if row["expected_state"] == "HOLD"]
        for code in gate.HOLD_CODES:
            self.assertEqual(codes.count(code), 5)
        dests = [row["destination"] for row in rows if row["expected_state"] == "RECOVER"]
        self.assertEqual(dests.count("CMDP"), 20)
        self.assertEqual(dests.count("NETDMR"), 20)
        self.assertEqual(dests.count("POWER_BI"), 20)

    def test_pass_contract_exact_counts_and_golden_hashes(self) -> None:
        result = gate.run_reporting()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.EXPECTED_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertNotEqual(gate.GOLDEN_AUDIT_SHA256, "PIN_AFTER_FIRST_RUN")
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)
        self.assertEqual(result["replay_audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(len(result["audit_sha256"]), 64)
        self.assertTrue(result["ok"])
        exports = result["export_records"]
        self.assertEqual(exports["CMDP"]["payload_sha256"], gate.GOLDEN_CMDP_SHA256)
        self.assertEqual(exports["NETDMR"]["payload_sha256"], gate.GOLDEN_NETDMR_SHA256)
        self.assertEqual(exports["POWER_BI"]["payload_sha256"], gate.GOLDEN_POWER_BI_SHA256)

    def test_sixty_recover_and_twenty_conflict_holds_with_exact_codes(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_reporting(rows)
        recovered = {item["event_id"]: item for item in result["recover_records"]}
        holds = {item["event_id"]: item for item in result["hold_records"]}
        self.assertEqual(len(recovered), 60)
        self.assertEqual(len(holds), 20)
        self.assertEqual(result["hold_code_counts"], {code: 5 for code in gate.HOLD_CODES})
        for row in rows:
            if row["expected_state"] == "RECOVER":
                item = recovered[row["event_id"]]
                self.assertEqual(item["state"], "RECOVER")
                self.assertEqual(item["destination"], row["destination"])
                self.assertEqual(item["source_hash"], row["source_hash"])
                self.assertFalse(item["submitted"])
                self.assertFalse(item["live"])
                self.assertEqual(item["interface_state"], "SYNTHETIC")
            else:
                hold = holds[row["event_id"]]
                self.assertEqual(hold["code"], row["expected_hold_code"])
                self.assertEqual(hold["state"], "HOLD")
                self.assertEqual(hold["owner_role"], gate.EXCEPTION_OWNER_ROLE)
                self.assertEqual(hold["owner_desk"], gate.EXCEPTION_OWNER_DESK)
                self.assertFalse(hold["released"])
                self.assertFalse(hold["submitted"])
        accounted = set(recovered) | set(holds)
        self.assertEqual(accounted, {row["event_id"] for row in rows})

    def test_export_contracts_exclude_holds_and_match_golden_payloads(self) -> None:
        result = gate.run_reporting()
        self.assertEqual(result["hold_leaks"], [])
        hold_hashes = {item["source_hash"] for item in result["hold_records"]}
        for name in gate.EXPORT_CONTRACTS:
            export = result["export_records"][name]
            self.assertEqual(export["row_count"], 20)
            self.assertEqual(export["payload"]["adapter"], "SYNTHETIC_READONLY")
            self.assertFalse(export["payload"]["live_submission"])
            self.assertFalse(export["payload"]["city_contact"])
            self.assertFalse(export["submitted"])
            self.assertFalse(export["live"])
            self.assertEqual(export["payload_sha256"], gate.golden_export_sha256(name))
            for row in export["payload"]["rows"]:
                self.assertNotIn(row["source_hash"], hold_hashes)
                self.assertTrue(row["source_hash"])

    def test_replay_adds_zero_and_keeps_audit_hash(self) -> None:
        first = gate.run_reporting()
        second = gate.run_reporting()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["replay"]["added_recover"], 0)
        self.assertEqual(first["replay"]["added_holds"], 0)
        ledger = gate.empty_ledger()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_event(ledger, row)
        self.assertEqual(len(ledger["recovered"]), 60)
        self.assertEqual(len(ledger["holds"]), 20)
        replay = gate.replay_into(ledger, rows)
        self.assertEqual(replay["added_recover"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["replay_noops"], 80)

    def test_named_human_only_export_release_zero_autonomous(self) -> None:
        result = gate.run_reporting()
        self.assertTrue(
            all(
                item["code"] == "AUTONOMOUS_RELEASE_DENIED"
                for item in result["autonomous_release_effects"]
            )
        )
        self.assertEqual(result["autonomous_released"], 0)
        self.assertEqual(sum(1 for item in result["human_release_effects"] if item.get("ok")), 3)
        ledger = gate.empty_ledger()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_event(ledger, row)
        gate.build_exports(ledger)
        auto = gate.release_export(ledger, "CMDP", "robot", "AUTONOMOUS")
        self.assertFalse(auto["ok"])
        self.assertEqual(auto["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(ledger["exports"]["CMDP"]["released"])
        other = gate.release_export(ledger, "CMDP", "someone", "INTAKE")
        self.assertFalse(other["ok"])
        self.assertEqual(other["code"], "HOLD_NAMED_HUMAN_REQUIRED")
        human = gate.release_export(
            ledger,
            "CMDP",
            gate.HUMAN_RELEASER,
            gate.HUMAN_ROLE,
        )
        self.assertTrue(human["ok"])
        self.assertTrue(ledger["exports"]["CMDP"]["released"])
        self.assertFalse(ledger["exports"]["CMDP"]["submitted"])
        self.assertFalse(ledger["exports"]["CMDP"]["live"])
        self.assertEqual(result["truth_gate"], "NOT_READY / HOLD / BUILD-AND-VERIFY")

    def test_no_live_adapters_submission_or_city_contact(self) -> None:
        result = gate.run_reporting()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SYNTHETIC")
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["live_submissions"], 0)
        self.assertEqual(result["city_contacts"], 0)
        self.assertEqual(result["customer_records"], 0)
        self.assertEqual(result["cash_usd"], 0)
        self.assertEqual(result["truth_gate"], gate.TRUTH_GATE)
        self.assertEqual(result["adapters"]["cmdp"], "SYNTHETIC_READONLY")
        self.assertEqual(result["adapters"]["netdmr"], "SYNTHETIC_READONLY")
        self.assertEqual(result["adapters"]["power_bi"], "SYNTHETIC_READONLY")
        self.assertEqual(result["adapters"]["lims"], "SYNTHETIC_READONLY")
        self.assertEqual(result["cite_only"]["private_sha"], "7a5ca7fe2856c49abf46bc248654a4d6f7af0335")
        self.assertNotIn("woahwhattheheck/aquatrace-lims", result["hard_off"])

    def test_official_command_exits_zero_when_goldens_locked(self) -> None:
        self.assertNotEqual(gate.GOLDEN_AUDIT_SHA256, "PIN_AFTER_FIRST_RUN")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "aquatrace_work_order_c_reporting_offline.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["failures"], [])
        self.assertEqual(payload["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(payload["official_binary"], "python3 aquatrace_work_order_c_reporting_offline.py")


if __name__ == "__main__":
    unittest.main()
