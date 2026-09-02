#!/usr/bin/env python3
"""LotRibbon waitlist-slot leftover. Does not steal GOAT template or peer packs."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_lotribbon_waitlist_slot as slot  # noqa: E402


INVENTED = """# Waitlist slot — LotRibbon Greetings
id: cursor-pack-door-waitlist-20260902-01
Form: packs/waitlist.html
Door blob 7804ec33 unread.
Zero sends.
Checkout stays `NOT_MINTED`.
Contact: operator@example.invalid
"""

STRIPED = """# Waitlist slot — LotRibbon Greetings
id: cursor-pack-door-waitlist-20260902-01
Form: packs/waitlist.html
Door blob 7804ec33 unread.
Zero sends.
Checkout stays `NOT_MINTED`.
Pay: https://buy.stripe.com/test_000
"""


class PackLotribbonWaitlistSlotTest(unittest.TestCase):
    def test_does_not_claim_peer_or_factory_paths(self) -> None:
        self.assertIn("packs/_template/waitlist-slot.md", slot.DO_NOT_OVERWRITE)
        self.assertIn("host/pack_waitlist.py", slot.DO_NOT_OVERWRITE)
        self.assertIn("packs/waitlist.html", slot.DO_NOT_OVERWRITE)
        self.assertIn(
            "packs/lotribbon-greetings-20260902-01/index.html",
            slot.DO_NOT_OVERWRITE,
        )
        self.assertIn(
            "packs/desk-website-service-20260902-01/waitlist-slot.md",
            slot.DO_NOT_OVERWRITE,
        )
        self.assertIn("packs/sidewalk-signal-web-desk-20260902-01", slot.DO_NOT_OVERWRITE)
        self.assertIn("packs/curbline-weekend-yard-help-20260902-01", slot.DO_NOT_OVERWRITE)
        self.assertIn("ground/BUSINESS_PACKS.json", slot.DO_NOT_OVERWRITE)

    def test_lotribbon_instance_stays_pointer_only(self) -> None:
        if not slot.LOTRIBBON.is_file():
            self.skipTest("LotRibbon waitlist-slot sheet not in this tree")
        result = slot.classify_path(slot.LOTRIBBON)
        text = slot.LOTRIBBON.read_text(encoding="utf-8")
        self.assertEqual(result["verdict"], "LOTRIBBON_WAITLIST_SLOT_INSTANCE_OK")
        self.assertIn("LotRibbon Greetings", text)
        self.assertIn("packs/waitlist.html", text)
        self.assertIn("cursor-pack-door-waitlist-20260902-01", text)
        self.assertIn("NOT_MINTED", text)
        self.assertIn("7804ec33", text)
        self.assertIn("Zero sends", text)
        self.assertNotIn("buy.stripe.com", text.lower())
        self.assertTrue(result["empty_public_addresses"])
        self.assertEqual(result["sends"], 0)

    def test_invented_address_fails(self) -> None:
        path = Path("/tmp/lotribbon-waitlist-slot-invented.md")
        path.write_text(INVENTED, encoding="utf-8")
        result = slot.classify_path(path)
        self.assertEqual(result["verdict"], "WAITLIST_ADDRESS_LEAKED")

    def test_invented_stripe_fails(self) -> None:
        path = Path("/tmp/lotribbon-waitlist-slot-stripe.md")
        path.write_text(STRIPED, encoding="utf-8")
        result = slot.classify_path(path)
        self.assertEqual(result["verdict"], "WAITLIST_LINK_INVENTED")

    def test_tree_ok_and_peers_unread(self) -> None:
        if not slot.TEMPLATE.is_file() or not slot.LOTRIBBON.is_file():
            self.skipTest("waitlist-slot files not in this tree")
        result = slot.classify_tree()
        self.assertEqual(result["verdict"], "LOTRIBBON_WAITLIST_SLOT_OK", msg=result)
        self.assertTrue(result["did_not_rewrite_goat_template"])
        self.assertTrue(result["did_not_remint_factory_slot"])
        self.assertTrue(result["did_not_overwrite_waitlist_html"])
        self.assertTrue(result["did_not_overwrite_lotribbon_door"])
        self.assertTrue(result["did_not_write_harborline_slot"])
        self.assertTrue(result["did_not_merge_7915"])
        self.assertEqual(result["blobs"]["packs/_template/waitlist-slot.md"], "50602561")
        self.assertEqual(result["blobs"]["packs/waitlist.html"], "bdcaa7ea")
        self.assertEqual(
            result["blobs"]["packs/lotribbon-greetings-20260902-01/index.html"],
            "7804ec33",
        )
        dumped = json.dumps(result)
        self.assertNotIn("337 NO", dumped)
        self.assertEqual(result["checkout"], "NOT_MINTED")

    def test_cli_json(self) -> None:
        if not slot.LOTRIBBON.is_file():
            self.skipTest("LotRibbon waitlist-slot sheet not in this tree")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "pack_lotribbon_waitlist_slot.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["verdict"], "LOTRIBBON_WAITLIST_SLOT_OK")
        self.assertIs(data["gate"], False)
        self.assertEqual(data["receipt_id"], "cursor-lead-lotribbon-waitlist-slot-20260902-01")


if __name__ == "__main__":
    unittest.main()
