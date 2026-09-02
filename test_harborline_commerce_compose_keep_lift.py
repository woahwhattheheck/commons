#!/usr/bin/env python3
"""KEEP-lift Harborline compose leftover tests after unique-pack leftover landed."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-harborline-commerce-compose-keep-lift-20260902-01.md"
COMPOSE_HELPER = ROOT / "host/harborline_commerce_compose.py"
COMPOSE_RECEIPT = ROOT / "p/cursor-harborline-commerce-compose-20260902-01.md"
UNIQUE_RECEIPT = ROOT / "p/cursor-big-huge-commerce-agents-20260902-01.md"
UNIQUE_HELPER = ROOT / "host/commerce_agents_same_loop.py"

KEEP = {
    "host/harborline_commerce_compose.py": "75128e5d",
    "p/cursor-harborline-commerce-compose-20260902-01.md": "45b7d435",
    "p/cursor-big-huge-commerce-agents-20260902-01.md": "fddb5a7c",
    "host/commerce_agents_same_loop.py": "c90f6e50",
    "test_commerce_agents_same_loop.py": "623e99e8",
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "host/commerce_agents.py": "8d2ddf29",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "p/cursor-what-a-pack-is-20260902-01.md": "a4e4dd89",
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestHarborlineCommerceComposeKeepLift(unittest.TestCase):
    def test_keep_compose_helper_and_unique_pack_leftover(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        lifted = git_blob("test_harborline_commerce_compose.py")
        self.assertFalse(
            lifted.startswith("277e5612"),
            "leftover tests were not lifted off the unique-pack absence freeze",
        )

    def test_leftover_compose_tests_pass_after_lift(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_harborline_commerce_compose.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 6 tests", proc.stderr)

    def test_unique_pack_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_commerce_agents_same_loop.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 12 tests", proc.stderr)

    def test_compose_json_still_finder_failed(self) -> None:
        proc = subprocess.run(
            ["python3", str(COMPOSE_HELPER), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("harborline-local-sites", proc.stdout)
        self.assertIn("FINDER-FAILED", proc.stdout)
        self.assertNotIn("buy.stripe.com", proc.stdout)
        proc_go = subprocess.run(
            ["python3", str(COMPOSE_HELPER), "--go"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc_go.returncode, 2)
        self.assertIn('"sent": 0', proc_go.stdout)

    def test_receipt_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = COMPOSE_RECEIPT.read_text(encoding="utf-8")
        unique = UNIQUE_RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-harborline-commerce-compose-keep-lift-20260902-01", text)
        self.assertIn("1788389483.199439", text)
        self.assertIn("1788388977.765219", text)
        self.assertIn("75128e5d", text)
        self.assertIn("45b7d435", text)
        self.assertIn("277e5612", text)
        self.assertIn("fddb5a7c", text)
        self.assertIn("4a630e83", text)
        self.assertIn("955d166fe", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, unique)
        self.assertNotIn("buy.stripe.com", text)
        self.assertTrue(UNIQUE_HELPER.exists())
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
