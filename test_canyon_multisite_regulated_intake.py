#!/usr/bin/env python3
"""Binary acceptance for canyon-multisite-regulated-intake-lims-01.

Fail-closed. The runner is the product. HTML is not the proof.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import canyon_multisite_regulated_intake as gate

ROOT = Path(__file__).resolve().parent


class CanyonMultisiteRegulatedIntakeTests(unittest.TestCase):
    def test_acceptance_fixture_is_300_split_240_60(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 300)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "ACCESSION"), 240)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "HOLD"), 60)
        holds = [row for row in rows if row["expected_state"] == "HOLD"]
        for code in gate.HOLD_CODES:
            self.assertEqual(sum(1 for row in holds if row["expected_hold_code"] == code), 10)

    def test_pass_contract_240_60_and_locked_digests(self) -> None:
        result = gate.run_intake(gate.build_acceptance_fixture())
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.EXPECTED_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["lineage_sha256"], gate.GOLDEN_LINEAGE_SHA256)
        self.assertEqual(result["accession_sha256"], gate.GOLDEN_ACCESSION_SHA256)
        self.assertEqual(result["replay_audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertTrue(result["ok"])

    def test_exactly_240_accession_once_at_correct_site(self) -> None:
        result = gate.run_intake(gate.build_acceptance_fixture())
        self.assertEqual(result["accessions"], 240)
        self.assertEqual(result["wrong_site"], [])
        self.assertEqual(result["site_counts"], {"BLF": 120, "RSH": 80, "VST": 40})
        self.assertEqual(result["duplicate_accessions"], 0)
        ids = [item["accession_id"] for item in result["accession_records"]]
        self.assertEqual(len(ids), len(set(ids)))
        for item in result["accession_records"]:
            self.assertIn(item["discipline"], gate.SITE_SCOPE[item["site"]])
            self.assertEqual(item["method_code"], gate.METHODS[item["discipline"]])
            self.assertTrue(item["accession_id"].startswith(item["site"] and f"CYN-{item['site']}-ACC-"))
            self.assertFalse(item["testing_started"])
            self.assertFalse(item["interface_live"])
            self.assertFalse(item["live_test"])

    def test_all_60_hold_with_exact_reason(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_intake(rows)
        holds = {item["submission_id"]: item for item in result["hold_records"]}
        self.assertEqual(len(holds), 60)
        self.assertEqual(result["hold_code_counts"], {code: 10 for code in gate.HOLD_CODES})
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["submission_id"]]
            self.assertEqual(hold["code"], row["expected_hold_code"])
            self.assertEqual(hold["state"], "HOLD")
            self.assertEqual(hold["owner_role"], gate.HOLD_OWNERS[row["expected_hold_code"]])
            self.assertFalse(hold["testing_started"])
            self.assertFalse(hold["live_test"])
        accounted = {item["submission_id"] for item in result["accession_records"]} | set(holds)
        self.assertEqual(accounted, {row["submission_id"] for row in rows})

    def test_zero_held_samples_start_testing(self) -> None:
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["holds"]), 60)
        for submission_id in list(journal["holds"]):
            blocked = gate.start_test(journal, submission_id, actor="SYSTEM", actor_role="SYSTEM")
            self.assertFalse(blocked["ok"])
            self.assertEqual(blocked["code"], "TEST_BLOCKED_HOLD")
            self.assertFalse(blocked["testing_started"])
            named = gate.start_test(
                journal, submission_id, actor=gate.HUMAN_RELEASER, actor_role=gate.HUMAN_ROLE
            )
            self.assertEqual(named["code"], "TEST_BLOCKED_HOLD")
            released = gate.release_hold(
                journal, submission_id, actor=gate.HUMAN_RELEASER, actor_role=gate.HUMAN_ROLE
            )
            self.assertFalse(released["ok"])
            self.assertEqual(released["code"], "HOLD_UNRESOLVED_NO_TEST")
            self.assertFalse(journal["holds"][submission_id]["testing_started"])
        self.assertEqual(sum(1 for item in journal["holds"].values() if item["testing_started"]), 0)
        result = gate.run_intake()
        self.assertEqual(result["held_testing_started"], 0)
        self.assertTrue(all(item["code"] == "TEST_BLOCKED_HOLD" for item in result["hold_test_attempts"]))
        self.assertTrue(all(item["code"] == "SIMULATED_ONLY_NO_LIVE_TEST" for item in result["released_test_attempts"]))

    def test_source_hashes_and_field_lineage_preserved(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_intake(rows)
        self.assertEqual(result["lineage_failures"], [])
        self.assertEqual(result["lineage_sha256"], gate.GOLDEN_LINEAGE_SHA256)
        journal = result["journal"]
        sample = next(iter(journal["accessions"].values()))
        blocked = gate.mutate_source_lineage(journal, sample["accession_id"], "f" * 64)
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "IMMUTABLE_SOURCE_LINEAGE")
        self.assertEqual(blocked["source_hash"], sample["source_hash"])
        for item in result["accession_records"]:
            self.assertEqual(len(item["source_hash"]), 64)
            self.assertEqual(set(item["field_lineage"]), {"sponsor_code", "lot_code", "material_family", "origin_record"})

    def test_replay_is_idempotent_zero_duplicate_or_state_change(self) -> None:
        rows = gate.build_acceptance_fixture()
        first = gate.run_intake(rows)
        second = gate.run_intake(rows)
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["lineage_sha256"], second["lineage_sha256"])
        self.assertEqual(first["accession_sha256"], second["accession_sha256"])
        journal = gate.empty_journal()
        for row in rows:
            gate.ingest_row(journal, row)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["accession_count"], 240)
        self.assertEqual(replay["hold_count"], 60)
        self.assertEqual(replay["replay_noops"], 300)
        self.assertFalse(replay["state_changed"])
        self.assertEqual(first["replay"]["added_accession_count"], 0)
        self.assertFalse(first["replay"]["state_changed"])

    def test_named_human_release_mandatory_no_autonomous_release(self) -> None:
        journal = gate.empty_journal()
        raw = next(item for item in gate.build_acceptance_fixture() if item["expected_state"] == "ACCESSION")
        ingested = gate.ingest_row(journal, raw)
        acc_id = ingested["accession_id"]
        autonomous = gate.release_accession(journal, acc_id, actor="SYSTEM", actor_role="SYSTEM")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(journal["accessions"][acc_id]["released"])
        bot = gate.release_accession(journal, acc_id, actor="bot", actor_role="RELEASE_OFFICER")
        self.assertEqual(bot["code"], "AUTONOMOUS_RELEASE_DENIED")
        blank = gate.release_accession(journal, acc_id, actor="", actor_role=gate.HUMAN_ROLE)
        self.assertEqual(blank["code"], "AUTONOMOUS_RELEASE_DENIED")
        before_release = gate.start_test(journal, acc_id, actor=gate.HUMAN_RELEASER, actor_role=gate.HUMAN_ROLE)
        self.assertEqual(before_release["code"], "HUMAN_RELEASE_REQUIRED")
        human = gate.release_accession(journal, acc_id, actor=gate.HUMAN_RELEASER, actor_role=gate.HUMAN_ROLE)
        self.assertTrue(human["ok"])
        self.assertEqual(human["code"], "HUMAN_RELEASED")
        self.assertEqual(journal["accessions"][acc_id]["released_by"], gate.HUMAN_RELEASER)
        live = gate.start_test(journal, acc_id, actor=gate.HUMAN_RELEASER, actor_role=gate.HUMAN_ROLE)
        self.assertFalse(live["ok"])
        self.assertEqual(live["code"], "SIMULATED_ONLY_NO_LIVE_TEST")
        self.assertFalse(journal["accessions"][acc_id]["testing_started"])
        self.assertFalse(journal["accessions"][acc_id]["live_test"])
        result = gate.run_intake()
        self.assertEqual(result["human_released"], 240)
        self.assertEqual(result["autonomous_released"], 0)
        self.assertTrue(all(item.get("code") == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"]))
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["live_tests"], 0)
        self.assertEqual(result["cash_usd"], 0)

    def test_cli_processes_300_and_writes_receipts_and_state(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "canyon_multisite_regulated_intake.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["failures"], [])
        self.assertEqual(payload["actual"]["accessions"], 240)
        self.assertEqual(payload["actual"]["holds"], 60)
        self.assertEqual(payload["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        for rel in (
            gate.FIXTURE_PATH,
            gate.STATE_PATH,
            gate.RUN_RECEIPT_PATH,
            gate.ACCESSION_RECEIPT_PATH,
            gate.HOLD_RECEIPT_PATH,
            gate.LINEAGE_RECEIPT_PATH,
            gate.AUDIT_RECEIPT_PATH,
            gate.CONTRACT_PATH,
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)
        fixture = json.loads((ROOT / gate.FIXTURE_PATH).read_text(encoding="utf-8"))
        self.assertEqual(len(fixture), 300)
        journal = json.loads((ROOT / gate.STATE_PATH).read_text(encoding="utf-8"))
        self.assertEqual(len(journal["accessions"]), 240)
        self.assertEqual(len(journal["holds"]), 60)
        accessions = json.loads((ROOT / gate.ACCESSION_RECEIPT_PATH).read_text(encoding="utf-8"))
        holds = json.loads((ROOT / gate.HOLD_RECEIPT_PATH).read_text(encoding="utf-8"))
        self.assertEqual(len(accessions), 240)
        self.assertEqual(len(holds), 60)
        replay = subprocess.run(
            [sys.executable, str(ROOT / "canyon_multisite_regulated_intake.py"), "--replay"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(replay.returncode, 0, replay.stderr or replay.stdout)
        replay_body = json.loads(replay.stdout)
        self.assertTrue(replay_body["ok"])
        self.assertEqual(replay_body["replay"]["added_accession_count"], 0)
        self.assertEqual(replay_body["replay"]["added_holds"], 0)
        self.assertFalse(replay_body["replay"]["state_changed"])
        self.assertTrue((ROOT / gate.REPLAY_RECEIPT_PATH).is_file())

    def test_cli_fails_closed_when_a_complete_row_is_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            # Local mutation of a loaded fixture must fail the contract.
            rows = gate.build_acceptance_fixture()
            broken = [row for row in rows if row["expected_state"] == "ACCESSION"][:239]
            broken.extend(row for row in rows if row["expected_state"] == "HOLD")
            result = gate.run_intake(broken)
            self.assertNotEqual(gate.pass_contract(result), [])
            self.assertIn("counts", gate.pass_contract(result))
            self.assertFalse(result["ok"])
            self.assertEqual(dest.exists(), True)


if __name__ == "__main__":
    unittest.main()
