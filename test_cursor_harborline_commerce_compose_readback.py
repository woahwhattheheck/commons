#!/usr/bin/env python3
"""Pin unique-pack readback of Harborline commerce-compose leftover. Do not remint leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-harborline-commerce-compose-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-harborline-commerce-compose-20260902-01.md"
HELPER = ROOT / "host/harborline_commerce_compose.py"

KEEP = {
    "p/cursor-harborline-commerce-compose-20260902-01.md": "45b7d435",
    "host/harborline_commerce_compose.py": "75128e5d",
    "p/cursor-harborline-commerce-compose-keep-lift-20260902-01.md": "668dd5c4",
    "test_harborline_commerce_compose.py": "96bea929",
    "test_harborline_commerce_compose_keep_lift.py": "aa5e2571",
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "host/commerce_agents.py": "8d2ddf29",
    "ground/COMMERCE_AGENTS.json": "ab6f56a8",
    "commerce-agents.html": "e2028ddc",
    ".agents/skills/commerce-agents/SKILL.md": "1f93c4a2",
    "test_commerce_agents.py": "78a158b3",
    "p/cursor-big-huge-commerce-agents-20260902-01.md": "fddb5a7c",
    "host/commerce_agents_same_loop.py": "c90f6e50",
    "test_commerce_agents_same_loop.py": "623e99e8",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "p/cursor-what-a-pack-is-20260902-01.md": "a4e4dd89",
    "p/cursor-pack-is-ready-to-run-20260902-01.md": "897b00ba",
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
    "packs/desk-website-service-20260902-01/instance.json": "f460d7bc",
    "packs/desk-website-service-20260902-01/checkout.md": "64633e36",
    "packs/desk-website-service-20260902-01/door.html": "d3d6fcc7",
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


class TestCursorHarborlineCommerceComposeReadback(unittest.TestCase):
    def test_keep_leftover_helper_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        leftover_tests = git_blob("test_harborline_commerce_compose.py")
        self.assertFalse(
            leftover_tests.startswith("277e5612"),
            "KEEP-lift unread expected leftover tests off absence freeze",
        )

    def test_leftover_json_fills_cart_and_handoff_stays_finder_failed(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["id"], "cursor-harborline-commerce-compose-20260902-01")
        self.assertEqual(packet["cite"], "https://github.com/anthropics/commerce-agents")
        self.assertFalse(packet["copy_blueprint_source"])
        self.assertEqual(packet["lead_leftover"], "cursor-claude-commerce-agents-20260902-01")
        self.assertEqual(packet["desk_route"], "/shop")
        self.assertEqual(packet["over"], "/market")
        self.assertEqual(packet["product"]["title"], "Harborline Local Sites")
        self.assertEqual(packet["product"]["price_usd"], 200)
        self.assertTrue(packet["cart"]["filled"])
        self.assertEqual(packet["cart"]["lines"][0]["product_id"], "harborline-local-sites")
        self.assertIsNone(packet["checkout"]["model_visible"]["checkout_url"])
        self.assertFalse(packet["checkout"]["model_sees_url"])
        self.assertEqual(
            packet["checkout"]["host_only"]["checkout_handoff"]["state"],
            "FINDER-FAILED",
        )
        self.assertIsNone(packet["checkout"]["host_only"]["checkout_handoff"]["url"])
        self.assertEqual(packet["merchant_staged"]["status"], "staged")
        self.assertFalse(packet["merchant_staged"]["applied"])
        self.assertEqual(packet["sent"], 0)
        self.assertEqual(packet["cash"], 0)
        self.assertNotIn("buy.stripe.com", proc.stdout)

    def test_leftover_send_go_dump_refused(self) -> None:
        for flag in ("--send", "--go", "--live", "--dump-commons", "--marketplace-html"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload["invented_stripe_urls"])

    def test_leftover_tests_pass_after_keep_lift_unread(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_harborline_commerce_compose.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 6 tests", leftover.stderr)
        lift = subprocess.run(
            ["python3", "-m", "unittest", "test_harborline_commerce_compose_keep_lift.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(lift.returncode, 0, msg=lift.stdout + lift.stderr)
        self.assertIn("Ran 5 tests", lift.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-harborline-commerce-compose-readback-20260902-01", text)
        self.assertIn("d4e327feb", text)
        self.assertIn("45b7d435", text)
        self.assertIn("75128e5d", text)
        self.assertIn("668dd5c4", text)
        self.assertIn("96bea929", text)
        self.assertIn("277e5612", text)
        self.assertIn("Did **not** remint leftover helper", text)
        self.assertIn("Did **not** unique-pack this seat remainder", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertTrue(
            (ROOT / "p/cursor-big-huge-commerce-agents-20260902-01.md").exists()
        )
        self.assertTrue(
            (ROOT / "p/cursor-big-huge-commerce-agents-readback-20260902-01.md").exists()
        )
        self.assertTrue(
            (
                ROOT
                / "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md"
            ).exists()
        )
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
