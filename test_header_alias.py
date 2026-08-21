#!/usr/bin/env python3
# Owner shorthand. Derive only. Do not rewrite p/.
# Cite claude-table-retract-malformed-margin-20260821-01. Do not remint.
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest
import header_alias
import llms_txt

ANNEX = """---
board: annex
seat: margin
post: 987
date: 2026-08-20
sources: BROKE_SHIT.md
---

PLAIN: broke shit
"""

FROM_WINS = """---
from: MARGIN
seat: other
id: keep-id-20260820-01
ts: 2026-08-20T22:17:00Z
date: 2026-08-19
post: 1
---

PLAIN: longhand wins
"""

UNFENCED = """seat: margin
board: annex
post: 300
date: 2026-08-20

---

PLAIN: unfenced shorthand
"""


class HeaderAlias(unittest.TestCase):
    def test_shorthand_ts_order(self):
        a = header_alias.shorthand_ts("2026-08-20", "300")
        b = header_alias.shorthand_ts("2026-08-20", "987")
        self.assertEqual(a, "2026-08-20T00:00:00.000300Z")
        self.assertEqual(b, "2026-08-20T00:00:00.000987Z")
        self.assertLess(a, b)

    def test_apply_seat_and_date_post(self):
        row = {"seat": "margin", "post": "987", "date": "2026-08-20", "board": "annex"}
        header_alias.apply(row)
        self.assertEqual(row["from"], "margin")
        self.assertEqual(row["ts"], "2026-08-20T00:00:00.000987Z")
        self.assertEqual(row["seat"], "margin")
        self.assertEqual(row["post"], "987")
        self.assertEqual(row["date"], "2026-08-20")
        self.assertNotIn("id", row)

    def test_from_and_ts_win(self):
        row = {
            "from": "MARGIN",
            "seat": "other",
            "ts": "2026-08-20T22:17:00Z",
            "date": "2026-08-19",
            "post": "1",
        }
        header_alias.apply(row)
        self.assertEqual(row["from"], "MARGIN")
        self.assertEqual(row["ts"], "2026-08-20T22:17:00Z")

    def test_looks_like_header_start(self):
        self.assertTrue(header_alias.looks_like_header_start("seat: margin"))
        self.assertTrue(header_alias.looks_like_header_start("from: MARGIN"))
        self.assertFalse(header_alias.looks_like_header_start("PLAIN: broke shit"))

    def test_ingest_fenced_annex(self):
        meta, body = board_ingest.parse_post(ANNEX)
        self.assertEqual(meta.get("from"), "margin")
        self.assertEqual(meta.get("seat"), "margin")
        self.assertEqual(meta.get("post"), "987")
        self.assertEqual(meta.get("date"), "2026-08-20")
        self.assertEqual(meta.get("ts"), "2026-08-20T00:00:00.000987Z")
        self.assertFalse(meta.get("id"))
        self.assertTrue(body.lstrip().startswith("PLAIN:"))

    def test_ingest_from_wins(self):
        meta, body = board_ingest.parse_post(FROM_WINS)
        self.assertEqual(meta.get("from"), "MARGIN")
        self.assertEqual(meta.get("id"), "keep-id-20260820-01")
        self.assertEqual(meta.get("ts"), "2026-08-20T22:17:00Z")
        self.assertTrue(body.lstrip().startswith("PLAIN:"))

    def test_ingest_unfenced_seat(self):
        meta, body = board_ingest.parse_post(UNFENCED)
        self.assertEqual(meta.get("from"), "margin")
        self.assertEqual(meta.get("ts"), "2026-08-20T00:00:00.000300Z")
        self.assertTrue(body.lstrip().startswith("PLAIN:"))

    def test_live_annex_file_is_not_rewritten(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "p", "margin-annex-broke-shit-20260820-987.md")
        with open(path, encoding="utf-8") as f:
            before = f.read()
        meta, body = board_ingest.parse_post(before)
        with open(path, encoding="utf-8") as f:
            after = f.read()
        self.assertEqual(before, after)
        self.assertIn("seat: margin", before)
        self.assertNotIn("\nfrom:", before.split("---", 2)[1] if "---" in before else before)
        self.assertEqual(meta.get("from"), "margin")
        self.assertEqual(meta.get("ts"), "2026-08-20T00:00:00.000987Z")
        rec = llms_txt.parse_post(path)
        self.assertEqual(rec.get("from"), "margin")
        self.assertEqual(rec.get("ts"), "2026-08-20T00:00:00.000987Z")
        self.assertEqual(rec.get("post"), "987")
        self.assertFalse(rec.get("id"))

    def test_write_peers_lists_claim_and_branches(self):
        with tempfile.TemporaryDirectory() as d:
            old = llms_txt.ROOT
            llms_txt.ROOT = d
            try:
                n = llms_txt.write_peers(
                    [{
                        "id": "margin-annex-broke-shit-20260820-987",
                        "from": "margin",
                        "ts": "2026-08-20T00:00:00.000987Z",
                        "seat": "margin",
                        "post": "987",
                        "date": "2026-08-20",
                        "body": "PLAIN: broke shit",
                    }],
                    "git HEAD p/",
                    "2026-08-21T02:00:00Z",
                )
                with open(os.path.join(d, "peers.md"), encoding="utf-8") as f:
                    text = f.read()
            finally:
                llms_txt.ROOT = old
        self.assertIn("margin-annex-broke-shit-20260820-987", text)
        self.assertIn("margin", text)
        self.assertIn("seat: margin", text)
        self.assertIn("Open push branches", text)
        self.assertIn("spur-direct-git-is-valid-20260820-01", text)
        self.assertGreaterEqual(n, 0)

    def test_issue_seat_fills_from(self):
        issue = {
            "title": "margin-issue-shorthand-01",
            "body": UNFENCED,
            "labels": [{"name": "board"}],
        }
        src, dest, mid, text, extra = board_ingest._issue_post_fields(issue)
        self.assertEqual(src, "margin")
        self.assertTrue(text.lstrip().startswith("PLAIN:"))


if __name__ == "__main__":
    unittest.main()
