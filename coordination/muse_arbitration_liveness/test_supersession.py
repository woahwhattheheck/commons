# SPDX-License-Identifier: MIT
from __future__ import annotations
import unittest
from .ledger import LedgerError, compile_ledger
from .test_ledger import decision, payload, request, sent


def _item(events, **kw):
    return compile_ledger(payload(events, **kw))["items"][0]


def _status(events, **kw):
    return _item(events, **kw)["status"]


class SupersessionTests(unittest.TestCase):
    def test_tangoe_predecessor_correction_selects(self):
        old = decision("closed", "2026-09-16T10:00:30Z", "OTHER")
        new = decision("corrected", "2026-09-16T10:01:00Z", "SELECTED", supersedes_provider_event_id="closed")
        got = _item([request(), old, new])
        self.assertEqual(got["status"], "SELECTED_AWAITING_SEND_RECEIPT")
        self.assertEqual(got["superseded_decision_count"], 1)

    def test_hold_supersedes_selected(self):
        old = decision("d0", "2026-09-16T10:00:30Z", "SELECTED")
        new = decision("d1", "2026-09-16T10:01:00Z", "HOLD", supersedes_provider_event_id="d0")
        self.assertEqual(_status([request(), old, new]), "HOLD_OR_COLLISION")

    def test_exact_selection_supersedes_underbound_old_decision(self):
        old = decision("d0", "2026-09-16T10:00:30Z", "SELECTED", bound_purpose_sha256=None)
        new = decision("d1", "2026-09-16T10:01:00Z", "SELECTED", supersedes_provider_event_id="d0")
        self.assertEqual(_status([request(), old, new]), "SELECTED_AWAITING_SEND_RECEIPT")

    def test_missing_target_conflicts(self):
        self.assertEqual(_status([request(), decision(supersedes_provider_event_id="missing")]), "CONFLICT")

    def test_self_supersession_conflicts(self):
        self.assertEqual(_status([request(), decision(supersedes_provider_event_id="d1")]), "CONFLICT")

    def test_nondecision_target_conflicts(self):
        self.assertEqual(_status([request(), decision(supersedes_provider_event_id="r1")]), "CONFLICT")

    def test_target_must_be_strictly_earlier(self):
        old = decision("d0", "2026-09-16T10:01:00Z", "HOLD")
        new = decision("d1", "2026-09-16T10:01:00Z", "SELECTED", supersedes_provider_event_id="d0")
        self.assertEqual(_status([request(), old, new]), "CONFLICT")

    def test_superseder_must_bind_exact_tuple(self):
        old = decision("d0", "2026-09-16T10:00:30Z", "HOLD")
        new = decision("d1", "2026-09-16T10:01:00Z", "SELECTED", supersedes_provider_event_id="d0", bound_seat_id="Z-B")
        self.assertEqual(_status([request(), old, new]), "CONFLICT")

    def test_wrong_request_target_conflicts(self):
        other = decision("d0", "2026-09-16T10:00:20Z", "HOLD", bound_request_key="REQ-2")
        new = decision("d1", "2026-09-16T10:01:00Z", "SELECTED", supersedes_provider_event_id="d0")
        self.assertEqual(_status([request(), other, new]), "CONFLICT")

    def test_double_supersession_conflicts(self):
        old = decision("d0", "2026-09-16T10:00:20Z", "HOLD")
        a = decision("d1", "2026-09-16T10:01:00Z", "SELECTED", supersedes_provider_event_id="d0")
        b = decision("d2", "2026-09-16T10:01:10Z", "HOLD", supersedes_provider_event_id="d0")
        self.assertEqual(_status([request(), old, a, b]), "CONFLICT")

    def test_chain_uses_latest_active_decision(self):
        d0 = decision("d0", "2026-09-16T10:00:20Z", "HOLD")
        d1 = decision("d1", "2026-09-16T10:01:00Z", "SELECTED", supersedes_provider_event_id="d0")
        d2 = decision("d2", "2026-09-16T10:01:20Z", "HOLD", supersedes_provider_event_id="d1")
        got = _item([request(), d0, d1, d2])
        self.assertEqual(got["status"], "HOLD_OR_COLLISION")
        self.assertEqual(got["superseded_decision_count"], 2)

    def test_superseded_selection_does_not_authorize_send(self):
        d0 = decision("d0", "2026-09-16T10:00:20Z", "SELECTED")
        d1 = decision("d1", "2026-09-16T10:01:00Z", "HOLD", supersedes_provider_event_id="d0")
        self.assertEqual(_status([request(), d0, d1, sent(at="2026-09-16T10:02:00Z")]), "CONFLICT")

    def test_correction_after_send_cannot_retro_authorize(self):
        d0 = decision("d0", "2026-09-16T10:00:20Z", "HOLD")
        d1 = decision("d1", "2026-09-16T10:02:30Z", "SELECTED", supersedes_provider_event_id="d0")
        self.assertEqual(_status([request(), d0, sent(at="2026-09-16T10:02:00Z"), d1]), "CONFLICT")

    def test_unhashable_supersedes_value_is_bounded(self):
        bad = decision()
        bad["supersedes_provider_event_id"] = []
        with self.assertRaises(LedgerError):
            compile_ledger(payload([request(), bad]))


if __name__ == "__main__":
    unittest.main()
