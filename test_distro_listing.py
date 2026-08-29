#!/usr/bin/env python3
"""Muhlnickel DISTRO sales listing: page, catalog slot, White Box WB-RANGE line."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parent
STRIPE_URL_RE = re.compile(r"https://(?:buy|donate)\.stripe\.com/[A-Za-z0-9]+")
CANONICAL_STRIPE = [
    "https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08",
    "https://buy.stripe.com/3cIeVc5WB1MRgX7al443S03",
    "https://buy.stripe.com/3cIbJ0ckZgHL36h8cW43S04",
    "https://buy.stripe.com/bJe28qacR4Z3gX7bp843S05",
    "https://buy.stripe.com/3cIfZgacRezDfT39h043S06",
    "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
    "https://buy.stripe.com/7sYbJ02Kpcrv9uF0Ku43S09",
]


class DistroListing(unittest.TestCase):
    def test_sales_page_is_measured_and_does_not_publish_the_artifact(self):
        page = (ROOT / "distro.html").read_text(encoding="utf-8")
        self.assertIn("A computer you copy as a folder", page)
        self.assertIn("136,450", page)
        self.assertIn("7,611", page)
        self.assertIn("0 / 65536", page)
        self.assertIn("65536 / 65536", page)
        self.assertIn("129", page)
        self.assertIn("66", page)
        self.assertIn("8052b0ac17b70f0c68836ce1a12af26060b1a8f3ae03ff1588416ee601e5c0bc", page)
        self.assertIn("OWNER SLOT", page)
        self.assertIn("does not host, attach, or download the DISTRO artifact", page)
        self.assertIn("No login", page)
        self.assertIn("tokenjunkielabs@gmail.com", page)
        self.assertNotIn('type="password"', page)
        self.assertNotIn("required login", page.lower())
        self.assertNotRegex(page, r'href=["\'][^"\']+\.mno["\']')
        self.assertEqual(STRIPE_URL_RE.findall(page), [])

    def test_catalog_keeps_seven_stripe_urls_and_marks_owner_slot(self):
        catalog = (ROOT / "land" / "stripe-payment-links-20260826.md").read_text(encoding="utf-8")
        page = (ROOT / "stripe-payment-links-20260826.html").read_text(encoding="utf-8")
        self.assertEqual(STRIPE_URL_RE.findall(catalog), CANONICAL_STRIPE)
        self.assertEqual(STRIPE_URL_RE.findall(page), CANONICAL_STRIPE)
        self.assertIn("../distro.html", catalog)
        self.assertIn("OWNER SLOT", catalog)
        self.assertIn("./distro.html", page)
        self.assertIn("OWNER SLOT", page)
        self.assertNotIn("| distro |", catalog)
        self.assertNotIn("| muhlnickel-distro |", catalog)

    def test_white_box_pilot_copy_names_wb_range(self):
        html = (ROOT / "commercial.html").read_text(encoding="utf-8")
        self.assertIn(
            "WB-RANGE (PR #5317): stored weights read by address over HTTP Range, 14 KB fetched of 1.56 TB measured live.",
            html,
        )
        self.assertIn("./distro.html", html)

    def test_sitemap_lists_distro_page(self):
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn(
            "https://woahwhattheheck.github.io/commons/distro.html",
            sitemap,
        )


if __name__ == "__main__":
    unittest.main()
