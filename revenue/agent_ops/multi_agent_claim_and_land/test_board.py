#!/usr/bin/env python3
"""Tests for the gap-free board index.

The properties that matter are not "does it parse" but: does it refuse to
overstate what it knows, and does the watermark actually advance monotonically
so successive passes stay continuous.
"""
import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load_board(root):
    spec = importlib.util.spec_from_file_location(
        "board_under_test", os.path.join(HERE, "board.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT = root
    mod.LOG = os.path.join(root, "board_log.jsonl")
    mod.MARK = os.path.join(root, "board_watermark.json")
    return mod


class BoardIndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.b = load_board(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _entry(self, ts, text, seat="SEAT-A"):
        e = {"ts": ts, "when": "2026-09-19 10:00:00 EDT", "seat": seat, "text": text}
        e["orders"] = [f"{int(o):03d}" for o in self.b.ORDER_RE.findall(text)]
        e["acts"] = self.b.classify(text)
        return e

    def test_watermark_starts_at_zero(self):
        self.assertEqual(self.b.watermark(), "0")

    def test_watermark_advances_to_newest(self):
        self.b.append([self._entry("100.1", "x"), self._entry("300.5", "y"),
                       self._entry("200.2", "z")])
        self.assertEqual(self.b.watermark(), "300.5")

    def test_watermark_never_goes_backward(self):
        # A later pass that only sees older messages must not rewind the
        # offset -- rewinding would re-open a gap that was already closed.
        self.b.append([self._entry("300.5", "y")])
        self.b.append([self._entry("100.1", "older")])
        self.assertEqual(self.b.watermark(), "300.5")

    def test_duplicate_timestamps_are_not_double_indexed(self):
        # Overlapping pages are expected -- the reader deliberately re-reads
        # the boundary to guarantee continuity, so dedupe must hold.
        e = self._entry("100.1", "UIOWA-115 taking this")
        self.b.append([e])
        self.b.append([e])
        self.assertEqual(len(self.b.load()), 1)

    def test_claim_is_detected_across_phrasings(self):
        for phrasing in ("TAKE UIOWA-115", "I'm on UIOWA-115",
                         "claiming UIOWA-115", "picking up UIOWA-115"):
            self.assertIn("claim", self.b.classify(phrasing), phrasing)

    def test_yield_is_not_mistaken_for_a_claim_only(self):
        acts = self.b.classify("yielding UIOWA-131, not racing a duplicate")
        self.assertIn("yield", acts)

    def test_order_ids_are_zero_padded_consistently(self):
        e = self._entry("100.1", "UIOWA-92 and UIOWA-092 and UIOWA-115")
        self.assertEqual(sorted(set(e["orders"])), ["092", "115"])

    def test_unindexed_order_is_reported_as_unknown_not_free(self):
        # The expensive error is calling an order unclaimed because the index
        # is merely silent about it.
        self.b.append([self._entry("100.1", "UIOWA-115 taking this")])
        self.assertEqual(self.b.order_view(999), 1)

    def test_torn_final_line_does_not_break_the_index(self):
        self.b.append([self._entry("100.1", "UIOWA-115 taking this")])
        with open(self.b.LOG, "a") as f:
            f.write('{"ts": "200.0", "tex')  # crashed mid-write
        self.assertEqual(len(self.b.load()), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
