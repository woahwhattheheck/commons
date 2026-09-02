#!/usr/bin/env python3
"""Pin grok-build verify leftover for PR 8367. Do not remint #7915 helper."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/pr7915_closed_unmerged.py"
REPAIR = ROOT / "p/grok-repair-tests-battery-c57e501-pr7915-20260902-01.md"
RECEIPT = ROOT / "p/grokbuild-pr8367-verify-20260902-01.md"
LIVE = ROOT / "test_pr7915_closed_unmerged.py"

KEEP = {
    "test_pr7915_closed_unmerged.py": "195a38c0",
    "test_pr7915_harborline_readbacks_ack.py": "b3830936",
    "p/grok-repair-tests-battery-c57e501-pr7915-20260902-01.md": "2e73859d",
    "host/pr7915_closed_unmerged.py": "9d56ea0e",
    "autogtm.html": "9d8b3e85",
    "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md": "7a8987b5",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8367Verify(unittest.TestCase):
    def test_keep_8367_repair_and_helper_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

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
            self.assertFalse(row["permission"])
        src = HELPER.read_text(encoding="utf-8")
        self.assertNotIn("Authorization", src)
        self.assertNotIn("GITHUB_TOKEN", src)

    def test_live_test_accepts_non_200_as_named_miss(self) -> None:
        text = LIVE.read_text(encoding="utf-8")
        self.assertIn("if row[\"http\"] != 200:", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("Missing auth is not a Commons defect", text)
        self.assertIn("test_http_403_is_named_miss_never_reopen_never_silent_zero", text)
        self.assertIn("test_http_429_is_named_miss_never_reopen", text)

    def test_receipt_cites_8367_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        repair = REPAIR.read_text(encoding="utf-8")
        self.assertIn("id: grokbuild-pr8367-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8367@7f51741fdd757dc617edebd948e12eb4a07d30f8",
            text,
        )
        self.assertIn("c8c42fe3ef3caadaf5b960e6ecdab3646291deae", text)
        self.assertIn("195a38c0", text)
        self.assertIn("9d56ea0e", text)
        self.assertIn("issuecomment-5516512178", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("35/35 OK", text)
        self.assertIn("Did not remint helper", text)
        self.assertIn("No login", text)
        self.assertNotEqual(text, repair)
        self.assertNotIn("qualify.html", text)


if __name__ == "__main__":
    unittest.main()
