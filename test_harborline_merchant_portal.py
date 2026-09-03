#!/usr/bin/env python3
"""Pin Harborline merchant portal leftover. Do not remint leftover compose."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/harborline_merchant_portal.py"
RECEIPT = ROOT / "p/cursor-harborline-merchant-portal-20260903-01.md"
COMPOSE_HELPER = ROOT / "host/harborline_commerce_compose.py"

KEEP = {
    "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md": "7155141f",
    "test_cursor_harborline_commerce_compose_keep_lift_readback.py": "5ab31d10",
    "host/harborline_commerce_compose.py": "75128e5d",
    "p/cursor-harborline-commerce-compose-20260902-01.md": "45b7d435",
    "p/cursor-harborline-commerce-compose-keep-lift-20260902-01.md": "668dd5c4",
    "test_harborline_commerce_compose.py": "96bea929",
    "test_harborline_commerce_compose_keep_lift.py": "aa5e2571",
    "p/cursor-harborline-commerce-compose-readback-20260902-01.md": "b33e2e24",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "p/cursor-what-a-pack-is-20260902-01.md": "a4e4dd89",
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "ground/CLAUDE_PEER_CHECK.md": "3cb9709b",
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


class TestHarborlineMerchantPortal(unittest.TestCase):
    def test_keep_leftover_compose_and_keep_lift_unique(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertNotIn("CLAUDE.md", KEEP)
        self.assertNotIn("wire.html", KEEP)
        self.assertNotIn("boards.html", KEEP)

    def test_json_origin_floor_keeps_leftover_compose_price(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["id"], "cursor-harborline-merchant-portal-20260903-01")
        self.assertEqual(packet["desk_route"], "/merchant")
        self.assertEqual(packet["listing"]["price_usd"], 250)
        self.assertEqual(packet["owner_floor"]["min_usd"], 250)
        self.assertEqual(packet["owner_floor"]["max_usd"], 399)
        self.assertTrue(packet["listing"]["applied"])
        self.assertFalse(packet["next_instance"]["applied"])
        self.assertFalse(packet["tier"]["applied"])
        self.assertEqual(packet["leftover_compose"]["price_usd"], 200)
        self.assertEqual(packet["leftover_compose"]["checkout"], "FINDER-FAILED")
        self.assertEqual(packet["leftover_compose"]["sent"], 0)
        self.assertEqual(packet["checkout"], "FINDER-FAILED")
        self.assertEqual(packet["stripe_card"], "do_not_ask_bryce_to_reenter")
        self.assertEqual(packet["pack_market_skin"], "unread")
        self.assertEqual(packet["type_pk"], "unread")
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["sent"], 0)
        self.assertNotIn("buy.stripe.com", proc.stdout)
        leftover = subprocess.run(
            ["python3", str(COMPOSE_HELPER), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        compose = json.loads(leftover.stdout)
        self.assertEqual(compose["product"]["price_usd"], 200)
        self.assertEqual(compose["desk_route"], "/shop")

    def test_send_go_dump_refused(self) -> None:
        for flag in ("--send", "--go", "--live", "--dump-commons", "--marketplace-html"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload["invented_stripe_urls"])

    def test_leftover_compose_and_keep_lift_unique_tests_still_pass(self) -> None:
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
            [
                "python3",
                "-m",
                "unittest",
                "test_harborline_commerce_compose_keep_lift.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(lift.returncode, 0, msg=lift.stdout + lift.stderr)
        self.assertIn("Ran 5 tests", lift.stderr)
        unique = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_cursor_harborline_commerce_compose_keep_lift_readback.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(unique.returncode, 0, msg=unique.stdout + unique.stderr)
        self.assertIn("Ran 4 tests", unique.stderr)

    def test_receipt_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-harborline-merchant-portal-20260903-01", text)
        self.assertIn("1788395816.824549", text)
        self.assertIn("1788394247.211089", text)
        self.assertIn("1788394778.868359", text)
        self.assertIn("7155141f", text)
        self.assertIn("75128e5d", text)
        self.assertIn("45b7d435", text)
        self.assertIn("54c348dc", text)
        self.assertIn("Did **not** remint", text)
        self.assertIn("/merchant", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
