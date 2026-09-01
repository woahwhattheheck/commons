#!/usr/bin/env python3
"""Legal/Data/Terms instruments: separate, versioned, no bundled authorization."""

from __future__ import annotations

import unittest

from charttrace.assurance.release_guards import (
    REQUIRED_TERM_INSTRUMENTS,
    default_terms_state,
    terms_report,
)


class ChartTraceTermsTests(unittest.TestCase):
    def test_seven_instruments_and_header_control(self) -> None:
        self.assertEqual(len(REQUIRED_TERM_INSTRUMENTS), 7)
        report = terms_report(default_terms_state(accepted=True))
        self.assertTrue(report["pass"], report)

    def test_prechecked_or_missing_instrument_fails(self) -> None:
        state = default_terms_state()
        state["instruments"].pop("recipient_transfer_authorization")
        self.assertFalse(terms_report(state)["pass"])
        state = default_terms_state()
        state["prechecked_boxes"] = True
        self.assertFalse(terms_report(state)["pass"])
