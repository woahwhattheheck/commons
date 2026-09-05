"""The pay-page Autopsy offer reaches the existing catalog-backed checkout."""
from html.parser import HTMLParser
from pathlib import Path
import json
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
SKU = "agent-failure-autopsy-29"


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class PayAutopsyFunnelTests(unittest.TestCase):
    def test_offer_uses_the_existing_checkout_renderer(self):
        html = (ROOT / "pay.html").read_text(encoding="utf-8")
        tags = Tags(html).tags
        slots = [attrs for _, attrs in tags
                 if attrs.get("data-sku") == SKU
                 and "js-checkout-slot" in attrs.get("class", "").split()]
        self.assertEqual(len(slots), 1)
        self.assertTrue(any(tag == "script" and attrs.get("src", "").split("?")[0] == "./pay.js"
                            for tag, attrs in tags))
        self.assertTrue(any(tag == "a" and attrs.get("href") == "./agent-rescue.html"
                            for tag, attrs in tags))
        self.assertIn("$29", html)
        self.assertIn("usable, in-cap evidence", html)

    def test_catalog_slot_resolves_to_the_existing_product_checkout(self):
        catalog = json.loads((ROOT / "revenue/outcome_commerce/catalog.json").read_text(encoding="utf-8"))
        matches = [row for row in catalog["listings"] if row["id"] == SKU]
        self.assertEqual(len(matches), 1)
        listing = matches[0]
        self.assertEqual(listing["routes"]["human"], "agent-rescue.html")
        self.assertEqual(listing["checkout"]["status"], "ACTIVE_CHARGEABLE")
        self.assertEqual(catalog["funnels"][SKU]["readiness"], "READY_FOR_CHECKOUT")
        product = Tags((ROOT / "agent-rescue.html").read_text(encoding="utf-8")).tags
        hrefs = [attrs["href"] for tag, attrs in product if tag == "a" and "data-checkout" in attrs]
        checkout = urlsplit(listing["checkout"]["url"])
        self.assertTrue(any(urlsplit(href)._replace(query="", fragment="") == checkout
                            for href in hrefs))


if __name__ == "__main__":
    unittest.main()
