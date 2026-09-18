#!/usr/bin/env python3
"""Binary acceptance for aquatrace-work-order-b-production-foundation-20260831-01.

Fail-closed. The runner is the product. HTML is not the proof.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import aquatrace_work_order_b_production_foundation as door

runner = door.MODULE
ROOT = Path(__file__).resolve().parent
GOLDEN = "669cf3ea966ee6351ffad46bbc0e2ce6854a10ce290bd6faf380b57910f3ec23"


class AquaTraceWorkOrderBProductionFoundationTests(unittest.TestCase):
    def test_pass_contract_exact_counts_and_locked_digest(self) -> None:
        result = runner.run_gate()
        self.assertEqual(runner.pass_contract(result), [])
        counts = runner.expected_actual(result)
        self.assertEqual(counts["expected"], runner.load_fixture()["expected"])
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(len(result["audit_sha256"]), 64)
        self.assertEqual(result["audit_sha256"], GOLDEN)
        self.assertEqual(result["audit_sha256"], runner.golden_audit_sha256())
        self.assertEqual(runner.sha256_hex(result["audit"]), result["audit_sha256"])
        self.assertEqual(result["program_state"], "NOT_READY")
        self.assertFalse(result["readiness_claim"])
        self.assertFalse(result["automatic_release"])

    def test_unknown_and_disabled_actors_refused(self) -> None:
        result = runner.run_gate()
        self.assertEqual(result["counts"]["unknown_actor_refusals"], 1)
        self.assertEqual(result["counts"]["disabled_actor_refusals"], 1)
        codes = {item["code"] for item in result["probes"]}
        self.assertIn("UNKNOWN_ACTOR", codes)
        self.assertIn("ACTOR_DISABLED", codes)
        journal = runner.empty_journal()
        unknown = runner.act(journal, actor_id="not-in-roster", action="INTAKE", sample_id="SYN-ATB-S99")
        self.assertFalse(unknown["ok"])
        self.assertEqual(unknown["code"], "UNKNOWN_ACTOR")
        disabled = runner.act(journal, actor_id="disabled-analyst-1", action="RECORD_RESULT", sample_id="SYN-ATB-S01")
        self.assertFalse(disabled["ok"])
        self.assertEqual(disabled["code"], "ACTOR_DISABLED")

    def test_deny_by_default_rbac_keeps_each_role_in_named_scope(self) -> None:
        journal = runner.empty_journal()
        plan = runner.load_fixture()["samples"][0]
        runner.act(journal, actor_id="collector-1", action="INTAKE", sample_id=plan["sample_id"], payload=runner._intake_payload(plan))
        collector_release = runner.act(journal, actor_id="collector-1", action="RELEASE_PACKET", sample_id=plan["sample_id"])
        self.assertFalse(collector_release["ok"])
        self.assertEqual(collector_release["code"], "RBAC_DENIED")
        analyst_admin = runner.act(journal, actor_id="analyst-1", action="ADMIN_USER")
        self.assertFalse(analyst_admin["ok"])
        self.assertEqual(analyst_admin["code"], "RBAC_DENIED")
        reporting_collect = runner.act(journal, actor_id="reporting-1", action="CUSTODY_COLLECT", sample_id=plan["sample_id"])
        self.assertFalse(reporting_collect["ok"])
        self.assertEqual(reporting_collect["code"], "RBAC_DENIED")
        qa_result = runner.act(journal, actor_id="qa-1", action="RECORD_RESULT", sample_id=plan["sample_id"])
        self.assertFalse(qa_result["ok"])
        self.assertEqual(qa_result["code"], "RBAC_DENIED")

    def test_same_actor_cannot_approve_own_proposal(self) -> None:
        result = runner.run_gate()
        self.assertEqual(result["counts"]["self_approve_refusals"], 1)
        events = [
            item
            for item in result["first_pass_events"]
            if item["code"] == "SELF_APPROVE" and item["actor_id"] == "analyst-1"
        ]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["action"], "APPROVE_QC")
        self.assertEqual(events[0]["sample_id"], "SYN-ATB-S01")
        approved = next(item for item in result["samples"] if item["sample_id"] == "SYN-ATB-S01")
        self.assertEqual(approved["qc_proposed_by"], "analyst-1")
        self.assertEqual(approved["qc_approved_by"], "qa-1")
        self.assertNotEqual(approved["qc_proposed_by"], approved["qc_approved_by"])

    def test_support_is_time_bounded_and_cannot_elevate(self) -> None:
        result = runner.run_gate()
        self.assertEqual(result["counts"]["support_window_refusals"], 1)
        self.assertEqual(result["counts"]["support_elevate_refusals"], 1)
        self.assertEqual(result["counts"]["support_reads_allowed"], 1)
        journal = runner.empty_journal()
        expired = runner.act(journal, actor_id="support-expired-1", action="SUPPORT_READ")
        self.assertFalse(expired["ok"])
        self.assertEqual(expired["code"], "SUPPORT_WINDOW_CLOSED")
        elevate = runner.act(journal, actor_id="support-1", action="ELEVATE")
        self.assertFalse(elevate["ok"])
        self.assertEqual(elevate["code"], "SUPPORT_NO_ELEVATE")
        allowed = runner.act(journal, actor_id="support-1", action="SUPPORT_READ")
        self.assertTrue(allowed["ok"])
        self.assertEqual(allowed["code"], "SUPPORT_READ")

    def test_integration_cannot_admin_and_qa_cannot_erase_audit(self) -> None:
        result = runner.run_gate()
        self.assertEqual(result["counts"]["integration_admin_refusals"], 1)
        self.assertEqual(result["counts"]["qa_erase_refusals"], 1)
        before = len(result["first_pass_events"])
        journal = runner.empty_journal()
        admin = runner.act(journal, actor_id="integration-1", action="ADMIN_USER")
        erase = runner.act(journal, actor_id="qa-1", action="ERASE_AUDIT")
        self.assertFalse(admin["ok"])
        self.assertEqual(admin["code"], "INTEGRATION_NO_ADMIN")
        self.assertFalse(erase["ok"])
        self.assertEqual(erase["code"], "QA_NO_ERASE_AUDIT")
        self.assertEqual(len(journal["audit"]), 2)
        self.assertGreaterEqual(before, 1)

    def test_reporting_releases_only_reconciled_approved_packets(self) -> None:
        result = runner.run_gate()
        self.assertEqual(result["counts"]["unreconciled_release_refusals"], 1)
        self.assertEqual(result["counts"]["qc_hold_release_refusals"], 1)
        self.assertEqual(result["counts"]["released_after_named_human"], 4)
        self.assertEqual(result["counts"]["released_without_named_human"], 0)
        released = [item for item in result["samples"] if item["released"]]
        self.assertEqual(len(released), 4)
        for item in released:
            self.assertTrue(item["reconciled"])
            self.assertEqual(item["qc_state"], "APPROVED")
            self.assertEqual(item["released_by"], "reporting-1")
            self.assertNotEqual(item["qc_proposed_by"], item["released_by"])
            self.assertTrue(item["custody_complete"])
            self.assertTrue(item["device_known"])
            self.assertIsNotNone(item["result_by"])
        held = next(item for item in result["samples"] if item["sample_id"] == "SYN-ATB-S05")
        self.assertEqual(held["hold_code"], "HOLD_QC")
        self.assertFalse(held["released"])

    def test_complete_custody_and_qc_hold_block_release(self) -> None:
        result = runner.run_gate()
        self.assertEqual(result["counts"]["complete_custody_chains"], 7)
        self.assertEqual(result["counts"]["incomplete_custody_holds"], 1)
        self.assertEqual(result["counts"]["qc_held"], 1)
        incomplete = next(item for item in result["samples"] if item["sample_id"] == "SYN-ATB-S07")
        self.assertFalse(incomplete["custody_complete"])
        self.assertEqual(incomplete["hold_code"], "HOLD_INCOMPLETE_CUSTODY")
        self.assertFalse(incomplete["released"])
        self.assertIsNone(incomplete["result"])

    def test_unknown_device_holds_and_cites_billings_fixtures_only(self) -> None:
        result = runner.run_gate()
        self.assertEqual(result["counts"]["unknown_device_holds"], 1)
        self.assertEqual(result["counts"]["known_device_handshakes"], 6)
        unknown = next(item for item in result["samples"] if item["sample_id"] == "SYN-ATB-S06")
        self.assertEqual(unknown["hold_code"], "HOLD_UNKNOWN_DEVICE")
        self.assertFalse(unknown["device_known"])
        self.assertFalse(unknown["released"])
        cites = {item["cites"] for item in result["devices"]}
        self.assertIn("mock-ph-meter-1 / SM 4500-H+ B", cites)
        self.assertIn("mock-metrohm-ic / EPA 300.0", cites)
        self.assertIn("mock-analytical-balance-1 / SM 2540 D", cites)
        for item in result["devices"]:
            self.assertEqual(len(item["export_hash"]), 64)
            self.assertTrue(item["known"])

    def test_no_result_without_named_human_and_autonomous_release_denied(self) -> None:
        result = runner.run_gate()
        self.assertEqual(result["counts"]["no_named_human_result_holds"], 1)
        self.assertEqual(result["counts"]["autonomous_release_refusals"], 8)
        self.assertTrue(all(not item["ok"] for item in result["autonomous_release_effects"]))
        self.assertTrue(all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"]))
        bare = next(item for item in result["samples"] if item["sample_id"] == "SYN-ATB-S08")
        self.assertIsNone(bare["result"])
        self.assertIsNone(bare["result_by"])
        self.assertFalse(bare["released"])

    def test_replay_produces_at_most_one_effect_and_stable_audit(self) -> None:
        first = runner.run_gate()
        second = runner.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["audit_sha256"], GOLDEN)
        self.assertEqual(first["replay"]["changed_records"], 0)
        self.assertEqual(first["replay"]["duplicate_effects"], 0)
        self.assertFalse(first["replay"]["state_changed"])
        self.assertGreater(first["replay"]["replay_noops"], 0)
        keys = [item["effect_key"] for item in first["first_pass_events"]]
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_refusal_and_privileged_act_is_attributable(self) -> None:
        result = runner.run_gate()
        events = result["first_pass_events"]
        self.assertGreaterEqual(len(events), 40)
        for event in events:
            self.assertIn(event["decision"], {"ALLOWED", "REFUSED"})
            self.assertTrue(event["actor_id"])
            self.assertTrue(event["action"])
            self.assertTrue(event["code"])
            self.assertTrue(event["effect_key"])
            self.assertEqual(event["program_state"], "NOT_READY")
        refusals = [item for item in events if item["decision"] == "REFUSED"]
        self.assertGreaterEqual(len(refusals), 18)
        self.assertTrue(all(item["actor_id"] for item in refusals))

    def test_official_command_exits_zero_and_prints_exact_counts(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "aquatrace_work_order_b_production_foundation.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["actual"]["samples"], 8)
        self.assertEqual(payload["actual"]["released_after_named_human"], 4)
        self.assertEqual(payload["actual"]["hold_samples"], 4)
        self.assertEqual(payload["actual"]["released_without_named_human"], 0)
        self.assertEqual(payload["actual"]["replay_changed_records"], 0)
        self.assertEqual(payload["audit_sha256"], GOLDEN)
        self.assertEqual(payload["program_state"], "NOT_READY")
        self.assertFalse(payload["readiness_claim"])


if __name__ == "__main__":
    unittest.main()
