#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
import public_surface_isolation_guard as guard

REPO_URL = "https://github.com/woahwhattheheck/commons/tree/main/revenue/expertise_catalog"
PAGES_URL = "https://woahwhattheheck.github.io/commons/commerce.html"
RAW_URL = "https://raw.githubusercontent.com/woahwhattheheck/commons/main/README.md"
API_URL = "https://api.github.com/repos/woahwhattheheck/commons/contents/README.md"

class PublicSurfaceIsolationGuardTests(unittest.TestCase):
    def no_grants(self): return {}

    def test_root_storefront_rejects_repo_backlink(self):
        hits = guard.scan_text("expertise.html", f'<a href="{REPO_URL}">evidence</a>', self.no_grants())
        self.assertEqual([(h.line, h.url) for h in hits], [(1, REPO_URL)])

    def test_docs_rejects_pages_backlink(self):
        hits = guard.scan_text("docs/customer-guide.md", f"Open {PAGES_URL}.", self.no_grants())
        self.assertEqual(len(hits), 1); self.assertEqual(hits[0].url, PAGES_URL)

    def test_public_generated_rejects_raw_and_api_backlinks(self):
        hits = guard.scan_text("public/catalog.json", f'{{"source":"{RAW_URL}","api":"{API_URL}"}}', self.no_grants())
        self.assertEqual({h.url for h in hits}, {RAW_URL, API_URL})

    def test_relative_product_routes_and_plain_commons_text_are_allowed(self):
        text = '<a href="./commerce.html">Buy</a><p>Commons coordinates this work.</p>'
        self.assertEqual(guard.scan_text("commerce.html", text, self.no_grants()), [])

    def test_internal_receipt_can_keep_provenance(self):
        self.assertEqual(guard.scan_text("receipts/customer-delivery.md", f"source: {REPO_URL}\n", self.no_grants()), [])

    def test_tests_are_not_public_surfaces(self):
        self.assertFalse(guard.is_public_surface("tests/fixtures/storefront.html"))

    def test_nested_internal_revenue_markdown_is_not_swept(self):
        self.assertFalse(guard.is_public_surface("revenue/internal/ledger.md"))
        self.assertEqual(guard.scan_text("revenue/internal/ledger.md", f"receipt {REPO_URL}", self.no_grants()), [])

    def test_root_readme_is_public(self):
        self.assertTrue(guard.is_public_surface("README.md"))
        self.assertEqual(len(guard.scan_text("README.md", REPO_URL, self.no_grants())), 1)

    def test_public_directory_hints_cover_delivery_outreach_and_p(self):
        for path in ("deliverables/acme/README.md", "outreach/acme/proposal.md", "p/customer-proof.md"):
            with self.subTest(path=path): self.assertTrue(guard.is_public_surface(path))

    def test_exact_exception_is_scoped_to_path_and_url(self):
        grant = guard.ExceptionGrant("expertise.html", REPO_URL, "OWNER-APPROVED: bryce 2026-09-17 special case", "explicit surface-specific exception")
        grants = {(grant.path, grant.url): grant}
        self.assertEqual(guard.scan_text("expertise.html", REPO_URL, grants), [])
        self.assertEqual(len(guard.scan_text("commerce.html", REPO_URL, grants)), 1)
        self.assertEqual(len(guard.scan_text("expertise.html", PAGES_URL, grants)), 1)

    def test_manifest_requires_owner_approved_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "exceptions.json"
            path.write_text(json.dumps({"version":1,"exceptions":[{"path":"expertise.html","url":REPO_URL,"owner_approval":"reviewed by someone","reason":"not enough"}]}), encoding="utf-8")
            with self.assertRaises(guard.GuardError): guard.load_exceptions(path)

    def test_manifest_rejects_non_commons_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "exceptions.json"
            path.write_text(json.dumps({"version":1,"exceptions":[{"path":"expertise.html","url":"https://example.com/product","owner_approval":"OWNER-APPROVED: bryce","reason":"wrong host must not become an exemption"}]}), encoding="utf-8")
            with self.assertRaises(guard.GuardError): guard.load_exceptions(path)

if __name__ == "__main__":
    unittest.main()
