#!/usr/bin/env python3
"""Every LIVE SKU checkout must agree with the public Payment Links table."""
import os
import re
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(ROOT, "land", "stripe-payment-links-20260826.md")
SKUS = {
    "tip": "sku-tip-20260826.md",
    "seat": "sku-seat-20260826.md",
    "unlock": "sku-unlock-20260826.md",
    "monthly-tip": "sku-monthly-tip-20260826.md",
    "boost": "sku-boost-20260826.md",
    "whitebox-hour": "sku-whitebox-hour-20260826.md",
    "muhlnickel-titan": "sku-muhlnickel-titan-20260826.md",
}


def field(text, name):
    match = re.search(rf"(?m)^{re.escape(name)}:\s*(\S+)\s*$", text)
    return match.group(1) if match else ""


def catalog_rows(text):
    rows = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 4 or cells[0] in {"sku", "---"}:
            continue
        rows[cells[0]] = cells[3]
    return rows


class StripePaymentLinks(unittest.TestCase):
    def test_live_skus_match_catalog_exactly(self):
        with open(CATALOG, encoding="utf-8") as handle:
            rows = catalog_rows(handle.read())
        self.assertEqual(set(rows), set(SKUS))

        for slug, filename in SKUS.items():
            path = os.path.join(ROOT, "land", filename)
            with open(path, encoding="utf-8") as handle:
                sku = handle.read()
            self.assertEqual(field(sku, "status"), "LIVE", slug)
            checkout = field(sku, "checkout")
            self.assertRegex(
                checkout,
                r"^https://(?:buy|donate)\.stripe\.com/[A-Za-z0-9]+$",
                slug,
            )
            self.assertEqual(rows[slug], checkout, slug)
            self.assertNotIn("NOT_MINTED", rows[slug], slug)


if __name__ == "__main__":
    unittest.main()
