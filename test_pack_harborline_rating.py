#!/usr/bin/env python3
"""Harborline rating leftover. Does not steal GOAT template or peer packs."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_harborline_rating as rating  # noqa: E402


INVENTED = """# Third-party rating slot — Harborline Local Sites
id: cursor-business-pack-rating-slot-20260902-01
Badge URL: `https://example.invalid/seal.png`
Report URL: `OWNER_UNSET`
Partner name: `OWNER_UNSET`
Bulk price: `OWNER_UNSET`
Owner pasted: no
Checkout stays `NOT_MINTED`.
"""


class PackHarborlineRatingTest(unittest.TestCase):
    def test_does_not_claim_peer_or_factory_paths(self) -> None:
        self.assertIn("packs/_template/rating.md", rating.DO_NOT_OVERWRITE)
        self.assertIn("host/business_pack_rating.py", rating.DO_NOT_OVERWRITE)
        self.assertIn("packs/desk-website-service-20260902-01/door.html", rating.DO_NOT_OVERWRITE)
        self.assertIn("host/business_pack_harborline_tally_map.py", rating.DO_NOT_OVERWRITE)
        self.assertIn(
            "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md",
            rating.DO_NOT_OVERWRITE,
        )
        self.assertIn("packs/sidewalk-signal-web-desk-20260902-01", rating.DO_NOT_OVERWRITE)
        self.assertIn("packs/lotribbon-greetings-20260902-01", rating.DO_NOT_OVERWRITE)
        self.assertIn("packs/curbline-weekend-yard-help-20260902-01", rating.DO_NOT_OVERWRITE)
        self.assertIn("ground/BUSINESS_PACKS.json", rating.DO_NOT_OVERWRITE)

    def test_harborline_instance_stays_empty_owner_paste(self) -> None:
        if not rating.HARBORLINE.is_file():
            self.skipTest("Harborline rating sheet not in this tree")
        result = rating.classify_path(rating.HARBORLINE)
        text = rating.HARBORLINE.read_text(encoding="utf-8")
        self.assertEqual(result["verdict"], "HARBORLINE_RATING_INSTANCE_OK")
        self.assertEqual(result["factory_verdict"], "RATING_SLOT_EMPTY")
        self.assertTrue(result["empty"])
        self.assertIn("Harborline Local Sites", text)
        self.assertIn("OWNER_UNSET", text)
        self.assertIn("cursor-business-pack-rating-slot-20260902-01", text)
        self.assertIn("NOT_MINTED", text)
        self.assertNotIn("buy.stripe.com", text.lower())
        self.assertFalse(result["slots"]["owner_pasted_rating"])
        self.assertEqual(result["sends"], 0)

    def test_invented_url_fails(self) -> None:
        path = Path("/tmp/harborline-rating-invented.md")
        path.write_text(INVENTED, encoding="utf-8")
        result = rating.classify_path(path)
        self.assertEqual(result["verdict"], "RATING_LINK_INVENTED")

    def test_tree_ok_and_peer_pins_lifted(self) -> None:
        if not rating.TEMPLATE.is_file() or not rating.HARBORLINE.is_file():
            self.skipTest("rating files not in this tree")
        result = rating.classify_tree()
        self.assertEqual(result["verdict"], "HARBORLINE_RATING_OK", msg=result)
        self.assertTrue(result["live_peer_blobs_not_pinned"])
        self.assertTrue(result["peer_absence_not_pinned"])
        self.assertTrue(result["did_not_rewrite_goat_template"])
        self.assertTrue(result["did_not_remint_factory_slot"])
        self.assertTrue(result["did_not_overwrite_harborline_door"])
        self.assertTrue(result["did_not_write_leftover_pin_helpers"])
        self.assertTrue(result["did_not_overwrite_pointer_receipt"])
        self.assertTrue(result["did_not_rewrite_harborline_sheet"])
        self.assertTrue(result["did_not_fill_sidewalk"])
        self.assertTrue(result["did_not_fill_lotribbon"])
        self.assertTrue(result["did_not_merge_7915"])
        self.assertTrue(result["did_not_remint_leftover_receipt"])
        self.assertEqual(
            result["observed_at_land"][rating.HARBORLINE_REL],
            "7fe8667a",
        )
        self.assertEqual(
            result["observed_at_land"][rating.POINTER_RECEIPT_REL],
            "7a8987b5",
        )
        self.assertIn(rating.LOTRIBBON_REL, result["peer_absence_at_land"])
        self.assertIn(rating.LOTRIBBON_REL, rating.DO_NOT_OVERWRITE)
        self.assertNotIn(rating.LOTRIBBON_REL, rating.THIS_SEAT_PATHS)
        self.assertNotIn(rating.HARBORLINE_REL, rating.THIS_SEAT_PATHS)
        dumped = json.dumps(result)
        self.assertNotIn("337 NO", dumped)
        self.assertEqual(result["checkout"], "NOT_MINTED")

    def test_lotribbon_presence_does_not_fail_tree(self) -> None:
        if not rating.HARBORLINE.is_file():
            self.skipTest("Harborline rating sheet not in this tree")
        fake = Path("/tmp/lotribbon-rating-presence.md")
        fake.write_text("# LotRibbon peer fill\nCheckout stays `NOT_MINTED`.\n", encoding="utf-8")
        with unittest.mock.patch.object(rating, "LOTRIBBON", fake):
            result = rating.classify_tree()
        self.assertTrue(fake.is_file())
        self.assertEqual(result["verdict"], "HARBORLINE_RATING_OK", msg=result)
        self.assertTrue(result["peer_absence_not_pinned"])
        self.assertTrue(result["did_not_fill_lotribbon"])

    def test_pointer_receipt_blob_drift_does_not_fail_tree(self) -> None:
        if not rating.HARBORLINE.is_file():
            self.skipTest("Harborline rating sheet not in this tree")
        real = rating.git_blob_prefix

        def drifted(rel: str, n: int = 8) -> str:
            if rel == rating.POINTER_RECEIPT_REL:
                return "deadbeef"
            return real(rel, n)

        with unittest.mock.patch.object(rating, "git_blob_prefix", drifted):
            result = rating.classify_tree()
        self.assertEqual(result["verdict"], "HARBORLINE_RATING_OK", msg=result)
        self.assertTrue(result["live_peer_blobs_not_pinned"])
        self.assertEqual(result["blobs"][rating.POINTER_RECEIPT_REL], "deadbeef")
        self.assertEqual(result["observed_at_land"][rating.POINTER_RECEIPT_REL], "7a8987b5")

    def test_cli_json(self) -> None:
        if not rating.HARBORLINE.is_file():
            self.skipTest("Harborline rating sheet not in this tree")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "pack_harborline_rating.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["verdict"], "HARBORLINE_RATING_OK")
        self.assertIs(data["gate"], False)
        self.assertEqual(data["receipt_id"], "cursor-pack-harborline-rating-20260902-01")


if __name__ == "__main__":
    unittest.main()
