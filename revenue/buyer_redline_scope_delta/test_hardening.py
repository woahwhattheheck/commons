from __future__ import annotations

import copy
import hashlib
import json
import unittest

from revenue.buyer_redline_scope_delta.engine import compile_redline, parse_draft, semantic_digest, verify_packet
from revenue.buyer_redline_scope_delta.test_engine import base_obj, encoded, pair


def resign(packet):
    packet.pop("receipt_sha256", None)
    raw = json.dumps(
        packet,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    packet["receipt_sha256"] = hashlib.sha256(raw).hexdigest()
    return packet


def bound_pair(*, baseline_time: str, counter_time: str):
    baseline = base_obj()
    baseline["observed_at"] = baseline_time
    baseline_raw = encoded(baseline)
    digest = semantic_digest(parse_draft(baseline_raw, role="baseline"))
    counter = copy.deepcopy(baseline)
    counter["generation_id"] = "g2"
    counter["observed_at"] = counter_time
    counter["baseline_semantic_sha256"] = digest
    return baseline_raw, encoded(counter)


class BuyerRedlineScopeDeltaHardeningTests(unittest.TestCase):
    def test_basic_iso_earlier_counter_cannot_bypass_chronology(self):
        packet = compile_redline(*bound_pair(
            baseline_time="2026-09-17T02:00:00Z",
            counter_time="20260917T010000Z",
        ))
        self.assertEqual(packet["status"], "HOLD_CONTRADICTION")
        self.assertIn(
            "counterdraft observed_at predates baseline",
            packet["source"]["binding_reasons"],
        )
        self.assertTrue(verify_packet(packet))

    def test_mixed_iso_representation_does_not_create_false_chronology_hold(self):
        packet = compile_redline(*bound_pair(
            baseline_time="20260917T010000Z",
            counter_time="2026-09-17T02:00:00Z",
        ))
        self.assertEqual(packet["status"], "ACCEPTABLE_AS_WRITTEN")
        self.assertNotIn(
            "counterdraft observed_at predates baseline",
            packet["source"]["binding_reasons"],
        )
        self.assertTrue(verify_packet(packet))

    def test_resigned_empty_authority_object_is_rejected(self):
        packet = compile_redline(*pair())
        packet["authority"] = {}
        self.assertFalse(verify_packet(resign(packet)))

    def test_resigned_falsey_non_boolean_authority_is_rejected(self):
        packet = compile_redline(*pair())
        packet["authority"]["book_revenue"] = 0
        self.assertFalse(verify_packet(resign(packet)))

    def test_resigned_missing_authority_key_is_rejected(self):
        packet = compile_redline(*pair())
        packet["authority"].pop("mutate_payment")
        self.assertFalse(verify_packet(resign(packet)))

    def test_resigned_falsey_binding_ok_is_rejected(self):
        packet = compile_redline(*pair())
        packet["source"]["binding_ok"] = 1
        self.assertFalse(verify_packet(resign(packet)))

    def test_resigned_status_promotion_is_rejected(self):
        packet = compile_redline(*pair())
        packet["status"] = "OWNER_REVIEW"
        self.assertFalse(verify_packet(resign(packet)))

    def test_resigned_summary_drift_is_rejected(self):
        packet = compile_redline(*pair())
        packet["summary"]["changed_clause_count"] = 1
        self.assertFalse(verify_packet(resign(packet)))


if __name__ == "__main__":
    unittest.main()
