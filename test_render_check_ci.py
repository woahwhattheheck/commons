#!/usr/bin/env python3
"""render_check leftover is a CI wire, not a Chromium success story."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from render_check_ci import (
    REQUIRED_PAGES,
    WORKFLOW,
    classify,
    measure_root,
    parse_workflow,
)


class TestRenderCheckCi(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_missing_pages_stay_not_landed(self):
        measured = parse_workflow("python3 render_check.py board.html\nplaywright\nupload-artifact\n")
        self.assertEqual(measured["page_count"], 0)
        self.assertTrue(measured["has_tool"])
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("8bit.html", verdict["note"])

    def test_wired_gate_is_integrated(self):
        body = (
            "python3 render_check.py 8bit.html 8walk.html pixel.html visual.html "
            "--receipt receipts/render\n"
            "playwright install --with-deps chromium\n"
            "uses: actions/upload-artifact@v4\n"
            "workflow_dispatch:\n"
        )
        measured = parse_workflow(body)
        self.assertEqual(measured["page_count"], 4)
        self.assertEqual(measured["pages"], list(REQUIRED_PAGES))
        self.assertTrue(measured["has_receipt"])
        self.assertTrue(measured["has_playwright"])
        self.assertTrue(measured["has_workflow_dispatch"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("Chromium receipts", verdict["note"])

    def test_live_workflow_is_the_gate(self):
        measured = measure_root(ROOT)
        self.assertTrue(measured["measured"])
        self.assertTrue(measured["present"])
        self.assertEqual(measured["workflow"], WORKFLOW)
        self.assertEqual(measured["page_count"], 4)
        self.assertTrue(measured["has_tool"])
        self.assertTrue(measured["has_playwright"])
        self.assertTrue(measured["has_receipt"])
        self.assertEqual(classify(measured)["state"], "INTEGRATED")
        workflow_path = os.path.join(ROOT, WORKFLOW)
        with open(workflow_path, "r", encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("render_check.py 8bit.html 8walk.html pixel.html visual.html", text)
        self.assertIn("upload-artifact", text)
        checker = os.path.join(ROOT, "render_check.py")
        with open(checker, "r", encoding="utf-8") as handle:
            tool = handle.read()
        self.assertIn("--receipt", tool)
        self.assertIn("ThreadingMixIn", tool)
        self.assertIn("BrokenPipeError", tool)


if __name__ == "__main__":
    unittest.main()
