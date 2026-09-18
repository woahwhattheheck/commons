#!/usr/bin/env python3
"""Binary acceptance for bsk-multilab-accession-parity-lims-01.

Fail-closed. The runner is the product. HTML is not the proof.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import bsk_multilab_accession_parity as door

gate = door.MODULE
ROOT = Path(__file__).resolve().parent


class BskMultilabAccessionParityTests(unittest.TestCase):
    def test_acceptance_fixture_is_600_split_480_120_and_100_per_lab(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 600)
        self.assertEqual(sum(1 for row in rows if not row["block"]), 480)
        self.assertEqual(sum(1 for row in rows if row["block"]), 120)
        for lab in gate.LABS:
            total = [row for row in rows if row["home_lab"] == lab]
            valid = [row for row in total if not row["block"]]
            blocked = [row for row in total if row["block"]]
            self.assertEqual(len(total), 100, lab)
            self.assertEqual(len(valid), 80, lab)
            self.assertEqual(len(blocked), 20, lab)
        holds = [row for row in rows if row["block"]]
        for code in gate.HOLD_CODES:
            self.assertEqual(sum(1 for row in holds if row["expected_hold_code"] == code), 20)
        self.assertEqual(len({row["sample_id"] for row in rows}), 600)
        self.assertEqual(len({row["coc_id"] for row in rows}), 600)

    def test_pass_contract_exact_600_480_120_and_locked_digest(self) -> None:
        result = gate.run_gate(gate.build_acceptance_fixture())
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

    def test_every_valid_field_maps_exactly_once_to_correct_lab(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        routed = result["accession_records"]
        self.assertEqual(len(routed), 480)
        self.assertEqual(result["routed_exact"], 480)
        self.assertEqual(result["mapped_once"], 480)
        self.assertEqual(result["wrong_route"], [])
        self.assertEqual(result["lab_counts"], gate.EXPECTED_LAB_COUNTS)
        by_id = {row["coc_id"]: row for row in rows if not row["block"]}
        seen_accessions = set()
        seen_samples = set()
        for item in routed:
            src = by_id[item["coc_id"]]
            self.assertEqual(item["lab"], src["expected_lab"])
            self.assertEqual(item["lab"], src["home_lab"])
            self.assertEqual(item["analysis_id"], src["analysis_id"])
            self.assertEqual(item["matrix"], src["matrix"])
            self.assertEqual(item["sample_id"], src["sample_id"])
            self.assertEqual(item["source_hash"], src["source_hash"])
            self.assertEqual(item["source_coordinate"], src["source_coordinate"])
            self.assertTrue(item["source_hash"])
            self.assertTrue(item["source_coordinate"])
            self.assertEqual(len(item["source_hash"]), 64)
            maps = item["field_map"]
            self.assertEqual(set(maps.values()), {src["expected_lab"]})
            for field in gate.MAP_FIELDS:
                self.assertEqual(maps[field], src["expected_lab"], field)
            self.assertEqual(item["state"], "HUMAN_RELEASED")
            self.assertNotIn(item["accession_id"], seen_accessions)
            self.assertNotIn(item["sample_id"], seen_samples)
            seen_accessions.add(item["accession_id"])
            seen_samples.add(item["sample_id"])
            self.assertEqual(item["accession_id"], gate.accession_id(item["coc_id"], item["source_hash"]))

    def test_all_120_block_with_expected_reason(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {item["coc_id"]: item for item in result["hold_records"]}
        self.assertEqual(len(holds), 120)
        self.assertEqual(result["hold_code_counts"], gate.EXPECTED_HOLD_COUNTS)
        self.assertEqual(result["blocked_expected_reason"], 120)
        for row in rows:
            if not row["block"]:
                continue
            hold = holds[row["coc_id"]]
            self.assertEqual(hold["code"], row["expected_hold_code"])
            verdict = gate.classify(row)
            self.assertFalse(verdict["ok"])
            self.assertEqual(verdict["code"], row["expected_hold_code"])
            self.assertFalse(hold["released"])
            self.assertEqual(hold["owner_role"], gate.EXCEPTION_OWNER_ROLE)
            self.assertEqual(hold["owner_desk"], gate.EXCEPTION_OWNER_DESK)
            self.assertTrue(hold["source_hash"])
            self.assertTrue(hold["source_coordinate"])
        accounted = {item["coc_id"] for item in result["accession_records"]} | set(holds)
        self.assertEqual(accounted, {row["coc_id"] for row in rows})

    def test_zero_cross_facility_routing(self) -> None:
        result = gate.run_gate(gate.build_acceptance_fixture())
        self.assertEqual(result["cross_facility_routes"], 0)
        hold_ids = {item["coc_id"] for item in result["hold_records"]}
        for item in result["accession_records"]:
            self.assertEqual(item["lab"], item["home_lab"])
            self.assertNotIn(item["coc_id"], hold_ids)
        for route in result["route_records"]:
            home = next(item["home_lab"] for item in result["accession_records"] if item["coc_id"] == route["coc_id"])
            self.assertEqual(route["lab"], home)
        for hold in result["hold_records"]:
            self.assertIsNone(next((item for item in result["route_records"] if item["coc_id"] == hold["coc_id"]), None))

    def test_replay_creates_zero_new_records(self) -> None:
        first = gate.run_gate(gate.build_acceptance_fixture())
        second = gate.run_gate(gate.build_acceptance_fixture())
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(gate.sha256_hex(first["audit"]), first["audit_sha256"])
        self.assertEqual(first["replay"]["added_records"], 0)
        self.assertEqual(first["replay"]["added_holds"], 0)
        self.assertEqual(first["replay"]["added_routes"], 0)
        self.assertEqual(first["replay"]["added_accessions"], 0)
        self.assertEqual(first["replay"]["replay_noops"], 600)
        self.assertEqual(first["replay"]["duplicate_events"], 0)
        self.assertFalse(first["replay"]["state_changed"])
        self.assertEqual(first["replay_added_records"], 0)

    def test_named_human_release_only(self) -> None:
        result = gate.run_gate(gate.build_acceptance_fixture())
        self.assertTrue(all(not item.get("ok") for item in result["autonomous_release_effects"]))
        self.assertEqual(result["released_without_named_human"], 0)
        self.assertEqual(result["autonomous_released"], 0)
        self.assertEqual(sum(1 for item in result["human_release_effects"] if item.get("ok")), 480)
        denied = [item for item in result["human_release_effects"] if not item.get("ok")]
        self.assertEqual(len(denied), 120)
        self.assertTrue(all(item["code"] == "RELEASE_BLOCKED_OPEN_HOLD" for item in denied))
        self.assertEqual(result["released_after_named_human"], 480)
        self.assertEqual(result["blocked_released"], 0)

    def test_named_human_cannot_release_before_route_or_on_hold(self) -> None:
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        clean = next(item for item in rows if not item["block"])
        hold = next(item for item in rows if item["block"])
        early = gate.release_coc(journal, clean["coc_id"], actor=gate.NAMED_ACTOR, actor_role=gate.NAMED_ROLE)
        self.assertFalse(early["ok"])
        self.assertEqual(early["code"], "UNKNOWN_COC")
        gate.ingest_coc(journal, hold)
        blocked = gate.release_coc(journal, hold["coc_id"], actor=gate.NAMED_ACTOR, actor_role=gate.NAMED_ROLE)
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "RELEASE_BLOCKED_OPEN_HOLD")
        gate.ingest_coc(journal, clean)
        auto = gate.release_coc(journal, clean["coc_id"], actor="SYSTEM", actor_role="SYSTEM")
        self.assertFalse(auto["ok"])
        self.assertEqual(auto["code"], "AUTONOMOUS_RELEASE_DENIED")
        human = gate.release_coc(journal, clean["coc_id"], actor=gate.NAMED_ACTOR, actor_role=gate.NAMED_ROLE)
        self.assertTrue(human["ok"])
        self.assertEqual(journal["accessions"][clean["coc_id"]]["released_by"], gate.NAMED_ACTOR)

    def test_official_command_exits_zero_and_prints_600_480_120(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "bsk_multilab_accession_parity.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["actual"]["cocs"], 600)
        self.assertEqual(payload["actual"]["valid"], 480)
        self.assertEqual(payload["actual"]["blocked"], 120)
        self.assertEqual(payload["actual"]["routed_exact"], 480)
        self.assertEqual(payload["actual"]["blocked_expected_reason"], 120)
        self.assertEqual(payload["actual"]["cross_facility_routes"], 0)
        self.assertEqual(payload["audit_sha256"], gate.golden_audit_sha256())


if __name__ == "__main__":
    unittest.main()
