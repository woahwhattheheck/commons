#!/usr/bin/env python3
"""LotRibbon rating leftover. Does not steal GOAT template or Harborline sheet."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_lotribbon_rating as rating  # noqa: E402


INVENTED = """# Third-party rating slot — LotRibbon Greetings
id: cursor-business-pack-rating-slot-20260902-01
Harborline sheet 7fe8667a unread-as-write.
cursor-pack-harborline-rating-peer-unpin-20260902-01 already landed.
Badge URL: `https://example.invalid/seal.png`
Report URL: `OWNER_UNSET`
Partner name: `OWNER_UNSET`
Bulk price: `OWNER_UNSET`
Owner pasted: no
Checkout stays `NOT_MINTED`.
"""


class PackLotribbonRatingTest(unittest.TestCase):
    def test_does_not_claim_peer_or_factory_paths(self) -> None:
        self.assertIn("packs/_template/rating.md", rating.DO_NOT_OVERWRITE)
        self.assertIn("host/business_pack_rating.py", rating.DO_NOT_OVERWRITE)
        self.assertIn("p/cursor-pack-harborline-rating-20260902-01.md", rating.DO_NOT_OVERWRITE)
        self.assertIn("p/cursor-pack-harborline-rating-peer-unpin-20260902-01.md", rating.DO_NOT_OVERWRITE)
        self.assertIn("packs/desk-website-service-20260902-01/rating.md", rating.DO_NOT_OVERWRITE)
        self.assertIn("host/pack_harborline_rating.py", rating.DO_NOT_OVERWRITE)
        self.assertIn("packs/lotribbon-greetings-20260902-01/index.html", rating.DO_NOT_OVERWRITE)
        self.assertIn(
            "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md",
            rating.DO_NOT_OVERWRITE,
        )
        self.assertIn("packs/sidewalk-signal-web-desk-20260902-01", rating.DO_NOT_OVERWRITE)
        self.assertIn("packs/curbline-weekend-yard-help-20260902-01", rating.DO_NOT_OVERWRITE)
        self.assertIn("ground/BUSINESS_PACKS.json", rating.DO_NOT_OVERWRITE)

    def test_lotribbon_instance_stays_empty_owner_paste(self) -> None:
        if not rating.LOTRIBBON.is_file():
            self.skipTest("LotRibbon rating sheet not in this tree")
        result = rating.classify_path(rating.LOTRIBBON)
        text = rating.LOTRIBBON.read_text(encoding="utf-8")
        self.assertEqual(result["verdict"], "LOTRIBBON_RATING_INSTANCE_OK")
        self.assertEqual(result["factory_verdict"], "RATING_SLOT_EMPTY")
        self.assertTrue(result["empty"])
        self.assertIn("LotRibbon Greetings", text)
        self.assertIn("OWNER_UNSET", text)
        self.assertIn("cursor-business-pack-rating-slot-20260902-01", text)
        self.assertIn("NOT_MINTED", text)
        self.assertIn("7fe8667a", text)
        self.assertIn("cursor-pack-harborline-rating-peer-unpin-20260902-01", text)
        self.assertIn("#7915", text)
        self.assertNotIn("buy.stripe.com", text.lower())
        self.assertFalse(result["slots"]["owner_pasted_rating"])
        self.assertEqual(result["sends"], 0)

    def test_invented_url_fails(self) -> None:
        path = Path("/tmp/lotribbon-rating-invented.md")
        path.write_text(INVENTED, encoding="utf-8")
        result = rating.classify_path(path)
        self.assertEqual(result["verdict"], "RATING_LINK_INVENTED")

    def test_tree_ok_and_harborline_unread(self) -> None:
        if not rating.TEMPLATE.is_file() or not rating.LOTRIBBON.is_file():
            self.skipTest("rating files not in this tree")
        result = rating.classify_tree()
        self.assertEqual(result["verdict"], "LOTRIBBON_RATING_OK", msg=result)
        self.assertTrue(result["did_not_rewrite_goat_template"])
        self.assertTrue(result["did_not_remint_factory_slot"])
        self.assertTrue(result["did_not_overwrite_lotribbon_door"])
        self.assertTrue(result["did_not_overwrite_harborline_rating"])
        self.assertTrue(result["did_not_remint_harborline_receipt"])
        self.assertTrue(result["did_not_remint_harborline_unpin"])
        self.assertTrue(result["did_not_overwrite_pointer_receipt"])
        self.assertTrue(result["did_not_fill_sidewalk"])
        self.assertTrue(result["did_not_merge_7915"])
        self.assertTrue(result["harborline_sheet_read"])
        self.assertEqual(result["blobs"]["packs/_template/rating.md"], "7d644a8b")
        self.assertEqual(
            result["blobs"]["packs/lotribbon-greetings-20260902-01/index.html"],
            "7804ec33",
        )
        self.assertEqual(
            result["blobs"]["packs/desk-website-service-20260902-01/rating.md"],
            "7fe8667a",
        )
        self.assertEqual(
            result["blobs"]["p/cursor-pack-harborline-rating-20260902-01.md"],
            "29930d8b",
        )
        self.assertEqual(
            result["blobs"]["p/cursor-pack-harborline-rating-peer-unpin-20260902-01.md"],
            "9d1991f3",
        )
        self.assertEqual(
            result["blobs"][
                "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md"
            ],
            "7a8987b5",
        )
        dumped = json.dumps(result)
        self.assertNotIn("337 NO", dumped)
        self.assertEqual(result["checkout"], "NOT_MINTED")
        self.assertEqual(result["receipt_id"], "cursor-lead-lotribbon-rating-20260902-01")
        self.assertEqual(result["unpin_id"], "cursor-pack-harborline-rating-peer-unpin-20260902-01")

    def test_cli_json(self) -> None:
        if not rating.LOTRIBBON.is_file():
            self.skipTest("LotRibbon rating sheet not in this tree")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "pack_lotribbon_rating.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["verdict"], "LOTRIBBON_RATING_OK")
        self.assertIs(data["gate"], False)
        self.assertEqual(data["receipt_id"], "cursor-lead-lotribbon-rating-20260902-01")
        self.assertEqual(data["checkout"], "NOT_MINTED")


if __name__ == "__main__":
    unittest.main()
