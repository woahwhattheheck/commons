#!/usr/bin/env python3
"""Shared-equipment composition of the C1 headless Claude runner, hermetic against stub_claude.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STUB = ROOT / "integrations" / "claude_headless" / "stub_claude.py"
STUB_ARGV = [sys.executable, str(STUB)]
TOOL_NAMES = (
    "claude_headless_start",
    "claude_headless_status",
    "claude_headless_followup",
    "claude_headless_cancel",
    "claude_headless_events",
    "claude_headless_recover",
)


class ClaudeHeadlessEquipmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        base = Path(self.tmp.name)
        (base / "state").mkdir()
        self._old_state = os.environ.get("STUB_CLAUDE_STATE")
        os.environ["STUB_CLAUDE_STATE"] = str(base / "state")
        from integrations.shared_equipment.peers import ClaudeHeadlessEquipment

        self.equipment = ClaudeHeadlessEquipment(str(base / "root"), claude=STUB_ARGV, min_free_mb=0)

    def tearDown(self) -> None:
        for record in self.equipment.runner.list_runs(limit=100):
            if record["status"] in ("queued", "running"):
                self.equipment.runner.cancel(record["run_id"])
        if self._old_state is None:
            os.environ.pop("STUB_CLAUDE_STATE", None)
        else:
            os.environ["STUB_CLAUDE_STATE"] = self._old_state
        self.tmp.cleanup()

    def test_catalog_lists_the_six_tools_with_schemas(self) -> None:
        tools = {t["name"]: t for t in self.equipment.tools()}
        self.assertEqual(set(tools), set(TOOL_NAMES))
        self.assertIn("prompt", json.dumps(tools["claude_headless_start"]))
        self.assertIn("allowed_tools", json.dumps(tools["claude_headless_start"]))
        from integrations.shared_equipment.services import build_cli_catalog

        names = {t["name"] for t in build_cli_catalog().tools()}
        for name in TOOL_NAMES + ("grokbot_submit", "github_read_file"):
            self.assertIn(name, names)

    def test_start_followup_events_cancel_recover_round_trip(self) -> None:
        started = self.equipment.call("claude_headless_start", {"prompt": "first question", "label": "eq", "peer": "TEST", "wait_s": 20})
        self.assertTrue(started["ok"], started)
        self.assertEqual(started["status"], "completed")
        self.assertIn("first question", started["result_text"])
        self.assertEqual(started["label"], "eq")
        followed = self.equipment.call("claude_headless_followup", {"target": started["run_id"], "prompt": "second question", "wait_s": 20})
        self.assertEqual(followed["session_id"], started["session_id"])
        self.assertNotEqual(followed["run_id"], started["run_id"])
        self.assertIn('"first question"', followed["result_text"])
        status = self.equipment.call("claude_headless_status", {"run_id": followed["run_id"]})
        self.assertEqual(status["status"], "completed")
        events = self.equipment.call("claude_headless_events", {"run_id": started["run_id"], "after": 0, "limit": 1})
        self.assertEqual(events["events"][0]["event"]["type"], "system")
        self.assertEqual(events["next_cursor"], 1)
        slow = self.equipment.call("claude_headless_start", {"prompt": "SLOW work"})
        self.assertEqual(slow["status"], "running")
        cancelled = self.equipment.call("claude_headless_cancel", {"run_id": slow["run_id"]})
        self.assertTrue(cancelled["ok"], cancelled)
        self.assertEqual(cancelled["status"], "cancelled")
        recovered = self.equipment.call("claude_headless_recover", {})
        self.assertTrue(recovered["ok"])
        self.assertEqual(recovered["still_running"], [])
        self.assertIn("free_physical_mb", recovered["memory_floor"])

    def test_memory_floor_refusal_is_a_tool_result_not_a_spawn(self) -> None:
        import claude_headless as ch  # importable once the equipment loaded the runner

        original = ch.free_physical_mb
        try:
            ch.free_physical_mb = lambda: 100
            from integrations.shared_equipment.peers import ClaudeHeadlessEquipment

            starved = ClaudeHeadlessEquipment(str(Path(self.tmp.name) / "starved"), claude=STUB_ARGV, min_free_mb=1024)
            result = starved.call("claude_headless_start", {"prompt": "should not spawn"})
            self.assertEqual(result["ok"], False)
            self.assertEqual(result["error"], "claude_headless_refused")
            self.assertIn("free physical RAM 100 MB", result["message"])
            self.assertEqual(starved.runner.list_runs(), [])
            self.assertTrue(starved.call("claude_headless_recover", {})["memory_floor"]["holds"])
        finally:
            ch.free_physical_mb = original

    def test_bad_arguments_are_reported(self) -> None:
        missing = self.equipment.call("claude_headless_start", {})
        self.assertEqual(missing["error"], "missing_argument")
        unknown = self.equipment.call("claude_headless_status", {"run_id": "nope"})
        self.assertEqual(unknown["error"], "claude_headless_refused")
        self.assertEqual(self.equipment.call("no_such_tool", {})["error"], "unknown_equipment_tool")

    def test_module_catalog_subprocess_includes_claude_headless(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT)
        proc = subprocess.run(
            [sys.executable, "-m", "integrations.shared_equipment.services", "catalog"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        names = {t["name"] for t in json.loads(proc.stdout)["tools"]}
        for name in TOOL_NAMES:
            self.assertIn(name, names)


if __name__ == "__main__":
    unittest.main()
