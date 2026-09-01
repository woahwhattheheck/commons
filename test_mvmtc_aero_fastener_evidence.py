#!/usr/bin/env python3
"""Binary acceptance for mvmtc-aero-fastener-evidence-lims-01.

Fail-closed. The runner is the product. HTML is not the proof.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import mvmtc_aero_fastener_evidence as door

gate = door.MODULE
ROOT = Path(__file__).resolve().parent


class MvmtcAeroFastenerEvidenceTests(unittest.TestCase):
    def test_acceptance_fixture_is_100_split_75_25(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 100)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "READY"), 75)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "HOLD"), 25)
        holds = [row for row in rows if row["expected_state"] == "HOLD"]
        for code, expected_n in gate.EXPECTED_HOLD_COUNTS.items():
            self.assertEqual(sum(1 for row in holds if row["expected_hold_code"] == code), expected_n)

    def test_pass_contract_exact_100_75_25_and_locked_digest(self) -> None:
        result = gate.run_gate(gate.build_acceptance_fixture())
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.EXPECTED_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["replay_audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertTrue(result["ok"])

    def test_exactly_75_ready_create_worksheets_once(self) -> None:
        result = gate.run_gate(gate.build_acceptance_fixture())
        self.assertEqual(result["ready"], 75)
        self.assertEqual(result["worksheets_created"], 75)
        self.assertEqual(result["duplicate_records"], 0)
        for item in result["ready_records"]:
            self.assertEqual(item["state"], "HUMAN_RELEASED")
            self.assertTrue(item["worksheet_id"].startswith("WS-MVMTC-"))
            self.assertTrue(item["method_key"] in gate.METHODS)
            self.assertTrue(item["released"])
            self.assertEqual(item["released_by"], gate.HUMAN_RELEASER)

    def test_all_25_hold_under_exact_codes_and_create_no_worksheets(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {item["lot_id"]: item for item in result["hold_records"]}
        self.assertEqual(len(holds), 25)
        self.assertEqual(result["hold_code_counts"], gate.EXPECTED_HOLD_COUNTS)
        self.assertEqual(result["held_worksheets"], 0)
        self.assertEqual(result["held_downstream"], 0)
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["lot_id"]]
            self.assertEqual(hold["code"], row["expected_hold_code"])
            self.assertEqual(hold["state"], "HOLD")
            self.assertFalse(hold["worksheet_created"])
            self.assertFalse(any(hold["downstream"].values()))

    def test_zero_downstream_activity_while_held(self) -> None:
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_lot(journal, row)
        self.assertEqual(len(journal["holds"]), 25)
        for lot_id in list(journal["holds"]):
            blocked_release = gate.release_lot(
                journal, lot_id, actor=gate.HUMAN_RELEASER, actor_role=gate.HUMAN_ROLE
            )
            self.assertFalse(blocked_release["ok"])
            self.assertEqual(blocked_release["code"], "HOLD_BLOCKED_NO_RELEASE")
            self.assertFalse(journal["holds"][lot_id]["worksheet_created"])
            self.assertFalse(any(journal["holds"][lot_id]["downstream"].values()))

    def test_every_record_preserves_hashes_and_provenance(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        for item in result["ready_records"]:
            self.assertEqual(len(item["source_hash"]), 64)
            self.assertIn(item["discipline"], gate.TEST_DISCIPLINES)
            self.assertIn(item["material"], gate.MATERIALS)
            self.assertIn(item["category"], gate.CATEGORIES)

    def test_replay_is_idempotent_zero_duplicates_or_state_change(self) -> None:
        rows = gate.build_acceptance_fixture()
        first = gate.run_gate(rows)
        second = gate.run_gate(rows)
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        journal = gate.empty_journal()
        for row in rows:
            gate.ingest_lot(journal, row)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(replay["added_lot_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["lot_count"], 75)
        self.assertEqual(replay["hold_count"], 25)
        self.assertEqual(replay["replay_noops"], 100)
        self.assertFalse(replay["state_changed"])

    def test_named_human_release_mandatory_autonomous_denied(self) -> None:
        journal = gate.empty_journal()
        raw = next(item for item in gate.build_acceptance_fixture() if item["expected_state"] == "READY")
        ingested = gate.ingest_lot(journal, raw)
        lot_id = ingested["lot_id"]
        autonomous = gate.release_lot(journal, lot_id, actor="SYSTEM", actor_role="SYSTEM")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(journal["lots"][lot_id]["released"])

        bot = gate.release_lot(journal, lot_id, actor="bot", actor_role="NAMED_RELEASE_OFFICER")
        self.assertEqual(bot["code"], "AUTONOMOUS_RELEASE_DENIED")

        blank = gate.release_lot(journal, lot_id, actor="", actor_role=gate.HUMAN_ROLE)
        self.assertEqual(blank["code"], "AUTONOMOUS_RELEASE_DENIED")

        human = gate.release_lot(journal, lot_id, actor=gate.HUMAN_RELEASER, actor_role=gate.HUMAN_ROLE)
        self.assertTrue(human["ok"])
        self.assertEqual(human["code"], "HUMAN_RELEASED")
        self.assertEqual(journal["lots"][lot_id]["released_by"], gate.HUMAN_RELEASER)

        result = gate.run_gate()
        self.assertEqual(result["human_released"], 75)
        self.assertEqual(result["autonomous_released"], 0)
        self.assertTrue(all(item.get("code") == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"]))

    def test_cli_processes_100_and_writes_receipts(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "mvmtc_aero_fastener_evidence.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["failures"], [])
        self.assertEqual(payload["actual"]["ready"], 75)
        self.assertEqual(payload["actual"]["holds"], 25)
        self.assertEqual(payload["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)

        for rel in (
            gate.FIXTURE_PATH,
            gate.STATE_PATH,
            gate.RUN_RECEIPT_PATH,
            gate.LOT_RECEIPT_PATH,
            gate.HOLD_RECEIPT_PATH,
            gate.WORKSHEET_RECEIPT_PATH,
            gate.AUDIT_RECEIPT_PATH,
            gate.CONTRACT_PATH,
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

        replay = subprocess.run(
            [sys.executable, str(ROOT / "mvmtc_aero_fastener_evidence.py"), "--replay"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(replay.returncode, 0, replay.stderr or replay.stdout)
        replay_body = json.loads(replay.stdout)
        self.assertTrue(replay_body["ok"])
        self.assertEqual(replay_body["replay"]["added_lot_count"], 0)
        self.assertEqual(replay_body["replay"]["added_holds"], 0)
        self.assertFalse(replay_body["replay"]["state_changed"])
        self.assertTrue((ROOT / gate.REPLAY_RECEIPT_PATH).is_file())


if __name__ == "__main__":
    unittest.main()
