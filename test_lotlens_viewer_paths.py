#!/usr/bin/env python3
"""Hermetic checks for LotLens viewer what-column + path-summary display (FORGE)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "lotlens" / "app.html"


class LotLensViewerPathsTests(unittest.TestCase):
    def test_viewer_has_what_column_and_path_summary_helpers(self):
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn("<th>what</th>", html)
        self.assertIn("function nodeDetail", html)
        self.assertIn("function pathSummaryLines", html)
        self.assertIn('attrs.material', html)
        self.assertIn('attrs.supplier', html)
        self.assertIn('attrs.product', html)
        self.assertIn('attrs.customer', html)
        self.assertIn(" -\"+e.relation", html)  # from -relation-> to form
        self.assertIn("pathline", html)
        # Still a closed page: no remote script / fetch / storage.
        self.assertNotIn("<script src", html)
        self.assertNotIn("http://", html.replace("http-equiv", ""))
        self.assertNotIn("https://", html)
        self.assertNotIn("fetch(", html)
        self.assertNotIn("localStorage", html)
        self.assertIn('name="robots" content="index, follow"', html)


if __name__ == "__main__":
    unittest.main()
