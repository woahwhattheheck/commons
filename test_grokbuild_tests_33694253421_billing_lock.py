#!/usr/bin/env python3
"""Pin unique leftover for tests battery run 33694253421. Do not remint GOAT Pages MATCH."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-tests-33694253421-billing-lock-20260902-01.md"
MATCH = ROOT / "p/cursor-goat-pages-super-mcp-land-readback-match-20260902-01.md"
UNIQUE_PACK = ROOT / "p/cursor-goat-pages-super-mcp-land-readback-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/tests.yml"

KEEP = {
    "p/cursor-goat-pages-super-mcp-land-readback-match-20260902-01.md": "865b3c95",
    "test_cursor_goat_pages_super_mcp_land_readback_match.py": "1249f69e",
    "p/cursor-goat-pages-super-mcp-land-readback-20260902-01.md": "f98887bf",
    "test_cursor_goat_pages_super_mcp_land_readback.py": "38146134",
    "p/goat-pages-super-mcp-land-20260902-01.md": "171e0daaf",
    "catalog.html": "154b7b67",
    "boards.html": "3fa79f12",
    "hub_pages.py": "5ac12648",
    "wire.html": "4ae38ce9",
    ".github/workflows/tests.yml": "8c2f2301",
    "open_door_guard.py": "4b053e43",
    "p/cursor-big-huge-commerce-agents-readback-20260902-01.md": "2a5ce894",
    "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md": "7155141f",
    "p/grokbuild-tests-33694246830-billing-lock-20260902-01.md": "b07d6192",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTests33694253421BillingLock(unittest.TestCase):
    def test_keep_goat_pages_match_and_tests_yml_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name: tests", yml)
        self.assertIn("battery:", yml)
        self.assertIn("the whole battery, one failure fails the run", yml)
        self.assertIn("find . -maxdepth 1 -type f -name 'test_*.py'", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)
        self.assertNotIn("continue-on-error", yml)

    def test_local_failed_step_still_passes(self) -> None:
        for name, expected in (
            ("test_cursor_goat_pages_super_mcp_land_readback.py", "Ran 5 tests"),
            ("test_cursor_goat_pages_super_mcp_land_readback_match.py", "Ran 5 tests"),
        ):
            proc = subprocess.run(
                ["python3", "-m", "unittest", name],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=name + "\n" + proc.stdout + proc.stderr)
            self.assertIn(expected, proc.stderr)
        added = [
            guard.AddedLine("test_grokbuild_tests_33694253421_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine(
                "p/grokbuild-tests-33694253421-billing-lock-20260902-01.md", 1, line
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        match = MATCH.read_text(encoding="utf-8")
        unique_pack = UNIQUE_PACK.read_text(encoding="utf-8")
        self.assertIn("grokbuild-tests-33694253421-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:tests:1fb31f62c6af944f339ced5665446891a91c95cd:battery",
            text,
        )
        self.assertIn("33694253421", text)
        self.assertIn("100459584039", text)
        self.assertIn("100461143953", text)
        self.assertIn("1fb31f62c6af944f339ced5665446891a91c95cd", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("865b3c95", text)
        self.assertIn("1249f69e", text)
        self.assertIn("38146134", text)
        self.assertIn("171e0daaf", text)
        self.assertIn("154b7b67", text)
        self.assertIn("3fa79f12", text)
        self.assertIn("5ac12648", text)
        self.assertIn("8c2f2301", text)
        self.assertIn("2a5ce894", text)
        self.assertIn("KEEP-lift leftover tests", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not unique-pack merge-on-PR leftover", text)
        self.assertIn("did not reopen #7915", text.lower())
        self.assertNotEqual(text, match)
        self.assertNotEqual(text, unique_pack)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "tests.yml job battery checks out the repo and runs every "
                "discovered root test_*.py / test_*.js plus infra test_*.py "
                "on push to main that touches engine or test paths"
            ),
            "repair_attempts": [
                "KEEP-lift leftover unique-pack GOAT Pages tests off absence freeze",
                "local leftover unique-pack GOAT Pages 5/5 on current main",
                "local independent MATCH leftover 5/5",
                "open_door_guard PASS; test_open_door_guard.py PASS; test_fix_first.py 6/6",
                "publisher inventory 15/15 PASS",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal",
            ],
            "blocker": (
                "GitHub Actions ubuntu-latest never assigned: "
                "The job was not started because your account is locked due to a billing issue."
            ),
            "report_only_sessions": 0,
            "unconsumed_findings": 0,
        }
        self.assertEqual(fix_first.validate(packet)["state"], "EXTERNAL_BLOCKER")


if __name__ == "__main__":
    unittest.main()
