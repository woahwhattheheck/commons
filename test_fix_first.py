#!/usr/bin/env python3
"""Regression coverage for the executable fix-first peer contract."""

from pathlib import Path
import unittest

import fix_first


ROOT = Path(__file__).resolve().parent


class FixFirstTest(unittest.TestCase):
    def test_fixed_requires_code_test_main_and_readback(self):
        packet = {
            "outcome": "fixed",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": "labelled issue becomes one durable record",
            "changed_paths": ["board_ingest.py"],
            "tests": ["python3 test_board_batch_drain.py"],
            "main_sha": "a" * 40,
            "readback_verified": True,
            "report_only_sessions": 0,
            "unconsumed_findings": 0,
        }
        self.assertEqual(fix_first.validate(packet)["state"], "FIXED")
        for key in ("changed_paths", "tests", "main_sha", "readback_verified"):
            broken = dict(packet)
            broken[key] = False if key == "readback_verified" else []
            with self.assertRaises(fix_first.PacketError, msg=key):
                fix_first.validate(broken)

    def test_open_door_is_not_a_defect_without_prior_closed_contract(self):
        packet = {
            "outcome": "not_bug",
            "observed_broken": True,
            "finding_kind": "closed_door",
            "prior_door_state": "open",
            "report_only_sessions": 0,
            "unconsumed_findings": 0,
        }
        self.assertEqual(fix_first.validate(packet)["state"], "NOT_BUG_OPEN_DOOR")
        packet["outcome"] = "external_blocker"
        with self.assertRaises(fix_first.PacketError):
            fix_first.validate(packet)

    def test_closed_door_can_be_a_real_measured_break(self):
        packet = {
            "outcome": "fixed",
            "observed_broken": True,
            "finding_kind": "closed_door",
            "prior_door_state": "closed",
            "expected_contract": "the exact door was already specified closed",
            "changed_paths": ["example.py"],
            "tests": ["python3 test_example.py"],
            "main_sha": "b" * 40,
            "readback_verified": True,
        }
        self.assertEqual(fix_first.validate(packet)["state"], "FIXED")

    def test_report_only_and_unconsumed_session_outputs_fail(self):
        base = {
            "outcome": "not_bug",
            "observed_broken": False,
        }
        for key in ("report_only_sessions", "unconsumed_findings"):
            packet = dict(base)
            packet[key] = 1
            with self.assertRaises(fix_first.PacketError, msg=key):
                fix_first.validate(packet)
        with self.assertRaises(fix_first.PacketError):
            fix_first.validate({"outcome": "report", "observed_broken": True})

    def test_external_blocker_requires_attempted_repair_and_exact_condition(self):
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "expected_contract": "existing contract",
            "repair_attempts": ["patched and tested the in-scope writer"],
            "blocker": "remote service rejected every non-force write",
        }
        self.assertEqual(fix_first.validate(packet)["state"], "EXTERNAL_BLOCKER")
        packet["repair_attempts"] = []
        with self.assertRaises(fix_first.PacketError):
            fix_first.validate(packet)

    def test_peer_instructions_invoke_the_executable_contract(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        skill = (ROOT / ".agents/skills/review-and-ship/SKILL.md").read_text(encoding="utf-8")
        for text in (agents, skill):
            self.assertIn("python3 fix_first.py", text)
            self.assertIn("report-only", text)
            self.assertIn("open Commons door", text)


if __name__ == "__main__":
    unittest.main()
