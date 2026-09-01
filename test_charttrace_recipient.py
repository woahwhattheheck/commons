#!/usr/bin/env python3
"""Named-human recipient authorization is separate and fail-closed."""

from __future__ import annotations

import unittest

from charttrace.assurance.release_guards import default_package, recipient_report


class ChartTraceRecipientTests(unittest.TestCase):
    def test_named_authorization_required(self) -> None:
        pkg = default_package()
        self.assertTrue(recipient_report(pkg["recipient"])["pass"])

    def test_unnamed_or_unlocked_recipient_blocked(self) -> None:
        self.assertFalse(recipient_report({"name": "", "authorized": True, "authorization_id": "x"})["pass"])
        self.assertFalse(recipient_report(default_package()["recipient"], bytes_locked=False)["pass"])
