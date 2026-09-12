# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import unittest

import coverage as c


class SymbolScannerTests(unittest.TestCase):
    def test_method_module_and_class_changes_are_distinguished(self):
        before = b"X = 1\nclass A:\n    Y = 2\n    def f(self):\n        return 1\n\ndef g():\n    return 3\n"
        after = b"X = 2\nclass A:\n    Y = 4\n    def f(self):\n        return 2\n\ndef g():\n    return 3\n"
        self.assertEqual(c.changed_symbols(before, after), {"__module__", "A.__class__", "A.f"})

    def test_added_method_is_a_changed_symbol(self):
        before = b"class A:\n    def f(self):\n        return 1\n"
        after = b"class A:\n    def f(self):\n        return 1\n    def g(self):\n        return 2\n"
        self.assertEqual(c.changed_symbols(before, after), {"A.g"})


class HistoricalCoverageTests(unittest.TestCase):
    def test_full_historical_ledger_has_zero_unknowns(self):
        ledger = json.loads((Path(__file__).resolve().parent / "COVERAGE.json").read_text(encoding="utf-8"))
        report = c.verify(ledger)
        self.assertEqual(report["unknown_rows"], 0)
        self.assertEqual(
            report["config_added"],
            {"crop_release": True, "early_capital": True, "idle_fertilizer": True, "town_procurement": True},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
