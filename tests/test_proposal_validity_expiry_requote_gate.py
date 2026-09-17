from __future__ import annotations

"""Successor proof for the proposal-validity gate.

The 9dee predecessor suite is retained byte-for-byte in the adjacent private
module. This discoverable subclass adapts deterministic clock injection to the
new private API-generation seam and adds exact predecessors for the two later
STOPs: public-clock rebinding and irrelevant/pre-issue old-source history.
"""

import datetime as dt
import importlib
from pathlib import Path
import sys

# Work under direct execution, unittest discovery, and dotted module invocation.
TEST_DIR = Path(__file__).resolve().parent
ROOT = TEST_DIR.parent
for path in (str(TEST_DIR), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import _proposal_validity_predecessor_suite as _pre

# Reuse the predecessor module's fixtures and public gate import.
gate = _pre.gate
UTC = _pre.UTC
NOW = _pre.NOW
DIGEST2 = _pre.DIGEST2
issued_v2 = _pre.issued_v2
current_v2 = _pre.current_v2


class GateTests(_pre.GateTests):
    def process_packet(self, a=None, b=None, now=NOW):
        evaluate, _verify = gate._build_current_api_for_test(lambda: now)
        return evaluate(a or issued_v2(), b or current_v2())

    def test_package_import_surface_loads_hardened_facade(self):
        packaged = importlib.import_module(
            "revenue.proposal_validity_expiry_requote_gate.gate"
        )
        self.assertTrue(callable(packaged.evaluate_offer))
        self.assertTrue(callable(packaged.verify_packet))
        self.assertTrue(hasattr(packaged, "_build_current_api_for_test"))

    def test_old_current_packet_does_not_verify_after_runtime_expiry(self):
        a = issued_v2()
        a["buyer_deadline"] = None
        a["validity"] = {
            "mode": "VALID_UNTIL",
            "valid_until": "2026-09-20T00:00:00Z",
        }
        b = current_v2()
        packet = self.process_packet(a, b, dt.datetime(2026, 9, 17, 0, 0, tzinfo=UTC))
        _evaluate, verify = gate._build_current_api_for_test(
            lambda: dt.datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
        )
        self.assertFalse(verify(a, b, packet))

    def test_same_coarse_expired_state_with_new_time_reason_does_not_verify(self):
        a = issued_v2()
        a["validity"] = {
            "mode": "VALID_UNTIL",
            "valid_until": "2026-09-15T00:00:00Z",
        }
        a["buyer_deadline"] = "2026-09-18T00:00:00Z"
        b = current_v2()
        b["source_observed_at"] = "2026-09-16T17:00:00Z"
        packet = self.process_packet(a, b, dt.datetime(2026, 9, 17, 0, 0, tzinfo=UTC))
        self.assertEqual(packet["status"], "EXPIRED_REQUOTE_REQUIRED")
        self.assertNotIn(
            "BUYER_DEADLINE_PASSED", packet["requote_delta"]["time_reasons"]
        )
        _evaluate, verify = gate._build_current_api_for_test(
            lambda: dt.datetime(2026, 9, 19, 0, 0, tzinfo=UTC)
        )
        self.assertFalse(verify(a, b, packet))

    def test_stable_expired_semantics_can_still_verify(self):
        a = issued_v2()
        a["buyer_deadline"] = None
        a["validity"] = {
            "mode": "VALID_UNTIL",
            "valid_until": "2026-09-15T00:00:00Z",
        }
        b = current_v2()
        b["source_observed_at"] = "2026-09-16T17:00:00Z"
        packet = self.process_packet(a, b, dt.datetime(2026, 9, 17, 0, 0, tzinfo=UTC))
        _evaluate, verify = gate._build_current_api_for_test(
            lambda: dt.datetime(2026, 9, 19, 0, 0, tzinfo=UTC)
        )
        self.assertTrue(verify(a, b, packet))

    def test_direct_utc_now_rebinding_cannot_select_public_evaluation_history(self):
        a = issued_v2()
        a["issued_on"] = "2026-01-01T00:00:00Z"
        a["validity"] = {
            "mode": "VALID_UNTIL",
            "valid_until": "2099-01-01T00:00:00Z",
        }
        a["buyer_deadline"] = None
        b = current_v2()
        b["source_observed_at"] = "2026-01-02T00:00:00Z"
        original = gate._utc_now
        gate._utc_now = lambda: dt.datetime(2001, 1, 1, tzinfo=UTC)
        try:
            out = gate.evaluate_offer(a, b)
        finally:
            gate._utc_now = original
        self.assertEqual(out["status"], "CURRENT_FOR_OWNER_USE")
        self.assertFalse(out["evaluated_at"].startswith("2001-"))
        self.assertEqual(out["clock_basis"], "PROCESS_UTC")

    def test_direct_utc_now_rebinding_cannot_freeze_public_verify(self):
        a = issued_v2()
        a["issued_on"] = "2026-01-01T00:00:00Z"
        a["validity"] = {
            "mode": "VALID_UNTIL",
            "valid_until": "2099-01-01T00:00:00Z",
        }
        a["buyer_deadline"] = None
        b = current_v2()
        b["source_observed_at"] = "2026-01-02T00:00:00Z"
        packet = self.process_packet(a, b, NOW)
        original = gate._utc_now
        gate._utc_now = lambda: dt.datetime(2100, 1, 1, tzinfo=UTC)
        try:
            self.assertTrue(gate.verify_packet(a, b, packet))
        finally:
            gate._utc_now = original

    def test_other_offer_old_source_history_is_ignored_after_syntax_validation(self):
        b = current_v2()
        b["superseding_events"] = [{
            "kind": "AMENDMENT",
            "event_id": "OTHER-OLD-1",
            "observed_at": "2026-09-12T00:00:00Z",
            "applies_to_offer_id": "OTHER",
            "source_generation": "src-historical",
            "source_digest_sha256": DIGEST2,
        }]
        out = self.compile(b=b)
        self.assertEqual(out["status"], "CURRENT_FOR_OWNER_USE")
        self.assertEqual(out["requote_delta"]["superseding_events"], [])

    def test_pre_issue_old_source_history_for_offer_is_ignored(self):
        b = current_v2()
        b["superseding_events"] = [{
            "kind": "REDLINE",
            "event_id": "PREISSUE-OLD-1",
            "observed_at": "2026-09-09T00:00:00Z",
            "applies_to_offer_id": "OFFER-001",
            "source_generation": "src-historical",
            "source_digest_sha256": DIGEST2,
        }]
        out = self.compile(b=b)
        self.assertEqual(out["status"], "CURRENT_FOR_OWNER_USE")
        self.assertEqual(out["requote_delta"]["superseding_events"], [])

    def test_post_issue_relevant_old_source_history_still_fails_closed(self):
        b = current_v2()
        b["superseding_events"] = [{
            "kind": "REPRICE",
            "event_id": "ACTIVE-OLD-1",
            "observed_at": "2026-09-12T00:00:00Z",
            "applies_to_offer_id": "OFFER-001",
            "source_generation": "src-historical",
            "source_digest_sha256": DIGEST2,
        }]
        with self.assertRaisesRegex(gate.GateError, "source generation"):
            self.compile(b=b)


if __name__ == "__main__":
    _pre.unittest.main(verbosity=2)
