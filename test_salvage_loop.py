#!/usr/bin/env python3
import json
import os
import tempfile
import unittest
from pathlib import Path

import board_ingest
import salvage_loop


class BoardAdapter:
    META_KEYS = board_ingest.META_KEYS
    ID_OK = board_ingest.ID_OK
    as_from = staticmethod(board_ingest.as_from)
    as_to = staticmethod(board_ingest.as_to)
    slug_id = staticmethod(board_ingest.slug_id)
    ntfy_envelope = staticmethod(board_ingest.ntfy_envelope)

    def __init__(self, root):
        self.root = Path(root)
        self.writes = []

    def write_post(self, src, dest, ident, body, ts=None, extra=None, event_id=None):
        self.writes.append((src, dest, ident, body, ts, extra, event_id))
        p = self.root / "p" / (ident + ".md")
        p.parent.mkdir(exist_ok=True)
        p.write_text(body, encoding="utf-8")
        return "wrote"


class SalvageLoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.board = BoardAdapter(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, rows):
        (self.root / "rejects.json").write_text(json.dumps(rows), encoding="utf-8")

    def test_repairs_fenced_json_and_is_idempotent(self):
        self.put([{
            "id": "broken-envelope-01", "state": "INGEST_ERROR",
            "reason": "unparseable", "event_id": "evt1", "ts": "2026-08-24T18:00:00Z",
            "raw": "```json\n{'from':'GEMINI','to':'TABLE','id':'gemini-repaired-post-01','body':'work survived'}\n```",
        }])
        first = salvage_loop.sweep(str(self.root), self.board)
        original = (self.root / "rejects.json").read_text(encoding="utf-8")
        second = salvage_loop.sweep(str(self.root), self.board)
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(len(self.board.writes), 1)
        self.assertEqual(self.board.writes[0][2:4], ("gemini-repaired-post-01", "work survived"))
        self.assertEqual(self.board.writes[0][5]["carrier"], "salvage-loop")
        self.assertEqual((self.root / "rejects.json").read_text(encoding="utf-8"), original)
        receipt = json.loads((self.root / "salvage" / "receipts.json").read_text(encoding="utf-8"))[0]
        self.assertIn("'body':'work survived'", receipt["source_raw"])

    def test_mints_stable_id_for_bad_or_missing_id(self):
        row = {"id": "bad", "state": "INGEST_ERROR", "reason": "bad-id",
               "raw": '{"from":"PEER","body":"still useful"}'}
        env = salvage_loop.repair(row, self.board)
        self.assertTrue(env["id"].startswith("salvage-"))
        self.assertEqual(env["id"], salvage_loop.repair(row, self.board)["id"])

    def test_never_salvages_snippets_conflicts_empty_or_push_failures(self):
        rows = [
            {"id": "snippet-only", "state": "INGEST_ERROR", "reason": "schema", "body": "partial"},
            {"id": "conflict-01", "state": "QUARANTINED_CONFLICT", "raw": '{"body":"x"}'},
            {"id": "push-fail-01", "state": "PUSH_FAIL", "raw": '{"body":"x"}'},
            {"id": "empty-post-01", "state": "INGEST_ERROR", "raw": '{"body":""}'},
        ]
        self.put(rows)
        self.assertEqual(salvage_loop.sweep(str(self.root), self.board), [])
        self.assertEqual(self.board.writes, [])
        self.assertFalse((self.root / "salvage" / "receipts.json").exists())

    def test_skips_tos_and_ntfy_file_notices(self):
        rows = [
            {"id": "tos-honest-01", "state": "INGEST_ERROR", "reason": "tos-honest",
             "raw": '{"from":"PEER","body":"challenge the owner"}'},
            {"id": "file-notice-01", "state": "INGEST_ERROR", "reason": "unparseable",
             "raw": "You received a file: attachment.json"},
        ]
        self.put(rows)
        self.assertEqual(salvage_loop.sweep(str(self.root), self.board), [])
        self.assertEqual(self.board.writes, [])

    def test_repairs_trailing_comma_json_and_from_equals_markdown(self):
        self.put([
            {
                "id": "comma-json-01", "state": "INGEST_ERROR", "reason": "unparseable",
                "raw": '{"from":"GEMINI","to":"TABLE","id":"gemini-salvage-comma-01","body":"repaired json",}',
            },
            {
                "id": "md-eq-01", "state": "INGEST_ERROR", "reason": "unparseable",
                "raw": "from=RIVET\nto=TABLE\nid=rivet-salvage-md-01\n\nPLAIN: markdown equals headers.\n",
            },
        ])
        added = salvage_loop.sweep(str(self.root), self.board)
        ids = {row["repaired_id"] for row in added}
        bodies = {w[3] for w in self.board.writes}
        self.assertEqual(ids, {"gemini-salvage-comma-01", "rivet-salvage-md-01"})
        self.assertTrue(any("repaired json" in b for b in bodies))
        self.assertTrue(any("markdown equals headers" in b for b in bodies))


if __name__ == "__main__":
    unittest.main()
