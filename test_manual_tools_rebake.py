#!/usr/bin/env python3
"""Exercise the real manual/tools publishers across successive catalog bakes."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import board_ingest
import hub_pages
import manual_build


ROOT = Path(__file__).resolve().parent


class ManualToolsRebakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.catalog = json.loads((ROOT / "tools.json").read_text(encoding="utf-8"))
        self.state = {
            "open": [{"id": "rebake-open-job", "from": "HARBOR", "status": "OPEN", "tool": "sample-tool", "ts": "2026-09-07T03:00:00Z"}],
            "done": [{"id": "rebake-done-job", "from": "HARBOR", "status": "DONE", "tool": "sample-tool", "receipt": "rebake-receipt"}],
            "receipts": 1,
        }

    def write_inputs(self):
        (self.root / "tools.json").write_text(json.dumps(self.catalog), encoding="utf-8")
        (self.root / "share.json").write_text(json.dumps(self.state), encoding="utf-8")

    def bake_manual(self):
        self.write_inputs()
        target = self.root / "ground" / "MANUAL.md"
        with patch.object(manual_build, "ROOT", str(self.root)), patch.object(manual_build, "OUT", str(target)):
            self.assertEqual(manual_build.main(), 0)
        return target.read_text(encoding="utf-8")

    def bake_tools(self):
        self.write_inputs()
        with patch.object(board_ingest, "ROOT", str(self.root)):
            hub_pages.rebuild_tools(board_ingest, [], self.state)
            board_ingest.splice_tools_cash_doors()
        return (self.root / "tools.html").read_text(encoding="utf-8")

    def test_manual_rebuild_retains_product_job_and_mcp_links(self):
        first = self.bake_manual()
        self.assertEqual(self.bake_manual(), first)
        self.assertEqual(first.count("## Live cash"), 1)
        self.assertLess(first.index("## Live cash"), first.index("## File a job"))
        for door in self.catalog["cash"]["doors"]:
            self.assertIn("[%s](../%s)" % (door["label"], door["href"][2:]), first)
        self.assertIn("[tools-cash.html](../tools-cash.html)", first)
        job_section = first.split("## File a job", 1)[1].split("## Catalog", 1)[0]
        self.assertIn("Catalog job hook: [`job`](../tools.json)", job_section)
        self.assertIn("[Job door](../job.html)", job_section)
        self.assertIn(self.catalog["job"]["button"], job_section)
        self.assertIn("coil-tools-json-job-hook-20260905-01", job_section)
        self.assertIn(self.catalog["super_mcp"]["url"], first)
        self.assertIn("OPEN HARBOR [rebake-open-job]", first)
        self.assertNotIn("buy.stripe.com", first)

    def test_manual_next_bake_reads_changed_catalog_and_jobs(self):
        previous = self.bake_manual()
        self.catalog["cash"]["doors"] = [{"label": "Updated diagnostic", "href": "offers/updated.html"}]
        self.catalog["cash"]["shelf"] = "https://example.invalid/catalog"
        self.catalog["job"].update(door="new-job.html", button="python updated_job.py", to="UPDATED")
        self.state["open"] = []
        current = self.bake_manual()
        self.assertIn("[Updated diagnostic](../offers/updated.html)", current)
        self.assertIn("(https://example.invalid/catalog)", current)
        self.assertIn("[Job door](../new-job.html)", current)
        self.assertIn("PC button `python updated_job.py`, `to: UPDATED`", current)
        self.assertNotIn("$199 dealer diagnostic", current)
        self.assertNotIn("rebake-open-job", current)
        self.assertIn("None open.", current)
        self.assertNotEqual(previous, current)

    def test_tools_rebuild_retains_static_hooks_form_jobs_and_cash_splice(self):
        first = self.bake_tools()
        self.assertEqual(self.bake_tools(), first)
        for identity in ("job-hook", "super-mcp-hook", "cash-doors", "cash-hook", "digit-door", "job", "feed"):
            self.assertEqual(first.count('id="%s"' % identity), 1, identity)
        self.assertIn('href="./job.html">Job door</a>', first)
        self.assertIn('href="./wire.html"', first)
        self.assertIn(self.catalog["super_mcp"]["url"], first)
        self.assertIn(self.catalog["job"]["button"], first)
        self.assertIn("coil-tools-json-job-hook-20260905-01", first)
        self.assertIn('href="./tools-cash.html"', first)
        self.assertIn('data-to="TOOLS"', first)
        self.assertIn('name="tool" required', first)
        for identity in ("rebake-open-job", "rebake-done-job", "rebake-receipt"):
            self.assertIn('href="./p/%s.html"' % identity, first)
        self.assertIn('id="trust-through-proof"', first)

    def test_tools_next_bake_uses_catalog_values_as_escaped_text(self):
        self.bake_tools()
        self.catalog["job"].update(door='./new-job.html?label="A&B"', button="python updated_job.py --label 'A & B < C'", to="A&B")
        self.catalog["super_mcp"].update(url="https://example.invalid/mcp?a=1&b=2", door="https://example.invalid/guide?a=1&b=2")
        current = self.bake_tools()
        self.assertIn('href="./new-job.html?label=&quot;A&amp;B&quot;"', current)
        self.assertIn("python updated_job.py --label &#x27;A &amp; B &lt; C&#x27;", current)
        self.assertIn("<code>to: A&amp;B</code>", current)
        self.assertIn("<code>https://example.invalid/mcp?a=1&amp;b=2</code>", current)
        self.assertIn('href="https://example.invalid/guide?a=1&amp;b=2"', current)
        self.assertNotIn("commons-spark-mcp.vercel.app/mcp", current)

    def test_legacy_catalog_without_optional_metadata_still_renders(self):
        for key in ("cash", "job", "super_mcp"):
            self.catalog.pop(key, None)
        manual = self.bake_manual()
        tools = self.bake_tools()
        self.assertIn("## File a job", manual)
        self.assertIn("## Catalog", manual)
        self.assertIn("rebake-open-job", manual)
        self.assertNotIn("## Live cash", manual)
        self.assertNotIn("Catalog job hook", manual)
        self.assertNotIn('id="job-hook"', tools)
        self.assertNotIn('id="super-mcp-hook"', tools)
        self.assertIn('id="job"', tools)
        self.assertIn("rebake-open-job", tools)


if __name__ == "__main__":
    unittest.main()
