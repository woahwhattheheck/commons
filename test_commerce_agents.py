#!/usr/bin/env python3
"""Pin Claude Commerce Agents leftover. Do not remint AutoGTM."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/commerce_agents.py"
RECEIPT = ROOT / "p/cursor-claude-commerce-agents-20260902-01.md"
CATALOG = ROOT / "ground/COMMERCE_AGENTS.json"
DOOR = ROOT / "commerce-agents.html"
SKILL = ROOT / ".agents/skills/commerce-agents/SKILL.md"

KEEP = {
    "p/cursor-explee-skills-adopt-20260902-01.md": "20db155c",
    ".agents/skills/autogtm/SKILL.md": "1c5b3e0c",
    "autogtm.html": "9d8b3e85",
    "p/cursor-pack-is-ready-to-run-20260902-01.md": "897b00ba",
    "p/cursor-what-a-pack-is-20260902-01.md": "a4e4dd89",
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
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


class TestCommerceAgents(unittest.TestCase):
    def test_keep_autogtm_and_pack_leftovers(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_catalog_pins_public_clone(self) -> None:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "cursor-claude-commerce-agents-20260902-01")
        self.assertEqual(data["source"]["repo"], "anthropics/commerce-agents")
        self.assertTrue(
            data["source"]["pin"].startswith("fd4d59224"),
        )
        self.assertFalse(data["source"]["copy_blueprint_source"])
        self.assertTrue(data["agents"]["shopping"])
        self.assertTrue(data["agents"]["merchant"])
        self.assertEqual(
            data["verticals"],
            ["retail", "travel", "telecom", "entertainment"],
        )
        self.assertTrue(data["checkout_hands_off"])
        self.assertFalse(data["charges_a_card"])
        self.assertEqual(data["anthropic_api_key"], "FINDER-FAILED")
        self.assertFalse(data["invented_stripe_urls"])
        self.assertFalse(data["commons_is_store"])
        self.assertFalse(data["remint_autogtm"])

    def test_json_renders_without_inventing_checkout(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertEqual(packet["repo"], "anthropics/commerce-agents")
        self.assertTrue(packet["shopping_agent"])
        self.assertTrue(packet["merchant_agent"])
        self.assertTrue(packet["checkout_hands_off"])
        self.assertFalse(packet["copy_blueprint_source"])
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertFalse(packet["remint_autogtm"])
        self.assertEqual(packet["anthropic_api_key"], "FINDER-FAILED")
        self.assertEqual(packet["sends"], 0)

    def test_send_live_checkout_refused(self) -> None:
        for flag in ("--send", "--go", "--live", "--checkout"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["refused"], flag)
        proc = run_helper("--not-a-real-flag")
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "FINDER-FAILED")
        self.assertEqual(payload["sent"], 0)

    def test_receipt_and_door_do_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")
        self.assertIn("cursor-claude-commerce-agents-20260902-01", text)
        self.assertIn("1788388678.488779", text)
        self.assertIn("Did **not** remint AutoGTM leftover", text)
        self.assertIn("fd4d59224", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("No login", door)
        self.assertIn("Possessing the link is enough", door)
        self.assertIn("git clone https://github.com/anthropics/commerce-agents.git", door)
        self.assertNotIn("https://buy.stripe.com/", door)
        self.assertNotIn("oauth", door.lower())
        self.assertIn("commerce-agents", skill)
        self.assertIn("do not copy the blueprint source onto Commons", skill)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
