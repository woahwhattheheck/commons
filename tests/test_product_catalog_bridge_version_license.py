import unittest

from revenue.product_catalog_bridge.bridge import compile_catalog_bridge
from tests.test_product_catalog_bridge import AS_OF, E64, fixture


class ProductCatalogBridgeVersionLicenseTests(unittest.TestCase):
    def test_listing_version_mismatch_holds(self):
        raw = fixture()
        raw["listings"][0]["version"] = "1.4.6"
        receipt = compile_catalog_bridge(raw, as_of=AS_OF)
        self.assertIn("LISTING_VERSION_MISMATCH", {x["code"] for x in receipt["holds"]})

    def test_receipt_exposes_license_evidence_digest(self):
        receipt = compile_catalog_bridge(fixture(), as_of=AS_OF)
        artifact = next(x for x in receipt["artifacts"] if x["artifactId"] == "autopsy-cli")
        self.assertEqual(artifact["licenseEvidenceSha256"], E64)


if __name__ == "__main__":
    unittest.main()
