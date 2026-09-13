from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "expertise.html"
FAMILIES = ROOT / "revenue" / "OFFERING_FAMILIES.md"
COMPILER_README = ROOT / "revenue" / "expertise_catalog" / "README.md"

EXPECTED_IDS = {
    "expertise-whitebox-hour",
    "expertise-agent-architecture-review",
    "expertise-failure-recovery-analysis",
    "expertise-computer-use-design-review",
    "expertise-reproducibility-review",
    "expertise-evidence-architecture-review",
    "expertise-carrier-resource-routing-review",
    "expertise-muhlnickel-titan-consultation",
}


class ExpertiseSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.families = FAMILIES.read_text(encoding="utf-8")
        cls.compiler = COMPILER_README.read_text(encoding="utf-8")

    def test_exact_eight_buyer_lanes_are_rendered_once(self):
        found = re.findall(r'data-expertise-id="([^"]+)"', self.html)
        self.assertEqual(set(found), EXPECTED_IDS)
        self.assertEqual(len(found), len(EXPECTED_IDS))

    def test_only_existing_whitebox_commerce_route_is_chargeable(self):
        self.assertEqual(self.html.count('href="./commerce.html#sku-whitebox-hour-20260826"'), 1)
        self.assertIn('$250 · one hour', self.html)
        self.assertNotIn('buy.stripe.com', self.html)
        self.assertNotIn('donate.stripe.com', self.html)

    def test_other_seven_lanes_are_quote_only(self):
        quote_routes = re.findall(r'href="mailto:tokenjunkielabs@gmail.com\?subject=[^"]+"', self.html)
        self.assertEqual(len(quote_routes), 7)
        self.assertIn('Seven additional expertise lanes are quote-only', self.html)

    def test_surface_points_to_landed_compiler_not_shadow_contract(self):
        self.assertIn('./revenue/expertise_catalog/README.md', self.html)
        self.assertNotIn('./revenue/expertise_catalog/catalog.json', self.html)
        self.assertNotIn('./revenue/expertise_catalog/catalog.schema.json', self.html)
        self.assertIn('compiler does not publish, contact buyers, create checkout, or recognize revenue', self.html)

    def test_offering_family_composes_surface_with_compiler(self):
        self.assertIn('[`expertise.html`](../expertise.html)', self.families)
        self.assertIn('[`revenue/expertise_catalog/`](./expertise_catalog/)', self.families)
        self.assertIn('other seven lanes remain quote-only', self.families)

    def test_landed_compiler_keeps_authority_ceiling(self):
        self.assertIn('## Authority ceiling', self.compiler)
        self.assertIn('never publishes a listing', self.compiler)
        self.assertIn('recognizes revenue', self.compiler)


if __name__ == "__main__":
    unittest.main()
