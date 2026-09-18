#!/usr/bin/env python3
"""Hermetic: harness capabilities include post-verify with append_post."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]


class CoilHarnessCapabilitiesPostVerifyTest(unittest.TestCase):
    def test_post_verify(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        caps = json.loads(path.read_text(encoding="utf-8"))["capabilities"]
        cap = next((c for c in caps if c.get("id") == "post-verify"), None)
        self.assertIsNotNone(cap)
        tools = cap.get("public_mcp_tools") or []
        self.assertIn("append_post", tools)
        self.assertIn("verify_durability", tools)
        html = cap.get("html") or []
        self.assertTrue(any("action.html" in h or "post.html" in h for h in html))


if __name__ == "__main__":
    unittest.main()
