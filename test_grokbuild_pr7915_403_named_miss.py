#!/usr/bin/env python3
"""Repair leftover: #7915 live GitHub 403/429 is FINDER-FAILED. KEEP helper."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-repair-tests-battery-c57e501-pr7915-20260902-01.md"
HELPER = ROOT / "host/pr7915_closed_unmerged.py"

KEEP_UNREAD = {
    "host/pr7915_closed_unmerged.py": "9d56ea0e",
    "autogtm.html": "9d8b3e85",
    "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md": "7a8987b5",
    "p/cursor-pr7915-closed-unmerged-readback-20260902-01.md": "2a7f31a4",
    "p/cursor-pr7915-harborline-readbacks-ack-20260902-01.md": "7082ab78",
    "ground/OWNER_NOW.md": "6b8ee988",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class GrokbuildPr7915NamedMissRepair(unittest.TestCase):
    def test_did_not_remint_keep_main_paths(self) -> None:
        for rel, prefix in KEEP_UNREAD.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_ack_leftover_keep_does_not_freeze_live_pr7915_test(self) -> None:
        import test_pr7915_harborline_readbacks_ack as ack

        self.assertNotIn("test_pr7915_closed_unmerged.py", ack.KEEP)
        self.assertIn("host/pr7915_closed_unmerged.py", ack.KEEP)

    def test_helper_classifies_403_and_429_as_finder_failed_without_auth(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("pr7915_closed_unmerged", HELPER)
        assert spec and spec.loader
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        for code, msg in (
            (403, "API rate limit exceeded"),
            (429, "You have exceeded a secondary rate limit"),
        ):
            row = probe.classify(code, json.dumps({"message": msg}).encode("utf-8"))
            self.assertEqual(row["state"], "FINDER-FAILED", code)
            self.assertEqual(row["http"], code)
            self.assertFalse(row["reopened"])
            self.assertEqual(row["sent"], 0)
        src = HELPER.read_text(encoding="utf-8")
        self.assertNotIn("Authorization", src)
        self.assertNotIn("GITHUB_TOKEN", src)

    def test_receipt_names_run_and_keeps_open_door(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: grok-repair-tests-battery-c57e501-pr7915-20260902-01", text)
        self.assertIn("c57e501b15edb2a54137d11fe176f0ba2686722e", text)
        self.assertIn("33681137186", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("9d56ea0e", text)
        self.assertIn("#8361", text)
        self.assertIn("Did not remint", text)
        self.assertIn("No login", text)
        self.assertNotIn("qualify.html", text)


if __name__ == "__main__":
    unittest.main()
