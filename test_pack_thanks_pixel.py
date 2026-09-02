#!/usr/bin/env python3
"""Thanks door: empty X Pixel slot loads no third-party scripts."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_thanks_pixel as thanks  # noqa: E402


class ThanksDoorTests(unittest.TestCase):
    def test_empty_slot_has_no_third_party_script_src(self) -> None:
        out = thanks.parse_thanks(ROOT / "packs" / "thanks.html")
        self.assertEqual(out["pixel_id"], "")
        self.assertEqual(out["third_party_scripts"], [])
        self.assertTrue(out["empty_slot_loads_no_third_party"])
        self.assertFalse(out["earnings_claim"])
        self.assertFalse(out["mint_pixel"])
        self.assertFalse(out["gate"])

    def test_static_html_has_no_script_src(self) -> None:
        html = (ROOT / "packs" / "thanks.html").read_text(encoding="utf-8")
        self.assertEqual(thanks.SCRIPT_SRC_RE.findall(html), [])

    def test_filled_slot_injector_is_first_party_until_runtime(self) -> None:
        html = (ROOT / "packs" / "thanks.html").read_text(encoding="utf-8")
        filled = thanks.filled_slot_would_purchase(html, 100)
        self.assertTrue(filled["injector_present"])
        self.assertEqual(filled["static_third_party_scripts"], [])
        self.assertFalse(filled["login_ask"])

    def test_checkout_template_names_after_payment_redirect(self) -> None:
        self.assertTrue(thanks.checkout_points_at_thanks(ROOT / "packs" / "_template" / "checkout.md"))

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "pack_thanks_pixel.py"), "--json"],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["empty_slot_loads_no_third_party"])
        self.assertTrue(payload["checkout_redirect"])

    def test_no_invented_stripe_url_on_thanks_door(self) -> None:
        html = (ROOT / "packs" / "thanks.html").read_text(encoding="utf-8")
        self.assertNotIn("buy.stripe.com", html)
        self.assertNotIn("donate.stripe.com", html)

    def test_land_doc_mentions_thanks_door(self) -> None:
        land = (ROOT / "land" / "pack-thanks-pixel-20260902.md").read_text(encoding="utf-8")
        self.assertIn("packs/thanks.html", land)
        self.assertIn("OWNER_PASTE", land)
        template = (ROOT / "land" / "business-pack-template-20260902.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("packs/thanks.html", template)
        self.assertIn("5c.", template)


if __name__ == "__main__":
    unittest.main()
