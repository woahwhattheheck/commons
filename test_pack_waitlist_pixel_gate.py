#!/usr/bin/env python3
"""CCPA pixel gate compose. Does not steal waitlist or thanks doors."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_waitlist_pixel_gate as gate  # noqa: E402


FILLED = {"x": "px-test", "tiktok": "", "meta": ""}


class WaitlistPixelGateTest(unittest.TestCase):
    def test_does_not_claim_peer_doors(self) -> None:
        self.assertIn("packs/waitlist.html", gate.DO_NOT_OVERWRITE)
        self.assertIn("packs/thanks.html", gate.DO_NOT_OVERWRITE)
        self.assertIn("host/pack_waitlist.py", gate.DO_NOT_OVERWRITE)
        self.assertIn("host/pack_thanks_pixel.py", gate.DO_NOT_OVERWRITE)
        self.assertIn("packs/lotribbon-greetings-20260902-01", gate.DO_NOT_OVERWRITE)
        self.assertIn("host/harborline_tally_pack_map.py", gate.DO_NOT_OVERWRITE)

    def test_missing_helpers_do_not_invent_files(self) -> None:
        result = gate.gate(
            waitlist_path=Path("/tmp/missing-pack_waitlist.py"),
            thanks_path=Path("/tmp/missing-pack_thanks_pixel.py"),
        )
        self.assertEqual(result["verdict"], "PIXEL_GATE_HELPER_MISSING")
        self.assertEqual(result["purchases"], [])
        self.assertEqual(result["sends"], 0)
        self.assertNotIn("337 NO", json.dumps(result))

    def test_empty_slots_load_nothing(self) -> None:
        if not gate.WAITLIST_HELPER.is_file() or not gate.THANKS_HELPER.is_file():
            self.skipTest("waitlist or thanks helper not in this tree")
        result = gate.gate(ccpa_do_not_sell=False, overrides={"x": "", "tiktok": "", "meta": ""})
        self.assertEqual(result["verdict"], "PIXEL_GATE_BLOCKED")
        self.assertEqual(result["purchases"], [])
        self.assertEqual(result["would_load_script"], [])
        self.assertEqual(result["sends"], 0)

    def test_ccpa_blocks_even_when_ids_are_pasted(self) -> None:
        if not gate.WAITLIST_HELPER.is_file() or not gate.THANKS_HELPER.is_file():
            self.skipTest("waitlist or thanks helper not in this tree")
        result = gate.gate(ccpa_do_not_sell=True, overrides=FILLED, value="200")
        self.assertEqual(result["verdict"], "PIXEL_GATE_BLOCKED")
        self.assertFalse(result["pixel_allowed"])
        self.assertEqual(result["purchases"], [])
        self.assertEqual(result["would_load_script"], [])
        self.assertNotIn("@", json.dumps(result))

    def test_filled_without_opt_out_fires_one_purchase(self) -> None:
        if not gate.WAITLIST_HELPER.is_file() or not gate.THANKS_HELPER.is_file():
            self.skipTest("waitlist or thanks helper not in this tree")
        result = gate.gate(ccpa_do_not_sell=False, overrides=FILLED, value="200")
        self.assertEqual(result["verdict"], "PIXEL_GATE_FIRE")
        self.assertEqual(result["purchase_count"], 1)
        self.assertEqual(result["purchases"][0]["channel"], "x")
        self.assertEqual(result["purchases"][0]["value"], 200.0)
        self.assertEqual(result["sends"], 0)

    def test_jsonl_opt_out_blocks_without_leaking_email(self) -> None:
        if not gate.WAITLIST_HELPER.is_file() or not gate.THANKS_HELPER.is_file():
            self.skipTest("waitlist or thanks helper not in this tree")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signups.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "kind": "opt_out",
                        "email": "person@example.com",
                        "ccpa_do_not_sell": True,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            result = gate.gate(
                email="person@example.com",
                jsonl_path=path,
                overrides=FILLED,
                value="200",
            )
        self.assertEqual(result["verdict"], "PIXEL_GATE_BLOCKED")
        self.assertTrue(result["ccpa_do_not_sell"])
        dumped = json.dumps(result)
        self.assertNotIn("@", dumped)
        self.assertNotIn("person", dumped)


if __name__ == "__main__":
    unittest.main()
