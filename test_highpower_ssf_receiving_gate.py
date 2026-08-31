#!/usr/bin/env python3
"""Binary acceptance for highpower-ssf-receiving-gate-lims-01.

Fail-closed. The runner is the product. HTML is a window, not the proof.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import highpower_ssf_receiving_gate as gate

ROOT = Path(__file__).resolve().parent


class HighpowerSsfReceivingGateTests(unittest.TestCase):
    def test_acceptance_fixture_is_200_split_160_40(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 200)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "ACCESSION"), 160)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "HOLD"), 40)
        holds = [row for row in rows if row["expected_state"] == "HOLD"]
        for code in gate.HOLD_CODES:
            self.assertEqual(sum(1 for row in holds if row["expected_hold_code"] == code), 5)

    def test_pass_contract_160_40_and_locked_digests(self) -> None:
        result = gate.run_gate(gate.build_acceptance_fixture())
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.EXPECTED_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["lineage_sha256"], gate.GOLDEN_LINEAGE_SHA256)
        self.assertEqual(result["accession_sha256"], gate.GOLDEN_ACCESSION_SHA256)
        self.assertEqual(result["report_sha256"], gate.GOLDEN_REPORT_SHA256)
        self.assertEqual(result["replay_audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertTrue(result["ok"])

    def test_exactly_160_accession_once(self) -> None:
        result = gate.run_gate(gate.build_acceptance_fixture())
        self.assertEqual(result["accessions"], 160)
        self.assertEqual(result["duplicate_accessions"], 0)
        ids = [item["accession_id"] for item in result["accession_records"]]
        pairs = [item["pair_id"] for item in result["accession_records"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(pairs), len(set(pairs)))
        for item in result["accession_records"]:
            self.assertTrue(item["accession_id"].startswith("HPV-ACC-"))
            self.assertTrue(item["study_id"].startswith("HPV-SYN-STUDY-"))
            self.assertFalse(item["live_test"])
            self.assertFalse(item["interface_live"])
            self.assertEqual(item["ssf"]["form_doc"], "HP-QC-067")
            self.assertEqual(item["receiving"]["form_doc"], "HP-LSOP-059")

    def test_all_40_hold_under_exact_discrepancy_code(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {item["pair_id"]: item for item in result["hold_records"]}
        self.assertEqual(len(holds), 40)
        self.assertEqual(result["hold_code_counts"], {code: 5 for code in gate.HOLD_CODES})
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["pair_id"]]
            self.assertEqual(hold["code"], row["expected_hold_code"])
            self.assertEqual(hold["state"], "HOLD")
            self.assertEqual(hold["owner_role"], gate.HOLD_OWNERS[row["expected_hold_code"]])
            self.assertFalse(any(hold["downstream"].values()))
        accounted = {item["pair_id"] for item in result["accession_records"]} | set(holds)
        self.assertEqual(accounted, {row["pair_id"] for row in rows})

    def test_zero_downstream_activity_while_held(self) -> None:
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["holds"]), 40)
        for pair_id in list(journal["holds"]):
            blocked = gate.start_test(journal, pair_id, actor="SYSTEM", actor_role="SYSTEM")
            self.assertFalse(blocked["ok"])
            self.assertEqual(blocked["code"], "DOWNSTREAM_BLOCKED_HOLD")
            named = gate.start_test(
                journal, pair_id, actor=gate.HUMAN_RELEASER, actor_role=gate.HUMAN_ROLE
            )
            self.assertEqual(named["code"], "DOWNSTREAM_BLOCKED_HOLD")
            report = gate.start_downstream(
                journal, pair_id, actor=gate.HUMAN_RELEASER, actor_role=gate.HUMAN_ROLE, action="WRITE_REPORT"
            )
            self.assertEqual(report["code"], "DOWNSTREAM_BLOCKED_HOLD")
            released = gate.release_hold(
                journal, pair_id, actor=gate.HUMAN_RELEASER, actor_role=gate.HUMAN_ROLE
            )
            self.assertFalse(released["ok"])
            self.assertEqual(released["code"], "HOLD_UNRESOLVED_NO_DOWNSTREAM")
            self.assertFalse(any(journal["holds"][pair_id]["downstream"].values()))
        self.assertEqual(sum(1 for item in journal["holds"].values() if any(item["downstream"].values())), 0)
        result = gate.run_gate()
        self.assertEqual(result["held_downstream"], 0)
        self.assertTrue(all(item["code"] == "DOWNSTREAM_BLOCKED_HOLD" for item in result["hold_test_attempts"]))
        self.assertTrue(all(item["code"] == "DOWNSTREAM_BLOCKED_HOLD" for item in result["hold_report_attempts"]))
        self.assertTrue(all(item["code"] == "SIMULATED_ONLY_NO_LIVE_TEST" for item in result["released_test_attempts"]))

    def test_every_field_retains_source_version_provenance(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        self.assertEqual(result["lineage_failures"], [])
        self.assertEqual(result["provenance_failures"], [])
        journal = result["journal"]
        sample = next(iter(journal["accessions"].values()))
        blocked = gate.mutate_source_lineage(journal, sample["accession_id"], "f" * 64)
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "IMMUTABLE_SOURCE_LINEAGE")
        self.assertEqual(blocked["source_hash"], sample["source_hash"])
        for item in list(result["accession_records"]) + list(result["hold_records"]):
            provenance = item["field_provenance"]
            self.assertEqual(set(provenance), set(gate.PROVENANCE_FIELDS))
            for name, cell in provenance.items():
                for side in ("ssf", "receiving"):
                    src = cell[side]
                    self.assertTrue(src["form_id"])
                    self.assertTrue(src["form_doc"])
                    self.assertTrue(src["form_rev"])
                    self.assertTrue(src["form_version"])
                    self.assertEqual(len(src["field_hash"]), 64)
                    self.assertIn(name, gate.PROVENANCE_FIELDS)

    def test_replay_is_idempotent_zero_duplicate_or_state_change(self) -> None:
        rows = gate.build_acceptance_fixture()
        first = gate.run_gate(rows)
        second = gate.run_gate(rows)
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["lineage_sha256"], second["lineage_sha256"])
        self.assertEqual(first["accession_sha256"], second["accession_sha256"])
        self.assertEqual(first["report_sha256"], second["report_sha256"])
        journal = gate.empty_journal()
        for row in rows:
            gate.ingest_row(journal, row)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["accession_count"], 160)
        self.assertEqual(replay["hold_count"], 40)
        self.assertEqual(replay["replay_noops"], 200)
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
        bot = gate.release_accession(journal, acc_id, actor="bot", actor_role="RECEIVING_RELEASE_OFFICER")
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
        self.assertFalse(journal["accessions"][acc_id]["live_test"])
        result = gate.run_gate()
        self.assertEqual(result["human_released"], 160)
        self.assertEqual(result["autonomous_released"], 0)
        self.assertTrue(all(item.get("code") == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"]))
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["live_tests"], 0)
        self.assertEqual(result["cash_usd"], 0)

    def test_dropped_valid_pair_fails_closed(self) -> None:
        rows = gate.build_acceptance_fixture()
        broken = [row for row in rows if row["expected_state"] == "ACCESSION"][:159]
        broken.extend(row for row in rows if row["expected_state"] == "HOLD")
        result = gate.run_gate(broken)
        self.assertIn("counts", gate.pass_contract(result))
        self.assertFalse(result["ok"])
        self.assertEqual(result["accessions"], 159)
        self.assertEqual(result["holds"], 40)

    def test_cli_processes_200_and_writes_receipts_and_state(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "highpower_ssf_receiving_gate.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["failures"], [])
        self.assertEqual(payload["actual"]["accessions"], 160)
        self.assertEqual(payload["actual"]["holds"], 40)
        self.assertEqual(payload["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(payload["report_sha256"], gate.GOLDEN_REPORT_SHA256)
        for rel in (
            gate.FIXTURE_PATH,
            gate.STATE_PATH,
            gate.RUN_RECEIPT_PATH,
            gate.ACCESSION_RECEIPT_PATH,
            gate.HOLD_RECEIPT_PATH,
            gate.LINEAGE_RECEIPT_PATH,
            gate.AUDIT_RECEIPT_PATH,
            gate.REPORT_RECEIPT_PATH,
            gate.CONTRACT_PATH,
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)
        fixture = json.loads((ROOT / gate.FIXTURE_PATH).read_text(encoding="utf-8"))
        self.assertEqual(len(fixture), 200)
        journal = json.loads((ROOT / gate.STATE_PATH).read_text(encoding="utf-8"))
        self.assertEqual(len(journal["accessions"]), 160)
        self.assertEqual(len(journal["holds"]), 40)
        accessions = json.loads((ROOT / gate.ACCESSION_RECEIPT_PATH).read_text(encoding="utf-8"))
        holds = json.loads((ROOT / gate.HOLD_RECEIPT_PATH).read_text(encoding="utf-8"))
        self.assertEqual(len(accessions), 160)
        self.assertEqual(len(holds), 40)
        replay = subprocess.run(
            [sys.executable, str(ROOT / "highpower_ssf_receiving_gate.py"), "--replay"],
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


if __name__ == "__main__":
    unittest.main()
