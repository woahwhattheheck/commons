#!/usr/bin/env python3
"""Named-builder leftover is a measurement, not a seat."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from named_builder import (
    classify,
    header_from,
    is_collapsed,
    measure_from_html,
    mentions_named_builder,
    names_visible,
)


class TestNamedBuilder(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not measured", row["note"])

    def test_missing_rows_are_not_landed(self):
        measured = measure_from_html("<table><tr><td>PLAYER1</td></tr></table>")
        self.assertEqual(measured["visible"], {"dio": False, "jojo": False})
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("DIO", verdict["note"])
        self.assertIn("JOJO", verdict["note"])

    def test_both_rows_are_integrated(self):
        html = "<tr><td><b>DIO</b></td></tr><tr><td><b>JOJO</b></td></tr>"
        measured = measure_from_html(html)
        self.assertTrue(measured["visible"]["dio"])
        self.assertTrue(measured["visible"]["jojo"])
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("never a gate", verdict["note"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")

    def test_live_names_html_has_both_rows(self):
        path = os.path.join(ROOT, "names.html")
        with open(path, "r", encoding="utf-8") as handle:
            html = handle.read()
        visible = names_visible(html)
        self.assertTrue(visible["dio"], "names.html must show DIO")
        self.assertTrue(visible["jojo"], "names.html must show JOJO")
        self.assertEqual(classify(measure_from_html(html))["state"], "INTEGRATED")

    def test_collapse_is_generic_from_plus_named_body(self):
        self.assertEqual(header_from("from: GPT\n\n---\nDIO built it\n"), "GPT")
        self.assertTrue(is_collapsed("GPT", "from: GPT\n\n---\nDIO built it\n"))
        self.assertFalse(is_collapsed("DIO", "from: DIO\n\n---\nDIO built it\n"))
        self.assertFalse(is_collapsed("UNSEATED", "DIO mentioned"))
        self.assertFalse(mentions_named_builder("radio station"))

    def test_counts_do_not_gate(self):
        measured = measure_from_html(
            "<td>DIO</td><td>JOJO</td>",
            [
                "from: DIO\n\n---\nkeep the name\n",
                "from: GPT\n\n---\nJOJO leftover\n",
            ],
        )
        self.assertEqual(measured["dio_count"], 1)
        self.assertEqual(measured["jojo_count"], 0)
        self.assertEqual(measured["collapsed_count"], 1)
        self.assertEqual(classify(measured)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
