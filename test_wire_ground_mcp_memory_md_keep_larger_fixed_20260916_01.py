"""wire-ground-mcp-memory-md-keep-larger-fixed-20260916-01"""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PAGES=(
 "ground/MCP_WAKE.md","ground/MCP_WAKE_JOB.md","ground/MEMORY_SHIP.md","ground/MEMORY_VISIBLE.md",
 "ground/SESSION_MEMORY.md","ground/PAYMENT_READY.md","ground/RENDER_CHECK.md","ground/STRICT_RECEIPT.md",
 "ground/WATCHDOG_HEAD_PROOF.md","ground/WEBMCP.md",
)
class T(unittest.TestCase):
 def test_batch(self):
  for rel in PAGES:
   text=(ROOT/rel).read_text(encoding="utf-8")
   self.assertIn("Larger fixed engagements", text, rel)
   self.assertIn("../diagnostic.html", text, rel)
   self.assertIn("../commercial.html", text, rel)
 def test_products(self):
  for n in ("diagnostic.html","commercial.html"):
   self.assertTrue((ROOT/n).is_file(), n)
if __name__=="__main__":
 unittest.main()
