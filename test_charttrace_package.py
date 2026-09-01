#!/usr/bin/env python3
"""Recipient package parts and fail-closed byte mutation."""

from __future__ import annotations

import hashlib
import unittest

from charttrace.assurance.release_guards import default_package, package_report


class ChartTracePackageTests(unittest.TestCase):
    def test_required_parts_and_digest(self) -> None:
        pkg = default_package()
        self.assertTrue(package_report(pkg)["pass"])
        self.assertEqual(pkg["package_hash"], hashlib.sha256(pkg["payload"]).hexdigest())

    def test_changed_bytes_fail_closed(self) -> None:
        pkg = default_package()
        self.assertTrue(package_report(pkg, mutated=pkg["payload"] + b"x")["pass"])
        self.assertFalse(package_report(pkg, mutated=pkg["payload"])["pass"])
        dropped = dict(pkg)
        dropped.pop("weak_lead_appendix")
        self.assertFalse(package_report(dropped)["pass"])
