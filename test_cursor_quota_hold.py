#!/usr/bin/env python3
"""Mechanical proof that current Commons cannot auto-wake Cursor."""
from __future__ import annotations

import os
import unittest

from harness_wake.cursor_adapter import claimed_paths, is_cursor_harness


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


if __name__ == "__main__":
    unittest.main()
