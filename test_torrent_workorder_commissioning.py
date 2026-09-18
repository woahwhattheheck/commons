#!/usr/bin/env python3
"""Binary acceptance for torrent-workorder-commissioning-lims-01.

Fail-closed. The runner is the product. HTML is not the proof.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import torrent_workorder_commissioning as gate

ROOT = Path(__file__).resolve().parent


class TorrentWorkorderCommissioningLimsTests(unittest.TestCase):
    def test_acceptance_fixture_is_500_split_400_100(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 500)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "WORK_ORDER"), 400)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "QUARANTINE"), 100)
        holds = [row for row in rows if row["expected_state"] == "QUARANTINE"]
        for code in gate.QUARANTINE_CODES:
            self.assertEqual(sum(1 for row in holds if row["expected_quarantine_code"] == code), 10)
        self.assertEqual(len({row["coc_id"] for row in rows}), 500)
        self.assertEqual(len({row["sample_id"] for row in rows}), 500)

    def test_pass_contract_400_100_and_locked_digests(self) -> None:
        result = gate.run_commissioning(gate.build_acceptance_fixture())
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.EXPECTED_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["work_orders"], 400)
        self.assertEqual(result["quarantines"], 100)
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["lineage_sha256"], gate.GOLDEN_LINEAGE_SHA256)
        self.assertEqual(result["work_order_sha256"], gate.GOLDEN_WORK_ORDER_SHA256)
        self.assertEqual(result["field_digest_sha256"], gate.GOLDEN_FIELD_DIGEST_SHA256)
        self.assertEqual(result["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)
        self.assertEqual(result["replay_audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertTrue(result["ok"])

    def test_valid_work_orders_create_once_with_exact_field_parity(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_commissioning(rows)
        self.assertEqual(result["work_orders"], 400)
        self.assertEqual(result["duplicate_work_orders"], 0)
        self.assertEqual(result["parity_failures"], [])
        keys = [item["work_order_key"] for item in result["work_order_records"]]
        self.assertEqual(len(keys), len(set(keys)))
        by_coc = {row["coc_id"]: row for row in rows if row["expected_state"] == "WORK_ORDER"}
        for item in result["work_order_records"]:
            src = by_coc[item["coc_id"]]
            self.assertEqual(item["work_order_id"], src["work_order_id"])
            self.assertEqual(item["matrix"], src["matrix"])
            self.assertEqual(item["container"], src["container"])
            self.assertEqual(item["tat"], src["tat"])
            self.assertEqual(item["edd_format"], src["edd_format"])
            self.assertEqual(item["sample_id"], src["sample_id"])
            self.assertEqual(item["analyses"], src["analyses"])
            self.assertEqual(item["parity"]["matrix"], src["matrix"])
            self.assertEqual(item["parity"]["container"], src["container"])
            self.assertEqual(item["parity"]["tat"], src["tat"])
            self.assertEqual(item["parity"]["edd_format"], src["edd_format"])
            self.assertEqual(item["parity"]["facility_id_normalized"], gate.CURRENT_FACILITY)
            self.assertFalse(item["interface_live"])
            self.assertFalse(item["live_lims"])

    def test_all_100_quarantine_with_expected_reason(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_commissioning(rows)
        holds = {item["coc_id"]: item for item in result["quarantine_records"]}
        self.assertEqual(len(holds), 100)
        self.assertEqual(result["quarantine_code_counts"], {code: 10 for code in gate.QUARANTINE_CODES})
        for row in rows:
            if row["expected_state"] != "QUARANTINE":
                continue
            hold = holds[row["coc_id"]]
            self.assertEqual(hold["code"], row["expected_quarantine_code"])
            self.assertEqual(hold["state"], "QUARANTINE")
            self.assertEqual(hold["owner_role"], gate.QUARANTINE_OWNERS[row["expected_quarantine_code"]])
            self.assertFalse(hold["released"])
            self.assertFalse(hold["live_lims"])
        accounted = {item["coc_id"] for item in result["work_order_records"]} | set(holds)
        self.assertEqual(accounted, {row["coc_id"] for row in rows})

    def test_old_and_current_facility_ids_normalize_deterministically(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_commissioning(rows)
        self.assertEqual(result["facility_failures"], [])
        raws = {item["facility_id_raw"] for item in result["work_order_records"]}
        self.assertEqual(raws, set(gate.FACILITY_MAP))
        for item in result["work_order_records"]:
            self.assertEqual(item["facility_id_normalized"], gate.CURRENT_FACILITY)
            self.assertEqual(gate.normalize_facility(item["facility_id_raw"]), gate.CURRENT_FACILITY)
        unmapped = [
            item
            for item in result["quarantine_records"]
            if item["code"] == "QUARANTINE_UNMAPPED_FACILITY_ID"
        ]
        self.assertEqual(len(unmapped), 10)
        for item in unmapped:
            self.assertEqual(item["facility_id"], gate.UNMAPPED_FACILITY)
            self.assertIsNone(item["facility_id_normalized"])
            self.assertIsNone(gate.normalize_facility(item["facility_id"]))

    def test_replay_is_idempotent_zero_added_or_state_change(self) -> None:
        rows = gate.build_acceptance_fixture()
        first = gate.run_commissioning(rows)
        second = gate.run_commissioning(rows)
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["lineage_sha256"], second["lineage_sha256"])
        self.assertEqual(first["work_order_sha256"], second["work_order_sha256"])
        self.assertEqual(first["field_digest_sha256"], second["field_digest_sha256"])
        journal = gate.empty_journal()
        for row in rows:
            gate.ingest_row(journal, row)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(replay["added_work_orders"], 0)
        self.assertEqual(replay["added_quarantines"], 0)
        self.assertEqual(replay["work_order_count"], 400)
        self.assertEqual(replay["quarantine_count"], 100)
        self.assertEqual(replay["replay_noops"], 500)
        self.assertFalse(replay["state_changed"])
        self.assertEqual(first["replay"]["added_work_orders"], 0)
        self.assertEqual(first["replay"]["added_quarantines"], 0)
        self.assertFalse(first["replay"]["state_changed"])

    def test_named_human_release_mandatory_no_autonomous_release(self) -> None:
        journal = gate.empty_journal()
        raw = next(item for item in gate.build_acceptance_fixture() if item["expected_state"] == "WORK_ORDER")
        ingested = gate.ingest_row(journal, raw)
        wo_key = ingested["work_order_key"]
        autonomous = gate.release_work_order(journal, wo_key, actor="SYSTEM", actor_role="SYSTEM")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(journal["work_orders"][wo_key]["released"])
        bot = gate.release_work_order(journal, wo_key, actor="bot", actor_role="NAMED_HUMAN_RELEASER")
        self.assertEqual(bot["code"], "AUTONOMOUS_RELEASE_DENIED")
        blank = gate.release_work_order(journal, wo_key, actor="", actor_role=gate.HUMAN_ROLE)
        self.assertEqual(blank["code"], "AUTONOMOUS_RELEASE_DENIED")
        auto_name = gate.release_work_order(journal, wo_key, actor="AUTO", actor_role=gate.HUMAN_ROLE)
        self.assertEqual(auto_name["code"], "AUTONOMOUS_RELEASE_DENIED")
        human = gate.release_work_order(journal, wo_key, actor=gate.HUMAN_RELEASER, actor_role=gate.HUMAN_ROLE)
        self.assertTrue(human["ok"])
        self.assertEqual(human["code"], "HUMAN_RELEASED")
        self.assertEqual(journal["work_orders"][wo_key]["released_by"], gate.HUMAN_RELEASER)
        live = gate.production_write(journal, wo_key)
        self.assertFalse(live["ok"])
        self.assertEqual(live["code"], "SIMULATED_ONLY_NO_PRODUCTION_WRITE")
        self.assertFalse(journal["work_orders"][wo_key]["live_lims"])
        self.assertEqual(journal["production_writes"], 0)
        result = gate.run_commissioning()
        self.assertEqual(result["human_released"], 400)
        self.assertEqual(result["autonomous_released"], 0)
        self.assertTrue(
            all(item.get("code") == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["live_lims"], 0)
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["cash_usd"], 0)
        q_id = next(item["coc_id"] for item in result["quarantine_records"])
        denied = gate.release_quarantine(
            result["journal"], q_id, actor=gate.HUMAN_RELEASER, actor_role=gate.HUMAN_ROLE
        )
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "QUARANTINE_UNRESOLVED")

    def test_air_water_soil_and_source_hashes_preserved(self) -> None:
        result = gate.run_commissioning(gate.build_acceptance_fixture())
        self.assertEqual(result["matrix_counts"], {"AIR": 134, "WATER": 133, "SOIL": 133})
        self.assertEqual(result["lineage_failures"], [])
        self.assertEqual(sum(result["matrix_counts"].values()), 400)
        sample = next(iter(result["journal"]["work_orders"].values()))
        self.assertEqual(len(sample["source_hash"]), 64)
        self.assertIn("matrix", sample["field_lineage"])
        self.assertIn("tat", sample["field_lineage"])
        self.assertIn("facility_id", sample["field_lineage"])

    def test_cli_processes_500_and_writes_receipts_and_state(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "torrent_workorder_commissioning.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["failures"], [])
        self.assertEqual(payload["actual"]["work_orders"], 400)
        self.assertEqual(payload["actual"]["quarantines"], 100)
        self.assertEqual(payload["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        for rel in (
            gate.FIXTURE_PATH,
            gate.STATE_PATH,
            gate.RUN_RECEIPT_PATH,
            gate.WORK_ORDER_RECEIPT_PATH,
            gate.QUARANTINE_RECEIPT_PATH,
            gate.LINEAGE_RECEIPT_PATH,
            gate.AUDIT_RECEIPT_PATH,
            gate.FIELD_DIGEST_PATH,
            gate.CONTRACT_PATH,
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)
        fixture = json.loads((ROOT / gate.FIXTURE_PATH).read_text(encoding="utf-8"))
        self.assertEqual(len(fixture), 500)
        journal = json.loads((ROOT / gate.STATE_PATH).read_text(encoding="utf-8"))
        self.assertEqual(len(journal["work_orders"]), 400)
        self.assertEqual(len(journal["quarantines"]), 100)
        work_orders = json.loads((ROOT / gate.WORK_ORDER_RECEIPT_PATH).read_text(encoding="utf-8"))
        holds = json.loads((ROOT / gate.QUARANTINE_RECEIPT_PATH).read_text(encoding="utf-8"))
        self.assertEqual(len(work_orders), 400)
        self.assertEqual(len(holds), 100)
        replay = subprocess.run(
            [sys.executable, str(ROOT / "torrent_workorder_commissioning.py"), "--replay"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(replay.returncode, 0, replay.stderr or replay.stdout)
        replay_body = json.loads(replay.stdout)
        self.assertTrue(replay_body["ok"])
        self.assertEqual(replay_body["replay"]["added_work_orders"], 0)
        self.assertEqual(replay_body["replay"]["added_quarantines"], 0)
        self.assertFalse(replay_body["replay"]["state_changed"])
        self.assertTrue((ROOT / gate.REPLAY_RECEIPT_PATH).is_file())

    def test_cli_fails_closed_when_a_valid_row_is_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            rows = gate.build_acceptance_fixture()
            broken = [row for row in rows if row["expected_state"] == "WORK_ORDER"][:399]
            broken.extend(row for row in rows if row["expected_state"] == "QUARANTINE")
            result = gate.run_commissioning(broken)
            self.assertNotEqual(gate.pass_contract(result), [])
            self.assertIn("counts", gate.pass_contract(result))
            self.assertFalse(result["ok"])
            self.assertTrue(dest.exists())

    def test_no_phone_or_personal_email_in_runner_bytes(self) -> None:
        text = (ROOT / "torrent_workorder_commissioning.py").read_text(encoding="utf-8")
        self.assertNotIn("6803283352", text)
        self.assertNotIn("mukesh.jani@", text)
        self.assertNotIn("@torrentlaboratory.com", text)


if __name__ == "__main__":
    unittest.main()
