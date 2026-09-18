#!/usr/bin/env python3
"""Vendor RUNBOOK.md is SOURCE_MANIFEST-pinned. Product cash stays on README."""
from __future__ import annotations
import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "revenue/agents_for_humans/vendor/autopsy/RUNBOOK.md"
README = ROOT / "revenue/agents_for_humans/README.md"
PIN = "66de6e3f2b5b65fe8bdb458ebd23200808aa0274"


def blob_id(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class T(unittest.TestCase):
    def test(self):
        self.assertEqual(blob_id(PAGE.read_bytes()), PIN)
        t = README.read_text(encoding="utf-8")
        self.assertIn("## Live cash", t)
        self.assertIn("dealer-service-lead-rescue.html", t)
        self.assertNotIn("buy.stripe.com", t)


if __name__ == "__main__":
    unittest.main()
