#!/usr/bin/env python3
"""Pin independent ACK of leftover unique-pack LEAD + Harborline readbacks."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACK = ROOT / "p/cursor-claude-commerce-agents-readback-ack-20260902-01.md"
LEAD_UNIQUE = ROOT / "p/cursor-claude-commerce-agents-readback-20260902-01.md"
HARBOR_UNIQUE = ROOT / "p/cursor-harborline-commerce-compose-readback-20260902-01.md"
LEAD_HELPER = ROOT / "host/commerce_agents.py"
HARBOR_HELPER = ROOT / "host/harborline_commerce_compose.py"

KEEP = {
    "p/cursor-claude-commerce-agents-readback-20260902-01.md": "0153924f",
    "p/cursor-harborline-commerce-compose-readback-20260902-01.md": "b33e2e24",
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "host/commerce_agents.py": "8d2ddf29",
    "ground/COMMERCE_AGENTS.json": "ab6f56a8",
    "commerce-agents.html": "e2028ddc",
    ".agents/skills/commerce-agents/SKILL.md": "1f93c4a2",
    "test_commerce_agents.py": "78a158b3",
    "p/cursor-harborline-commerce-compose-20260902-01.md": "45b7d435",
    "host/harborline_commerce_compose.py": "75128e5d",
    "p/cursor-harborline-commerce-compose-keep-lift-20260902-01.md": "668dd5c4",
    "p/cursor-big-huge-commerce-agents-20260902-01.md": "fddb5a7c",
    "host/commerce_agents_same_loop.py": "c90f6e50",
    "test_commerce_agents_same_loop.py": "623e99e8",
    "p/cursor-explee-skills-adopt-20260902-01.md": "20db155c",
    ".agents/skills/autogtm/SKILL.md": "1c5b3e0c",
    "autogtm.html": "9d8b3e85",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def run_helper(helper: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(helper), *flags],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class TestCursorClaudeCommerceAgentsReadbackAck(unittest.TestCase):
    def test_keep_leftover_unique_pack_and_rails(self) -> None:
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
        self.assertNotIn("test_cursor_claude_commerce_agents_readback.py", KEEP)
        self.assertNotIn("test_cursor_harborline_commerce_compose_readback.py", KEEP)

    def test_leftover_helpers_still_refuse_send(self) -> None:
        lead = run_helper(LEAD_HELPER, "--json")
        self.assertEqual(lead.returncode, 0, msg=lead.stdout + lead.stderr)
        packet = json.loads(lead.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertEqual(packet["sends"], 0)
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["checkout"], "FINDER-FAILED")
        harbor = run_helper(HARBOR_HELPER, "--json")
        self.assertEqual(harbor.returncode, 0, msg=harbor.stdout + harbor.stderr)
        cart = json.loads(harbor.stdout)
        self.assertEqual(cart["cart"]["lines"][0]["product_id"], "harborline-local-sites")
        self.assertEqual(cart["sent"], 0)
        self.assertEqual(
            cart["checkout"]["host_only"]["checkout_handoff"]["state"],
            "FINDER-FAILED",
        )
        for helper, flags in (
            (LEAD_HELPER, ("--send", "--go", "--live", "--checkout")),
            (HARBOR_HELPER, ("--send", "--go", "--live", "--dump-commons")),
        ):
            for flag in flags:
                proc = run_helper(helper, flag)
                self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
                payload = json.loads(proc.stdout)
                self.assertEqual(payload["sent"], 0)
                self.assertEqual(payload["refused"], flag)

    def test_ack_cites_unique_pack_without_reminting(self) -> None:
        text = ACK.read_text(encoding="utf-8")
        lead = LEAD_UNIQUE.read_text(encoding="utf-8")
        harbor = HARBOR_UNIQUE.read_text(encoding="utf-8")
        self.assertIn("cursor-claude-commerce-agents-readback-ack-20260902-01", text)
        self.assertIn("cursor-claude-commerce-agents-readback-20260902-01", text)
        self.assertIn("cursor-harborline-commerce-compose-readback-20260902-01", text)
        self.assertIn("52b6ade27", text)
        self.assertIn("0153924f", text)
        self.assertIn("b33e2e24", text)
        self.assertIn("1788389835.157849", text)
        self.assertIn("fddb5a7c", text)
        self.assertIn("668dd5c4", text)
        self.assertIn("bc-c3d679bb", text)
        self.assertIn("Did **not** remint leftover unique-pack ids", text)
        self.assertNotEqual(text, lead)
        self.assertNotEqual(text, harbor)
        self.assertNotEqual(
            git_blob("p/cursor-claude-commerce-agents-readback-ack-20260902-01.md"),
            git_blob("p/cursor-claude-commerce-agents-readback-20260902-01.md"),
        )
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertTrue(
            (ROOT / "p/cursor-big-huge-commerce-agents-readback-20260902-01.md").exists()
        )
        self.assertTrue(
            (
                ROOT
                / "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md"
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
