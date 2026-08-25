#!/usr/bin/env python3
"""Mechanical proof that current Commons cannot auto-wake Cursor."""
from __future__ import annotations

import os
import json
import unittest

from harness_wake.cursor_adapter import claimed_paths, is_cursor_harness
from wakeup import is_held_cursor, ntfy


ROOT = os.path.dirname(os.path.abspath(__file__))


class CursorQuotaHoldTests(unittest.TestCase):
    def test_boot_rule_is_always_applied(self):
        path = os.path.join(ROOT, ".cursor", "rules", "cursor-quota-hold.mdc")
        with open(path, encoding="utf-8") as handle:
            text = handle.read().lower()
        self.assertIn("alwaysapply: true", text)
        self.assertIn("stop", text)
        self.assertIn("supergrok heavy", text)
        card = os.path.join(ROOT, "ground", "CURSOR_QUOTA_HOLD.json")
        with open(card, encoding="utf-8") as handle:
            catalog = handle.read().lower()
        self.assertIn('"cursor_enabled": false', catalog)
        self.assertIn('"cursor_callback_invoke_model": false', catalog)

    def test_issue_reassignment_doorbell_is_absent(self):
        path = os.path.join(ROOT, ".github", "workflows", "harness-ping.yml")
        with open(path, encoding="utf-8") as handle:
            text = handle.read().lower()
        self.assertNotIn("--add-assignee", text)
        self.assertNotIn("--remove-assignee", text)
        self.assertNotIn("issues: write", text)

    def test_cursor_harnesses_are_held(self):
        self.assertTrue(is_cursor_harness("cursor-slack"))
        self.assertTrue(is_cursor_harness("Cursor Grok 4.6"))
        self.assertTrue(is_cursor_harness("Grok Bot / latch"))
        self.assertFalse(is_cursor_harness("supergrok-heavy/grok-build"))
        paths = claimed_paths()
        self.assertTrue(paths["cursor_quota_hold"])
        self.assertFalse(paths["claimed"]["slack_cursor_app"]["enabled"])
        self.assertFalse(paths["claimed"]["subscribe_timer"]["enabled"])
        self.assertFalse(paths["claimed"]["issue_1316"]["enabled"])
        self.assertFalse(paths["claimed"]["ntfy_poll"]["enabled"])

    def test_universal_wakeup_holds_cursor_rows(self):
        held = {"WIRE"}
        self.assertTrue(is_held_cursor({"from": "WIRE", "adapter": ""}, held))
        self.assertTrue(
            is_held_cursor({"from": "OTHER", "adapter": "grok-bot / other"}, held)
        )
        self.assertFalse(
            is_held_cursor(
                {"from": "GROK", "adapter": "SuperGrok Heavy / Grok Build"},
                held,
            )
        )
        calls = []

        def fail_if_called(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("network must not be called")

        import wakeup

        original = wakeup.urllib.request.urlopen
        wakeup.urllib.request.urlopen = fail_if_called
        try:
            self.assertFalse(
                ntfy(
                    {
                        "from": "WIRE",
                        "adapter": "grok-bot / wire",
                        "id": "wire-wakeup-test",
                        "wakeup": "2026-08-25T00:00:00Z",
                    },
                    "attempt-held",
                )
            )
        finally:
            wakeup.urllib.request.urlopen = original
        self.assertEqual(calls, [])
        workflow = os.path.join(
            ROOT, ".github", "workflows", "harness-wakeup.yml"
        )
        with open(workflow, encoding="utf-8") as handle:
            text = handle.read().lower()
        self.assertIn("cursor rows are held", text)
        self.assertNotIn("cursor issue-assign stays", text)

    def test_public_registries_do_not_advertise_cursor_wake(self):
        with open(os.path.join(ROOT, "wake.json"), encoding="utf-8") as handle:
            wake = json.load(handle)
        self.assertTrue(wake.get("held_cursor"))
        for row in wake.get("actionable") or []:
            self.assertFalse(is_cursor_harness(str(row.get("adapter") or "")))
        with open(
            os.path.join(ROOT, "ping", "last.json"), encoding="utf-8"
        ) as handle:
            last = json.load(handle)
        self.assertEqual(last.get("moved"), [])
        self.assertIn("LATCH", last.get("held_cursor") or [])
        self.assertNotIn("doorbell is issue 1316", last.get("instruction", "").lower())

    def test_manual_does_not_publish_cursor_jobs_as_open(self):
        with open(os.path.join(ROOT, "ground", "MANUAL.md"), encoding="utf-8") as handle:
            manual = handle.read()
        self.assertNotIn("OPEN CURSOR_GROK", manual)
        self.assertIn("HELD_CURSOR CURSOR_GROK", manual)

    def test_active_route_cards_name_the_hold(self):
        for rel in (
            "ground/SLACK.md",
            "ground/wake-harness-survey.md",
            "ground/wake-universal-all-harness.md",
            "ground/wake-slack.md",
        ):
            with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
                text = handle.read().lower()
            self.assertIn("cursor_quota_hold", text, rel)


if __name__ == "__main__":
    unittest.main()
