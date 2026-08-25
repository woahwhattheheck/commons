#!/usr/bin/env python3
"""Session export is a measurement, not a Slack yell."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from session_export import classify, measure_from_git_text


class TestSessionExport(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_dirty_is_not_landed(self):
        measured = measure_from_git_text(" M land.js\n?? host/session_export.py\n", "", "0")
        self.assertTrue(measured["measured"])
        self.assertEqual(measured["dirty"], 2)
        self.assertEqual(measured["unpushed"], 0)
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("dirty", verdict["note"])

    def test_unpushed_is_not_landed(self):
        measured = measure_from_git_text("", "abc123\ndef456\n", "2")
        self.assertEqual(measured["unpushed"], 2)
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("unpushed", verdict["note"])

    def test_ahead_clean_push_is_candidate(self):
        measured = {
            "measured": True,
            "dirty": 0,
            "unpushed": 0,
            "ahead_of_main": 3,
        }
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "CANDIDATE")
        self.assertIn("not merged", verdict["note"])

    def test_clean_clone_is_integrated_for_that_tree(self):
        measured = measure_from_git_text("", "", "0")
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("no hoarded bytes", verdict["note"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")


if __name__ == "__main__":
    unittest.main()
