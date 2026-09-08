#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check source-preserving application without modifying a working tree."""
from pathlib import Path
import unittest
from apply_distance import apply

HERE=Path(__file__).resolve().parent

class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.original=(HERE/'distance_original.inc').read_bytes()
        self.expected=(HERE/'distance_candidate.inc').read_bytes()

    def test_exact_method(self):
        self.assertEqual(apply(self.original),self.expected)

    def test_reapplication_is_idempotent(self):
        self.assertEqual(apply(self.expected),self.expected)

    def test_independent_regions_preserved(self):
        before=b'// independent topology change\nclass Solver {\n'
        after=b'\n// independent objective change\n};\n'
        self.assertEqual(apply(before+self.original+after),before+self.expected+after)

    def test_method_edits_are_not_overwritten(self):
        with self.assertRaisesRegex(ValueError,'independent edits'):
            apply(self.original.replace(b'if (a == b) return 0;',b'if (a == b) return 1;'))

    def test_missing_signature(self):
        with self.assertRaisesRegex(ValueError,'exactly one'):
            apply(b'// missing method')

    def test_duplicate_signature(self):
        with self.assertRaisesRegex(ValueError,'exactly one'):
            apply(self.original+self.original)

    def test_truncated_method(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            apply(self.original[:-3])

if __name__=='__main__':unittest.main(verbosity=2)
