#!/usr/bin/env python3
"""Binary acceptance for westpak-scope-capacity-routing-lims-01.

Fail-closed. The runner is the product. HTML is not the proof.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import westpak_scope_capacity_routing as door

gate = door.MODULE
ROOT = Path(__file__).resolve().parent


class WestpakScopeCapacityRoutingTests(unittest.TestCase):
    def test_acceptance_fixture_is_240_split_200_40(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 240)
        self.assertEqual(sum(1 for row in rows if not row["block"]), 200)
        self.assertEqual(sum(1 for row in rows if row["block"]), 40)
        valid = [row for row in rows if not row["block"]]
        for program in gate.PROGRAMS:
            self.assertEqual(sum(1 for row in valid if row["program"] == program), 40)
        holds = [row for row in rows if row["block"]]
        for code in gate.HOLD_CODES:
            self.assertEqual(sum(1 for row in holds if row["expected_hold_code"] == code), 8)

    def test_pass_contract_exact_240_200_40_and_locked_digest(self) -> None:
        result = gate.run_routing(gate.build_acceptance_fixture())
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

    def test_all_200_route_to_exact_site_equipment_sequence(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_routing(rows)
        routed = [item for item in result["job_records"] if not item["block"]]
        self.assertEqual(len(routed), 200)
        self.assertEqual(result["routed_exact"], 200)
        self.assertEqual(result["method_match"], 200)
        self.assertEqual(result["wrong_route"], [])
        self.assertEqual(result["site_counts"], gate.EXPECTED_SITE_COUNTS)
        by_id = {row["job_id"]: row for row in rows if not row["block"]}
        for item in routed:
            src = by_id[item["job_id"]]
            method = gate.METHODS[item["method_id"]]
            self.assertEqual(item["site"], src["expected_site"])
            self.assertEqual(item["equipment_id"], src["expected_equipment"])
            self.assertEqual(item["sequence"], src["expected_sequence"])
            self.assertEqual(item["sequence"], list(method["sequence"]))
            self.assertEqual(item["method_id"], src["method_id"])
            self.assertEqual(item["method_revision"], method["revision"])
            self.assertEqual(gate.METHODS[item["method_id"]]["program"], item["program"])
            self.assertIn(item["site"], method["sites"])
            self.assertEqual(item["state"], "HUMAN_RELEASED")

    def test_all_40_block_with_expected_reason(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_routing(rows)
        holds = {item["job_id"]: item for item in result["hold_records"]}
        self.assertEqual(len(holds), 40)
        self.assertEqual(result["hold_code_counts"], gate.EXPECTED_HOLD_COUNTS)
        self.assertEqual(result["blocked_expected_reason"], 40)
        for row in rows:
            if not row["block"]:
                continue
            hold = holds[row["job_id"]]
            self.assertEqual(hold["code"], row["expected_hold_code"])
            verdict = gate.classify(row)
            self.assertFalse(verdict["ok"])
            self.assertEqual(verdict["code"], row["expected_hold_code"])
            self.assertFalse(hold["released"])
            self.assertFalse(hold["testing_started"])
        accounted = {item["job_id"] for item in result["job_records"] if not item["block"]} | set(holds)
        self.assertEqual(accounted, {row["job_id"] for row in rows})

    def test_transfers_only_where_fixture_authorizes(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_routing(rows)
        self.assertEqual(result["authorized_transfers"], 24)
        self.assertEqual(result["unauthorized_transfers"], 0)
        routed = [item for item in result["job_records"] if not item["block"]]
        transferred = [item for item in routed if item["transfer"]]
        self.assertEqual(len(transferred), 24)
        for item in transferred:
            src = next(row for row in rows if row["job_id"] == item["job_id"])
            self.assertTrue(gate.transfer_authorized(src["origin_site"], src["dest_site"], src["method_id"]))
            self.assertEqual(item["custody_roles"], list(gate.CUSTODY_TRANSFER))
        blocked_transfers = [
            row for row in rows if row["block"] and row["expected_hold_code"] == "HOLD_TRANSFER_NOT_AUTHORIZED"
        ]
        self.assertEqual(len(blocked_transfers), 8)
        for row in blocked_transfers:
            self.assertFalse(gate.transfer_authorized(row["origin_site"], row["dest_site"], row["method_id"]))
            self.assertNotEqual(row["origin_site"], row["dest_site"])

    def test_replay_creates_zero_duplicate_job_or_custody_events(self) -> None:
        first = gate.run_routing(gate.build_acceptance_fixture())
        second = gate.run_routing(gate.build_acceptance_fixture())
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(gate.sha256_hex(first["audit"]), first["audit_sha256"])
        self.assertEqual(first["replay"]["duplicate_job_events"], 0)
        self.assertEqual(first["replay"]["duplicate_custody_events"], 0)
        self.assertEqual(first["replay"]["added_jobs"], 0)
        self.assertEqual(first["replay"]["added_holds"], 0)
        self.assertEqual(first["replay"]["replay_noops"], 240)
        self.assertFalse(first["replay"]["state_changed"])
        self.assertEqual(first["replay_duplicate_job_events"], 0)
        self.assertEqual(first["replay_duplicate_custody_events"], 0)

    def test_named_human_release_only(self) -> None:
        result = gate.run_routing(gate.build_acceptance_fixture())
        self.assertTrue(all(not item.get("ok") for item in result["autonomous_release_effects"]))
        self.assertEqual(result["released_without_named_human"], 0)
        self.assertEqual(result["autonomous_released"], 0)
        self.assertEqual(sum(1 for item in result["human_release_effects"] if item.get("ok")), 200)
        denied = [item for item in result["human_release_effects"] if not item.get("ok")]
        self.assertEqual(len(denied), 40)
        self.assertTrue(all(item["code"] == "RELEASE_BLOCKED_OPEN_HOLD" for item in denied))
        self.assertEqual(result["released_after_named_human"], 200)
        self.assertEqual(result["blocked_released"], 0)

    def test_named_human_cannot_release_before_route_or_on_hold(self) -> None:
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        clean = next(item for item in rows if not item["block"])
        hold = next(item for item in rows if item["block"])
        early = gate.release_job(journal, clean["job_id"], actor=gate.NAMED_ACTOR, actor_role=gate.NAMED_ROLE)
        self.assertFalse(early["ok"])
        self.assertEqual(early["code"], "UNKNOWN_JOB")
        gate.ingest_job(journal, hold)
        blocked = gate.release_job(journal, hold["job_id"], actor=gate.NAMED_ACTOR, actor_role=gate.NAMED_ROLE)
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "RELEASE_BLOCKED_OPEN_HOLD")
        gate.ingest_job(journal, clean)
        auto = gate.release_job(journal, clean["job_id"], actor="SYSTEM", actor_role="SYSTEM")
        self.assertFalse(auto["ok"])
        self.assertEqual(auto["code"], "AUTONOMOUS_RELEASE_DENIED")
        human = gate.release_job(journal, clean["job_id"], actor=gate.NAMED_ACTOR, actor_role=gate.NAMED_ROLE)
        self.assertTrue(human["ok"])
        self.assertEqual(journal["jobs"][clean["job_id"]]["released_by"], gate.NAMED_ACTOR)

    def test_official_command_exits_zero_and_prints_240_200_40(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "westpak_scope_capacity_routing.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["actual"]["jobs"], 240)
        self.assertEqual(payload["actual"]["valid"], 200)
        self.assertEqual(payload["actual"]["blocked"], 40)
        self.assertEqual(payload["actual"]["routed_exact"], 200)
        self.assertEqual(payload["actual"]["blocked_expected_reason"], 40)
        self.assertEqual(payload["audit_sha256"], gate.golden_audit_sha256())


if __name__ == "__main__":
    unittest.main()
