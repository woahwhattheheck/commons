#!/usr/bin/env python3
"""Harborline maps through TALLY helper checks. Does not steal peer paths."""
from __future__ import annotations

import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import harborline_tally_pack_map as pack_map  # noqa: E402


DOOR = textwrap.dedent(
    """\
    <!DOCTYPE html><html lang=\"en\"><head><title>Harborline Local Sites</title></head>
    <body>
    <p>This instance of the desk pack is $200.</p>
    <p>Checkout slot: OWNER_PASTE_REQUIRED — no Payment Link minted.</p>
    <p>Join the pack waitlist: <a href=\"../waitlist.html\">packs/waitlist.html</a>.</p>
    </body></html>
    """
)

INSTANCE = {
    "brand": "Harborline Local Sites",
    "door": "packs/desk-website-service-20260902-01/door.html",
    "unique_instance_sell": True,
    "checkout": "OWNER_PASTE_REQUIRED",
    "ftc_437_customers_included": False,
    "agents_spend_ads": False,
}

CHECKOUT = textwrap.dedent(
    """\
    status: NOT_MINTED
    Owner pastes live Payment Link.
    """
)

TERMS = textwrap.dedent(
    """\
    tjlabs_profit_share_percent: OWNER_UNSET
    tjlabs_partial_ownership_fraction: OWNER_UNSET
    owner_pasted: false
    counsel_cleared: false
    """
)


class HarborlineTallyPackMapTest(unittest.TestCase):
    def test_does_not_claim_tally_or_waitlist_paths(self) -> None:
        self.assertIn("host/business_pack_desk_instance.py", pack_map.DO_NOT_OVERWRITE)
        self.assertIn("packs/sidewalk-signal-web-desk-20260902-01", pack_map.DO_NOT_OVERWRITE)
        self.assertIn("packs/desk-website-service-20260902-01/door.html", pack_map.DO_NOT_OVERWRITE)
        self.assertIn("packs/waitlist.html", pack_map.DO_NOT_OVERWRITE)
        self.assertIn("host/harborline_desk_compose.py", pack_map.DO_NOT_OVERWRITE)

    def test_missing_peer_does_not_invent_tally_files(self) -> None:
        missing = Path("/tmp/does-not-exist-business_pack_desk_instance.py")
        result = pack_map.map_pack(peer_path=missing, pack_dir=Path("/tmp"))
        self.assertEqual(result["verdict"], "PACK_MAP_PEER_MISSING")
        self.assertFalse(result["peer_helper_present"])
        self.assertTrue(result["layout"]["did_not_call_peer_verify"])
        self.assertEqual(result["shared_helper_single_owner"], "tally")
        self.assertNotIn("337 NO", json.dumps(result))

    def test_fixture_maps_copy_sell_waitlist_and_empty_checkout(self) -> None:
        if not pack_map.PEER_HELPER.is_file():
            self.skipTest("TALLY helper not in this tree")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "door.html").write_text(DOOR, encoding="utf-8")
            (folder / "instance.json").write_text(json.dumps(INSTANCE), encoding="utf-8")
            (folder / "checkout.md").write_text(CHECKOUT, encoding="utf-8")
            (folder / "offer.md").write_text("Harborline Local Sites. Pack price $200.\n", encoding="utf-8")
            (folder / "terms.md").write_text(TERMS, encoding="utf-8")
            result = pack_map.map_pack(pack_dir=folder)
        self.assertEqual(result["errors"], [], msg=result)
        self.assertEqual(result["verdict"], "PACK_MAP_OK")
        self.assertEqual(result["sell_instance_verdict"], "UNIQUE_INSTANCE_SELL_OK")
        self.assertTrue(result["waitlist_href"])
        self.assertFalse(result["waitlist_form_on_harborline"])
        self.assertTrue(result["layout"]["did_not_call_peer_verify"])
        self.assertEqual(result["checkout"], "NOT_MINTED")
        self.assertEqual(result["copy_verdicts"].get("door.html"), "COPY_OK")

    def test_earnings_copy_fails_closed(self) -> None:
        if not pack_map.PEER_HELPER.is_file():
            self.skipTest("TALLY helper not in this tree")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "door.html").write_text(DOOR, encoding="utf-8")
            (folder / "instance.json").write_text(json.dumps(INSTANCE), encoding="utf-8")
            (folder / "checkout.md").write_text(CHECKOUT, encoding="utf-8")
            (folder / "offer.md").write_text("make $500 this weekend\n", encoding="utf-8")
            (folder / "terms.md").write_text(TERMS, encoding="utf-8")
            result = pack_map.map_pack(pack_dir=folder)
        self.assertEqual(result["verdict"], "PACK_MAP_ERROR")
        self.assertTrue(any("EARNINGS_CLAIM" in err for err in result["errors"]))

    def test_form_on_harborline_fails_closed(self) -> None:
        if not pack_map.PEER_HELPER.is_file():
            self.skipTest("TALLY helper not in this tree")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            bad = DOOR.replace("</body>", '<form action="/waitlist"></form></body>')
            (folder / "door.html").write_text(bad, encoding="utf-8")
            (folder / "instance.json").write_text(json.dumps(INSTANCE), encoding="utf-8")
            (folder / "checkout.md").write_text(CHECKOUT, encoding="utf-8")
            (folder / "terms.md").write_text(TERMS, encoding="utf-8")
            result = pack_map.map_pack(pack_dir=folder)
        self.assertEqual(result["verdict"], "PACK_MAP_ERROR")
        self.assertTrue(result["waitlist_form_on_harborline"])

    def test_live_harborline_when_present(self) -> None:
        door = pack_map.HARBORLINE / "door.html"
        if not pack_map.PEER_HELPER.is_file() or not door.is_file():
            self.skipTest("peer helper or Harborline instance not in this tree")
        result = pack_map.map_pack()
        self.assertEqual(result["errors"], [], msg=result)
        self.assertEqual(result["verdict"], "PACK_MAP_OK")
        self.assertTrue(result["waitlist_href"])
        self.assertFalse(result["waitlist_form_on_harborline"])
        self.assertTrue(result["did_not_overwrite_peer"])
        self.assertTrue(result["did_not_remint_harborline_instance"])
        self.assertTrue(result["layout"]["did_not_call_peer_verify"])


if __name__ == "__main__":
    unittest.main()
