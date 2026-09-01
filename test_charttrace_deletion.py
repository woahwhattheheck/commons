#!/usr/bin/env python3
"""Deletion destroys case bytes and keys and leaves only a tombstone."""

from __future__ import annotations

import unittest

from charttrace.assurance.release_guards import default_deletion_receipt, deletion_report


class ChartTraceDeletionTests(unittest.TestCase):
    def test_tombstone_only(self) -> None:
        self.assertTrue(deletion_report(default_deletion_receipt())["pass"])

    def test_remaining_bytes_or_live_keys_fail(self) -> None:
        receipt = default_deletion_receipt()
        receipt["case_bytes_remaining"] = 4
        self.assertFalse(deletion_report(receipt)["pass"])
        receipt = default_deletion_receipt()
        receipt["keys_destroyed"] = False
        self.assertFalse(deletion_report(receipt)["pass"])
