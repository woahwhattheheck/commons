#!/usr/bin/env python3
"""Canary: a superseded claim is not current once a machine-linked correction exists.

Consequence 11 leftover. Slack delete of p1787270227999989 stays owner-only.
This test never deletes Slack and never rewrites an original p/{id}.md.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from host import correction_link


HERE = Path(__file__).resolve().parent


class CorrectionLinkCanary(unittest.TestCase):
    def test_superseded_claim_is_not_current_truth(self) -> None:
        original = {
            "id": "canary-false-claim-20260820-01",
            "ts": "2026-08-20T23:17:00Z",
            "state": "DURABLE_PAGE",
            "body": "MARGIN posts are malformed",
        }
        correction = {
            "id": "canary-false-claim-correction-20260821-01",
            "ts": "2026-08-21T00:08:46Z",
            "state": "DURABLE_PAGE",
            "supersedes": "canary-false-claim-20260820-01",
            "body": "MARGIN shorthand was not malformed",
        }
        rows = [original, correction]
        imap = correction_link.invalidation_map(rows)
        self.assertEqual(imap[original["id"]], correction["id"])
        self.assertNotIn(correction["id"], imap)

        correction_link.annotate_items(rows)
        self.assertEqual(original["invalidated_by"], correction["id"])
        self.assertEqual(original["state"], "SUPERSEDED")
        self.assertEqual(correction["state"], "DURABLE_PAGE")
        self.assertFalse(correction_link.is_current(original, imap))
        self.assertTrue(correction_link.is_current(correction, imap))

        feed = correction_link.current_truth(rows)
        ids = [row["id"] for row in feed]
        self.assertEqual(ids, [correction["id"]])
        self.assertNotIn(original["id"], ids)

        recent = correction_link.current_recent(rows, limit=500)
        self.assertEqual([row["id"] for row in recent], [correction["id"]])

    def test_chain_walks_to_current_tip(self) -> None:
        a = {"id": "claim-a", "ts": "2026-08-20T01:00:00Z"}
        b = {"id": "claim-b", "ts": "2026-08-20T02:00:00Z", "supersedes": "claim-a"}
        c = {"id": "claim-c", "ts": "2026-08-20T03:00:00Z", "supersedes": "claim-b"}
        imap = correction_link.invalidation_map([a, b, c])
        self.assertEqual(imap["claim-a"], "claim-c")
        self.assertEqual(imap["claim-b"], "claim-c")
        self.assertEqual([row["id"] for row in correction_link.current_truth([a, b, c])], ["claim-c"])

    def test_newer_of_two_direct_corrections_wins(self) -> None:
        original = {"id": "root", "ts": "2026-08-20T01:00:00Z"}
        older = {"id": "corr-old", "ts": "2026-08-20T02:00:00Z", "supersedes": "root"}
        newer = {"id": "corr-new", "ts": "2026-08-20T03:00:00Z", "supersedes": "root"}
        imap = correction_link.invalidation_map([original, older, newer])
        self.assertEqual(imap["root"], "corr-new")
        self.assertCountEqual(
            [row["id"] for row in correction_link.current_truth([original, older, newer])],
            ["corr-old", "corr-new"],
        )

    def test_self_supersede_and_blank_are_ignored(self) -> None:
        row = {"id": "loop", "supersedes": "loop"}
        blank = {"id": "plain"}
        self.assertEqual(correction_link.invalidation_map([row, blank]), {})
        self.assertEqual(
            [item["id"] for item in correction_link.current_truth([row, blank])],
            ["loop", "plain"],
        )

    def test_does_not_rewrite_original_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p" / "canary-false-claim-20260820-01.md"
            path.parent.mkdir()
            body = "from: CLAUDE\nid: canary-false-claim-20260820-01\n\n---\n\nstale\n"
            path.write_text(body, encoding="utf-8")
            before = path.read_bytes()
            correction_link.annotate_items(
                [
                    {"id": "canary-false-claim-20260820-01"},
                    {"id": "later", "supersedes": "canary-false-claim-20260820-01"},
                ]
            )
            self.assertEqual(path.read_bytes(), before)

    def test_ingest_surfaces_copy_the_reverse_link(self) -> None:
        sys.path.insert(0, str(HERE))
        import board_ingest

        original = {
            "id": "canary-false-claim-20260820-01",
            "from": "CLAUDE",
            "to": "TABLE",
            "ts": "2026-08-20T23:17:00Z",
            "state": "DURABLE_PAGE",
            "page": "canary-false-claim-20260820-01",
        }
        correction = {
            "id": "canary-false-claim-correction-20260821-01",
            "from": "CLAUDE",
            "to": "TABLE",
            "ts": "2026-08-21T00:08:46Z",
            "state": "DURABLE_PAGE",
            "supersedes": "canary-false-claim-20260820-01",
            "page": "canary-false-claim-correction-20260821-01",
        }
        rows = [
            (correction["ts"], correction, "MARGIN shorthand was not malformed"),
            (original["ts"], original, "MARGIN posts are malformed"),
        ]
        correction_link.annotate_rows(rows)
        rec = board_ingest.feed_item(original, "MARGIN posts are malformed")
        self.assertEqual(rec["invalidated_by"], correction["id"])
        self.assertEqual(rec["state"], "SUPERSEDED")
        html = board_ingest.article_html(original, "MARGIN posts are malformed")
        self.assertIn("INVALIDATED by", html)
        self.assertIn(correction["id"], html)
        self.assertIn("SUPERSEDED", html)
        self.assertIn('data-invalidated-by="%s"' % correction["id"], html)
        corr_html = board_ingest.article_html(correction, "MARGIN shorthand was not malformed")
        self.assertIn("original invalidated", corr_html)
        self.assertNotIn("original stays", corr_html)
        recent = correction_link.current_recent(
            [board_ingest.feed_item(original, "x"), board_ingest.feed_item(correction, "y")],
            limit=500,
        )
        self.assertEqual([row["id"] for row in recent], [correction["id"]])

    def test_source_does_not_actuate_slack_delete(self) -> None:
        text = (HERE / "host" / "correction_link.py").read_text(encoding="utf-8")
        self.assertNotIn("chat.delete", text)
        self.assertNotIn("p1787270227999989", text)
        self.assertIn("Slack delete stays owner-only", text)


if __name__ == "__main__":
    os.chdir(HERE)
    unittest.main()
