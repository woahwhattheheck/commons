#!/usr/bin/env python3
"""Binary acceptance for pcl-scope-sla-routing-lims-01."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNNER_PATH = ROOT / "revenue" / "pcl_scope_sla_routing" / "runner.py"
SPEC = importlib.util.spec_from_file_location("pcl_scope_sla_routing_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


EXPECTED = {
    "orders": 180,
    "valid": 150,
    "blocked": 30,
    "integrity": 40,
    "aging": 40,
    "distribution": 40,
    "product": 30,
    "incomplete": 15,
    "outside_site_scope": 15,
    "routed_exact": 150,
    "blocked_expected_reason": 30,
    "custody_complete": 150,
    "dock_to_start_exact": 150,
    "report_sla_exact": 150,
    "released_without_named_qa": 0,
    "released_after_named_qa": 150,
    "blocked_released": 0,
    "replay_changed_records": 0,
}


class PclScopeSlaRoutingTests(unittest.TestCase):
    def test_acceptance_fixture_is_180_orders_150_valid_30_blocked(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 180)
        self.assertEqual(sum(1 for row in rows if not row["block"]), 150)
        self.assertEqual(sum(1 for row in rows if row["block"]), 30)
        families = {row["family"] for row in rows if not row["block"]}
        self.assertEqual(families, {"INTEGRITY", "AGING", "DISTRIBUTION", "PRODUCT"})
        self.assertEqual(sum(1 for row in rows if not row["block"] and row["family"] == "INTEGRITY"), 40)
        self.assertEqual(sum(1 for row in rows if not row["block"] and row["family"] == "AGING"), 40)
        self.assertEqual(sum(1 for row in rows if not row["block"] and row["family"] == "DISTRIBUTION"), 40)
        self.assertEqual(sum(1 for row in rows if not row["block"] and row["family"] == "PRODUCT"), 30)

    def test_pass_contract_exact_180_150_30_counts(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], EXPECTED)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])

    def test_all_valid_route_to_exact_facility_revision_sequence(self) -> None:
        result = gate.run_gate()
        valid = [item for item in result["intakes"] if not item["block"]]
        self.assertEqual(len(valid), 150)
        self.assertEqual(result["counts"]["routed_exact"], 150)
        for item in valid:
            method = gate.METHODS[item["method_id"]]
            self.assertEqual(item["facility"], item["requested_facility"])
            self.assertIn(item["facility"], method["sites"])
            self.assertEqual(item["method_revision"], method["revision"])
            self.assertEqual(item["sequence"], list(method["sequence"]))
            self.assertEqual(item["state"], "RELEASED")

    def test_all_30_block_with_expected_reason(self) -> None:
        result = gate.run_gate()
        blocked = [item for item in result["intakes"] if item["block"]]
        self.assertEqual(len(blocked), 30)
        self.assertEqual(result["block_reasons"], gate.load_fixture()["block_reason_counts"])
        self.assertEqual(
            {item["block_reason"] for item in blocked},
            set(gate.load_fixture()["block_reason_counts"]),
        )
        self.assertTrue(all(item["state"] == "BLOCKED" for item in blocked))
        self.assertTrue(all(not item["released"] for item in blocked))
        self.assertTrue(all(hold["expected"] for hold in result["blocks"]))

    def test_custody_complete_on_valid_orders_only(self) -> None:
        result = gate.run_gate()
        valid = [item for item in result["intakes"] if not item["block"]]
        blocked = [item for item in result["intakes"] if item["block"]]
        self.assertTrue(all(item["custody_complete"] for item in valid))
        self.assertTrue(all(len(item["custody"]) == 5 for item in valid))
        self.assertTrue(all({link["role"] for link in item["custody"]} == set(gate.CUSTODY_ROLES) for item in valid))
        incomplete = [item for item in blocked if item["block_reason"] == "INCOMPLETE_CUSTODY"]
        self.assertEqual(len(incomplete), 5)
        self.assertTrue(all(len(item["custody"]) == 1 for item in incomplete))
        self.assertEqual(result["counts"]["custody_complete"], 150)

    def test_sla_24h_dock_to_start_and_48h_report_are_exact(self) -> None:
        result = gate.run_gate()
        spec = gate.load_fixture()
        valid = [item for item in result["intakes"] if not item["block"]]
        self.assertEqual(result["counts"]["dock_to_start_exact"], 150)
        self.assertEqual(result["counts"]["report_sla_exact"], 150)
        for item in valid:
            start, report = gate.sla_times(
                item["dock_at"],
                spec["dock_to_start_hours"],
                spec["start_to_report_hours"],
            )
            self.assertEqual(item["start_at"], start)
            self.assertEqual(item["report_at"], report)
            self.assertEqual(item["start_at"], gate._add_hours(item["dock_at"], 24))
            self.assertEqual(item["report_at"], gate._add_hours(item["start_at"], 48))

    def test_retries_idempotent_replay_changes_nothing(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(len(first["audit_sha256"]), 64)
        self.assertEqual(gate.sha256_hex(first["audit"]), first["audit_sha256"])
        self.assertEqual(first["counts"]["replay_changed_records"], 0)
        self.assertEqual(first["replay"]["changed_records"], 0)
        self.assertEqual(first["replay"]["replay_noops"], 180)
        fixture = gate.load_fixture()
        golden = fixture.get("golden_audit_sha256")
        if golden and golden != "PIN_AFTER_FIRST_RUN":
            self.assertEqual(first["audit_sha256"], golden)

    def test_no_release_before_human_approval(self) -> None:
        result = gate.run_gate()
        self.assertTrue(
            all(item["code"] == "RELEASE_BLOCKED_AUTONOMOUS" for item in result["autonomous_release_effects"])
        )
        self.assertEqual(result["counts"]["released_without_named_qa"], 0)
        self.assertFalse(result["automatic_release"])
        self.assertEqual(sum(1 for item in result["named_qa_release_effects"] if item.get("ok")), 150)
        blocked = [item for item in result["named_qa_release_effects"] if not item.get("ok")]
        self.assertEqual(len(blocked), 30)
        self.assertTrue(all(item["code"] == "RELEASE_BLOCKED_OPEN_HOLD" for item in blocked))
        self.assertEqual(result["counts"]["released_after_named_qa"], 150)
        self.assertEqual(result["counts"]["blocked_released"], 0)

    def test_named_qa_cannot_release_before_import_or_on_block(self) -> None:
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        clean = next(item for item in rows if not item["block"])
        held = next(item for item in rows if item["block"])
        missing = gate.release_order(journal, clean["intake_id"], actor_role="NAMED_QA", actor="qa-named-pcl-1")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["code"], "UNKNOWN_ORDER")

        gate.import_rows(journal, [clean, held])
        autonomous = gate.release_order(journal, clean["intake_id"], actor_role="SYSTEM", actor="autonomous")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "RELEASE_BLOCKED_AUTONOMOUS")
        self.assertFalse(journal["intakes"][clean["intake_id"]]["released"])

        named = gate.release_order(journal, clean["intake_id"], actor_role="NAMED_QA", actor="qa-named-pcl-1")
        self.assertTrue(named["ok"])
        still = gate.release_order(journal, held["intake_id"], actor_role="NAMED_QA", actor="qa-named-pcl-1")
        self.assertFalse(still["ok"])
        self.assertEqual(still["code"], "RELEASE_BLOCKED_OPEN_HOLD")

    def test_no_live_adapters_or_production_writes(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["phi_records"], 0)
        self.assertEqual(result["billing_writes"], 0)
        self.assertEqual(result["delivery_writes"], 0)
        self.assertEqual(result["cash_usd"], 0)
        for name in gate.ADAPTERS:
            self.assertEqual(result["audit"]["adapters"][name], "SIMULATED_READONLY")
            self.assertEqual(len(result["adapters"][name]), 180)
            self.assertTrue(all(item["live"] is False and item["readonly"] is True for item in result["adapters"][name]))

    def test_working_program_is_intake_then_route_then_clocks_then_hold_release(self) -> None:
        journal = gate.empty_journal()
        row = next(item for item in gate.build_acceptance_fixture() if not item["block"])
        taken = gate.intake_order(journal, row)
        self.assertEqual(taken["kind"], "INTAKEN")
        self.assertEqual(journal["intakes"][row["intake_id"]]["state"], "INTAKEN")
        too_soon = gate.release_order(journal, row["intake_id"], actor_role="NAMED_QA", actor="qa-named-pcl-1")
        self.assertFalse(too_soon["ok"])
        self.assertEqual(too_soon["code"], "RELEASE_BLOCKED_SEQUENCE_OPEN")
        self.assertFalse(gate.route_order(journal, row["intake_id"]).get("ok") is False)
        self.assertEqual(journal["intakes"][row["intake_id"]]["state"], "ROUTED")
        clocks = gate.set_sla_clocks(journal, row["intake_id"])
        self.assertTrue(clocks["ok"])
        self.assertEqual(clocks["start_at"], row["expected_start_at"])
        self.assertEqual(clocks["report_at"], row["expected_report_at"])
        done = gate.run_sequence(journal, row["intake_id"])
        self.assertEqual(done["kind"], "SEQUENCE_DONE")
        self.assertEqual(journal["intakes"][row["intake_id"]]["state"], "READY_FOR_NAMED_QA")
        self.assertEqual(journal["intakes"][row["intake_id"]]["sequence_log"], row["sequence"])
        autonomous = gate.release_order(journal, row["intake_id"], actor_role="SYSTEM", actor="autonomous")
        self.assertEqual(autonomous["code"], "RELEASE_BLOCKED_AUTONOMOUS")
        named = gate.release_order(journal, row["intake_id"], actor_role="NAMED_QA", actor="qa-named-pcl-1")
        self.assertTrue(named["ok"])
        self.assertEqual(journal["intakes"][row["intake_id"]]["state"], "RELEASED")

    def test_official_command_writes_working_state_and_receipts(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(gate.PACK / "runner.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["failures"], [])
        self.assertEqual(payload["actual"]["orders"], 180)
        self.assertEqual(payload["actual"]["valid"], 150)
        self.assertEqual(payload["actual"]["blocked"], 30)
        self.assertEqual(payload["working_program"], "intake → route → SLA clocks → HOLD/release")
        for path in (
            gate.STATE_PATH,
            gate.RUN_RECEIPT_PATH,
            gate.ORDER_RECEIPT_PATH,
            gate.BLOCK_RECEIPT_PATH,
            gate.CLOCK_RECEIPT_PATH,
            gate.AUDIT_RECEIPT_PATH,
            gate.REPLAY_RECEIPT_PATH,
            gate.CONTRACT_PATH,
        ):
            self.assertTrue(path.is_file(), path)
        journal = json.loads(gate.STATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(journal["intakes"]), 180)
        self.assertEqual(len(journal["orders"]), 150)
        self.assertEqual(len(journal["blocks"]), 30)
        orders = json.loads(gate.ORDER_RECEIPT_PATH.read_text(encoding="utf-8"))
        blocks = json.loads(gate.BLOCK_RECEIPT_PATH.read_text(encoding="utf-8"))
        clocks = json.loads(gate.CLOCK_RECEIPT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(orders), 150)
        self.assertEqual(len(blocks), 30)
        self.assertEqual(len(clocks), 150)
        replay = subprocess.run(
            [sys.executable, str(gate.PACK / "runner.py"), "--replay"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(replay.returncode, 0, replay.stderr or replay.stdout)
        replay_body = json.loads(replay.stdout)
        self.assertTrue(replay_body["ok"])
        self.assertEqual(replay_body["replay"]["changed_records"], 0)
        self.assertEqual(replay_body["replay"]["replay_noops"], 180)


if __name__ == "__main__":
    unittest.main()
