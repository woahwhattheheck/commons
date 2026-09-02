#!/usr/bin/env python3
"""Harborline rating peer-unpin leftover. Does not remint leftover receipt."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_harborline_rating as leftover  # noqa: E402
import pack_harborline_rating_peer_unpin as unpin  # noqa: E402


class PackHarborlineRatingPeerUnpinTest(unittest.TestCase):
    def test_unpin_cites_leftover_without_remint(self) -> None:
        result = unpin.classify_unpin()
        self.assertEqual(result["id"], unpin.UNPIN_ID)
        self.assertEqual(result["leftover_id"], leftover.RECEIPT_ID)
        self.assertNotEqual(unpin.UNPIN_ID, leftover.RECEIPT_ID)
        self.assertTrue(result["unpin_ok"], msg=result)
        self.assertEqual(result["verdict"], "HARBORLINE_RATING_PEER_UNPIN_OK")
        self.assertTrue(result["live_peer_blobs_not_pinned"])
        self.assertTrue(result["peer_absence_not_pinned"])
        self.assertTrue(result["did_not_fill_lotribbon"])
        self.assertTrue(result["did_not_rewrite_harborline_sheet"])
        self.assertTrue(result["did_not_remint_leftover_receipt"])
        self.assertTrue(result["did_not_overwrite_pointer_receipt"])
        self.assertTrue(result["did_not_merge_7915"])
        self.assertEqual(result["checkout"], "NOT_MINTED")
        self.assertEqual(
            result["observed_at_land"][leftover.HARBORLINE_REL],
            "7fe8667a",
        )
        self.assertTrue(
            result["blobs"][f"p/{leftover.RECEIPT_ID}.md"].startswith("29930d8b")
        )
        self.assertTrue(result["blobs"][leftover.HARBORLINE_REL].startswith("7fe8667a"))
        self.assertIs(result["gate"], False)
        self.assertIn(leftover.LOTRIBBON_REL, leftover.DO_NOT_OVERWRITE)
        self.assertNotIn(leftover.LOTRIBBON_REL, leftover.THIS_SEAT_PATHS)

    def test_receipt_names_keep_main_and_unread_sheet(self) -> None:
        path = ROOT / "p" / f"{unpin.UNPIN_ID}.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn(f"id: {unpin.UNPIN_ID}", text)
        self.assertIn(leftover.RECEIPT_ID, text)
        self.assertIn("7fe8667a", text)
        self.assertIn("KEEP MAIN #7915", text)
        self.assertIn("NOT_MINTED", text)
        self.assertIn("CLAUDE_INTERMEDIATE_UNTRUSTED", text)
        self.assertIn("did not remint", text.lower())
        self.assertNotIn("337 NO", text)

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "pack_harborline_rating_peer_unpin.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["verdict"], "HARBORLINE_RATING_PEER_UNPIN_OK")
        self.assertTrue(data["unpin_ok"])
        self.assertIs(data["gate"], False)


if __name__ == "__main__":
    unittest.main()
