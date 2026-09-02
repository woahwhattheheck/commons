#!/usr/bin/env python3
"""Pin unique-pack readback of Claude Commerce Agents leftover. Do not remint leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-claude-commerce-agents-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-claude-commerce-agents-20260902-01.md"
HELPER = ROOT / "host/commerce_agents.py"
DOOR = ROOT / "commerce-agents.html"

KEEP = {
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "host/commerce_agents.py": "8d2ddf29",
    "ground/COMMERCE_AGENTS.json": "ab6f56a8",
    "commerce-agents.html": "e2028ddc",
    ".agents/skills/commerce-agents/SKILL.md": "1f93c4a2",
    "test_commerce_agents.py": "78a158b3",
    "p/cursor-explee-skills-adopt-20260902-01.md": "20db155c",
    ".agents/skills/autogtm/SKILL.md": "1c5b3e0c",
    "autogtm.html": "9d8b3e85",
    "p/cursor-big-huge-commerce-agents-20260902-01.md": "fddb5a7c",
    "host/commerce_agents_same_loop.py": "c90f6e50",
    "test_commerce_agents_same_loop.py": "623e99e8",
    "p/cursor-harborline-commerce-compose-20260902-01.md": "45b7d435",
    "host/harborline_commerce_compose.py": "75128e5d",
    "p/cursor-harborline-commerce-compose-keep-lift-20260902-01.md": "668dd5c4",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "p/cursor-what-a-pack-is-20260902-01.md": "a4e4dd89",
    "p/cursor-pack-is-ready-to-run-20260902-01.md": "897b00ba",
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "ground/OWNER_NOW.md": "59b1fd37",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def run_helper(*flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(HELPER), *flags],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class TestCursorClaudeCommerceAgentsReadback(unittest.TestCase):
    def test_keep_leftover_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_json_still_renders_without_inventing_checkout(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertEqual(packet["repo"], "anthropics/commerce-agents")
        self.assertTrue(packet["pin"].startswith("fd4d59224"))
        self.assertTrue(packet["shopping_agent"])
        self.assertTrue(packet["merchant_agent"])
        self.assertEqual(
            packet["verticals"],
            ["retail", "travel", "telecom", "entertainment"],
        )
        self.assertTrue(packet["checkout_hands_off"])
        self.assertEqual(packet["checkout"], "FINDER-FAILED")
        self.assertFalse(packet["copy_blueprint_source"])
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertFalse(packet["commons_is_store"])
        self.assertFalse(packet["remint_autogtm"])
        self.assertEqual(packet["anthropic_api_key"], "FINDER-FAILED")
        self.assertEqual(packet["sends"], 0)
        self.assertNotIn("buy.stripe.com", proc.stdout)

    def test_leftover_send_go_live_checkout_refused(self) -> None:
        for flag in ("--send", "--go", "--live", "--checkout"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["refused"], flag)

    def test_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_commerce_agents.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 5 tests", proc.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn("cursor-claude-commerce-agents-readback-20260902-01", text)
        self.assertIn("64a7e12d7", text)
        self.assertIn("3e48f691", text)
        self.assertIn("8d2ddf29", text)
        self.assertIn("ab6f56a8", text)
        self.assertIn("e2028ddc", text)
        self.assertIn("1f93c4a2", text)
        self.assertIn("78a158b3", text)
        self.assertIn("Did **not** remint leftover id", text)
        self.assertIn("Did **not** unique-pack this seat remainder", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("No login", door)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertFalse(
            (ROOT / "p/cursor-big-huge-commerce-agents-readback-20260902-01.md").exists()
        )


if __name__ == "__main__":
    unittest.main()
