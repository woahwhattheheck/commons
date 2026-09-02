#!/usr/bin/env python3
"""Pin unique-pack readback of Harborline KEEP-lift leftover. Do not remint KEEP-lift."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md"
KEEP_LIFT = ROOT / "p/cursor-harborline-commerce-compose-keep-lift-20260902-01.md"
HELPER = ROOT / "host/harborline_commerce_compose.py"

KEEP = {
    "p/cursor-harborline-commerce-compose-keep-lift-20260902-01.md": "668dd5c4",
    "p/cursor-harborline-commerce-compose-20260902-01.md": "45b7d435",
    "host/harborline_commerce_compose.py": "75128e5d",
    "test_harborline_commerce_compose.py": "96bea929",
    "test_harborline_commerce_compose_keep_lift.py": "aa5e2571",
    "p/cursor-claude-commerce-agents-readback-20260902-01.md": "0153924f",
    "p/cursor-harborline-commerce-compose-readback-20260902-01.md": "b33e2e24",
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "host/commerce_agents.py": "8d2ddf29",
    "p/cursor-big-huge-commerce-agents-20260902-01.md": "fddb5a7c",
    "host/commerce_agents_same_loop.py": "c90f6e50",
    "test_commerce_agents_same_loop.py": "623e99e8",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
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


class TestCursorHarborlineCommerceComposeKeepLiftReadback(unittest.TestCase):
    def test_keep_lift_and_leftover_unique_pack(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        leftover_unique_lead = git_blob("test_cursor_claude_commerce_agents_readback.py")
        leftover_unique_harbor = git_blob(
            "test_cursor_harborline_commerce_compose_readback.py"
        )
        self.assertFalse(
            leftover_unique_lead.startswith("0ed81a06"),
            "leftover unique-pack LEAD tests were not lifted off the absence freeze",
        )
        self.assertFalse(
            leftover_unique_harbor.startswith("34da2639"),
            "leftover unique-pack Harborline tests were not lifted off the absence freeze",
        )
        self.assertNotIn("boards.html", KEEP)
        self.assertNotIn("index.html", KEEP)
        self.assertNotIn("hub_pages.py", KEEP)
        self.assertNotIn("door.js", KEEP)

    def test_leftover_json_and_send_still_finder_failed(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["cart"]["lines"][0]["product_id"], "harborline-local-sites")
        self.assertEqual(packet["product"]["price_usd"], 200)
        self.assertEqual(packet["desk_route"], "/shop")
        self.assertEqual(packet["over"], "/market")
        self.assertEqual(
            packet["checkout"]["host_only"]["checkout_handoff"]["state"],
            "FINDER-FAILED",
        )
        self.assertIsNone(packet["checkout"]["host_only"]["checkout_handoff"]["url"])
        self.assertFalse(packet["checkout"]["model_sees_url"])
        self.assertEqual(packet["sent"], 0)
        self.assertEqual(packet["cash"], 0)
        self.assertNotIn("buy.stripe.com", proc.stdout)
        for flag in ("--send", "--go", "--live", "--dump-commons", "--marketplace-html"):
            refused = run_helper(flag)
            self.assertEqual(refused.returncode, 2, msg=refused.stdout + refused.stderr)
            payload = json.loads(refused.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload["invented_stripe_urls"])

    def test_keep_lift_and_compose_tests_still_pass(self) -> None:
        lift = subprocess.run(
            ["python3", "-m", "unittest", "test_harborline_commerce_compose_keep_lift.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(lift.returncode, 0, msg=lift.stdout + lift.stderr)
        self.assertIn("Ran 5 tests", lift.stderr)
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_harborline_commerce_compose.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 6 tests", leftover.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = KEEP_LIFT.read_text(encoding="utf-8")
        self.assertIn("cursor-harborline-commerce-compose-keep-lift-readback-20260902-01", text)
        self.assertIn("52b6ade27", text)
        self.assertIn("6e6813a4f", text)
        self.assertIn("668dd5c4", text)
        self.assertIn("75128e5d", text)
        self.assertIn("45b7d435", text)
        self.assertIn("0ed81a06", text)
        self.assertIn("34da2639", text)
        self.assertIn("Did **not** remint KEEP-lift", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
