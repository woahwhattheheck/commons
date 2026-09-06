#!/usr/bin/env python3
"""Pin Harborline operator library leftover. Do not remint merchant portal leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/harborline_operator_library.py"
RECEIPT = ROOT / "p/cursor-harborline-operator-library-20260903-01.md"
MERCHANT_HELPER = ROOT / "host/harborline_merchant_portal.py"
COMPOSE_HELPER = ROOT / "host/harborline_commerce_compose.py"

KEEP = {
    "p/cursor-harborline-merchant-portal-20260903-01.md": "18f06c0d",
    "host/harborline_merchant_portal.py": "c54f35e2",
    "test_harborline_merchant_portal.py": "b716966b",
    "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md": "7155141f",
    "test_cursor_harborline_commerce_compose_keep_lift_readback.py": "3aef5052",
    "host/harborline_commerce_compose.py": "75128e5d",
    "p/cursor-harborline-commerce-compose-20260902-01.md": "45b7d435",
    "p/cursor-harborline-commerce-compose-keep-lift-20260902-01.md": "668dd5c4",
    "test_harborline_commerce_compose.py": "aeb0588b",
    "test_harborline_commerce_compose_keep_lift.py": "0e4f5ec1",
    "p/cursor-harborline-commerce-compose-readback-20260902-01.md": "b33e2e24",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "p/cursor-desk-website-harborline-20260902-01.md": "655b9eb1",
    "p/cursor-what-a-pack-is-20260902-01.md": "a4e4dd89",
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
    "ground/CLAUDE_PEER_CHECK.md": "fac0eea8",
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


class TestHarborlineOperatorLibrary(unittest.TestCase):
    def test_keep_merchant_and_compose_leftovers(self) -> None:
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
        self.assertNotIn("packs/desk-website-service-20260902-01/outreach.md", KEEP)

    def test_json_library_keeps_merchant_and_compose(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["id"], "cursor-harborline-operator-library-20260903-01")
        self.assertEqual(packet["desk_route"], "/library")
        self.assertEqual(packet["brochure"], "/harborline")
        self.assertEqual(packet["merchant"], "/merchant")
        self.assertEqual(packet["instance"]["price_usd"], 250)
        self.assertFalse(packet["instance"]["held"])
        self.assertEqual(packet["hold"], "FINDER-FAILED")
        self.assertEqual(packet["build_pack"], "withheld")
        self.assertTrue(packet["methods_public"])
        self.assertEqual(packet["leftover_merchant"]["price_usd"], 250)
        self.assertEqual(packet["leftover_merchant"]["desk_route"], "/merchant")
        self.assertEqual(packet["leftover_compose"]["price_usd"], 200)
        self.assertEqual(packet["leftover_compose"]["checkout"], "FINDER-FAILED")
        self.assertEqual(packet["leftover_compose"]["sent"], 0)
        self.assertEqual(packet["checkout"], "FINDER-FAILED")
        self.assertEqual(packet["stripe_card"], "do_not_ask_bryce_to_reenter")
        self.assertEqual(packet["pack_market_skin"], "unread")
        self.assertEqual(packet["type_pk"], "unread")
        self.assertEqual(packet["commons_pack_markdown"], "unread")
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["sent"], 0)
        self.assertIn("gap_log", packet["tools"])
        self.assertIn("yes_first_outreach", packet["tools"])
        self.assertNotIn("buy.stripe.com", proc.stdout)
        merchant = subprocess.run(
            ["python3", str(MERCHANT_HELPER), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(merchant.returncode, 0, msg=merchant.stdout + merchant.stderr)
        merchant_packet = json.loads(merchant.stdout)
        self.assertEqual(merchant_packet["desk_route"], "/merchant")
        self.assertEqual(merchant_packet["listing"]["price_usd"], 250)
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

    def test_independently_leftover_merchant_tests_still_pass(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_harborline_merchant_portal.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 5 tests", leftover.stderr)

    def test_receipt_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-harborline-operator-library-20260903-01", text)
        self.assertIn("1788435385.830849", text)
        self.assertIn("18f06c0d", text)
        self.assertIn("c54f35e2", text)
        self.assertIn("7155141f", text)
        self.assertIn("75128e5d", text)
        self.assertIn("45b7d435", text)
        self.assertIn("54c348dc", text)
        self.assertIn("Did **not** remint", text)
        self.assertIn("/library", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
