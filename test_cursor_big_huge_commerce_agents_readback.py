#!/usr/bin/env python3
"""Pin unique-pack readback of remainder fddb5a7c. Do not remint remainder."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-big-huge-commerce-agents-readback-20260902-01.md"
REMAINDER = ROOT / "p/cursor-big-huge-commerce-agents-20260902-01.md"
HELPER = ROOT / "host/commerce_agents_same_loop.py"

KEEP = {
    "p/cursor-big-huge-commerce-agents-20260902-01.md": "fddb5a7c",
    "host/commerce_agents_same_loop.py": "c90f6e50",
    "test_commerce_agents_same_loop.py": "623e99e8",
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "host/commerce_agents.py": "8d2ddf29",
    "ground/COMMERCE_AGENTS.json": "ab6f56a8",
    "commerce-agents.html": "e2028ddc",
    ".agents/skills/commerce-agents/SKILL.md": "1f93c4a2",
    "test_commerce_agents.py": "78a158b3",
    "p/cursor-claude-commerce-agents-readback-20260902-01.md": "0153924f",
    "p/cursor-harborline-commerce-compose-readback-20260902-01.md": "b33e2e24",
    "p/cursor-harborline-commerce-compose-20260902-01.md": "45b7d435",
    "host/harborline_commerce_compose.py": "75128e5d",
    "p/cursor-harborline-commerce-compose-keep-lift-20260902-01.md": "668dd5c4",
    "p/cursor-explee-skills-adopt-20260902-01.md": "20db155c",
    "autogtm.html": "9d8b3e85",
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


class TestCursorBigHugeCommerceAgentsReadback(unittest.TestCase):
    def test_keep_remainder_and_leftover_unique_pack(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        self.assertNotIn("boards.html", KEEP)
        self.assertNotIn("index.html", KEEP)
        self.assertNotIn("hub_pages.py", KEEP)
        self.assertNotIn("door.js", KEEP)

    def test_remainder_json_stays_staged_host_handoff(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["id"], "cursor-big-huge-commerce-agents-20260902-01")
        self.assertFalse(packet["copied_tree"])
        self.assertEqual(packet["checkout"]["state"], "STAGED_HOST_HANDOFF")
        self.assertEqual(packet["checkout"]["host_door"], "payment-capability.html")
        self.assertFalse(packet["checkout"]["model_sees_url"])
        self.assertFalse(packet["checkout"]["invented_url"])
        self.assertEqual(packet["sends"], 0)
        self.assertFalse(packet["charged"])
        self.assertEqual(packet["cash_usd"], 0)
        self.assertEqual(packet["leftover"]["verdict"], "RENDER")
        self.assertTrue(packet["leftover"]["pin"].startswith("fd4d59224"))
        self.assertNotIn("buy.stripe.com", proc.stdout)

    def test_remainder_send_go_charge_live_refused(self) -> None:
        for flag in ("--send", "--go", "--charge", "--live", "--claude-plugin"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["flag"], flag)
            self.assertEqual(payload["verdict"], "REFUSED")
            self.assertFalse(payload["invented_url"])

    def test_remainder_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_commerce_agents_same_loop.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 12 tests", proc.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = REMAINDER.read_text(encoding="utf-8")
        self.assertIn("cursor-big-huge-commerce-agents-readback-20260902-01", text)
        self.assertIn("52b6ade27", text)
        self.assertIn("955d166fe", text)
        self.assertIn("fddb5a7c", text)
        self.assertIn("c90f6e50", text)
        self.assertIn("623e99e8", text)
        self.assertIn("0153924f", text)
        self.assertIn("Did **not** remint remainder helper", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
