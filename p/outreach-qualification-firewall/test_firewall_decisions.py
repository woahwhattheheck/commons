from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import outreach_qualification_firewall as fw  # noqa: E402

HIST = "2026-09-17T20:00:00Z"


def packet():
    return fw.strict_json_loads((ROOT / "demo.json").read_text())


def resign_source(data):
    source = fw._validate_source(copy.deepcopy(data["source_packet"]))
    data["source_packet"] = source
    data["source_packet_sha256"] = fw.sha256_hex(fw.canonical_json(source))


def rebind_lease(data):
    normalized_source = fw._validate_source(copy.deepcopy(data["source_packet"]))
    normalized_contact = fw._validate_contact(copy.deepcopy(data["contact"]))
    data["writer_lease"]["collision_key"] = fw.compute_dedupe_key(normalized_source, normalized_contact)



class FirewallDecisionTests(unittest.TestCase):
    def test_historical_can_qualify_owner_but_never_send(self):
        out = fw.compile_historical(packet(), as_of=HIST)
        self.assertTrue(out["qualified_for_owner_review"])
        self.assertFalse(out["authorized_to_send"])
        self.assertIn("HOLD_HISTORICAL_EVALUATION", out["hold_reasons"])
        self.assertTrue(fw.verify_receipt(packet(), out))

    def test_current_positive_requires_go(self):
        data = packet()
        now = fw._process_utc_now()
        data["writer_lease"]["issued_at"] = fw._utc_text(now - timedelta(seconds=60))
        data["writer_lease"]["expires_at"] = fw._utc_text(now + timedelta(seconds=600))
        out = fw.compile_current(data)
        self.assertTrue(out["qualified_for_owner_review"])
        self.assertTrue(out["authorized_to_send"])
        self.assertEqual(out["send_state"], "AUTHORIZED_TO_SEND")
        self.assertTrue(fw.verify_receipt(data, out))

    def test_bare_selected_never_authorizes(self):
        data = packet()
        now = fw._process_utc_now()
        data["writer_lease"]["issued_at"] = fw._utc_text(now - timedelta(seconds=60))
        data["writer_lease"]["expires_at"] = fw._utc_text(now + timedelta(seconds=600))
        data["writer_lease"]["status"] = "SELECTED"
        out = fw.compile_current(data)
        self.assertTrue(out["qualified_for_owner_review"])
        self.assertFalse(out["authorized_to_send"])
        self.assertIn("HOLD_WRITER_LEASE_STATUS", out["hold_reasons"])

    def test_deadline_exact_boundary_passes_owner_review(self):
        data = packet()
        data["source_packet"]["deadline_at"] = "2026-09-18T20:00:00Z"
        data["source_packet"]["min_runway_seconds"] = 86400
        resign_source(data)
        out = fw.compile_historical(data, as_of=HIST)
        self.assertTrue(out["qualified_for_owner_review"])

    def test_deadline_one_second_inside_fails(self):
        data = packet()
        data["source_packet"]["deadline_at"] = "2026-09-18T19:59:59Z"
        data["source_packet"]["min_runway_seconds"] = 86400
        resign_source(data)
        out = fw.compile_historical(data, as_of=HIST)
        self.assertFalse(out["qualified_for_owner_review"])
        self.assertIn("HOLD_RUNWAY", out["hold_reasons"])

    def test_registration_unknown_fails_closed(self):
        data = packet()
        data["source_packet"]["registration_required"] = True
        data["source_packet"]["registration_state"] = "UNKNOWN"
        resign_source(data)
        out = fw.compile_historical(data, as_of=HIST)
        self.assertFalse(out["qualified_for_owner_review"])
        self.assertIn("HOLD_REGISTRATION", out["hold_reasons"])

    def test_required_unknown_qualification_fails_closed(self):
        data = packet()
        data["qualifications"][0]["disposition"] = "UNKNOWN"
        out = fw.compile_historical(data, as_of=HIST)
        self.assertFalse(out["qualified_for_owner_review"])
        self.assertIn("HOLD_QUALIFICATION_UNKNOWN", out["hold_reasons"])

    def test_nonrequired_unknown_does_not_block(self):
        data = packet()
        data["qualifications"].append({
            "gate_id": "post-award-insurance",
            "disposition": "UNKNOWN",
            "required_for_outreach": False,
            "evidence_ref": "evidence-extra",
            "evidence_sha256": "3" * 64,
        })
        out = fw.compile_historical(data, as_of=HIST)
        self.assertTrue(out["qualified_for_owner_review"])

    def test_dnr_bounce_and_sent_dnr_block(self):
        for state in ("DNR", "BOUNCE", "SENT_DNR"):
            data = packet()
            data["contact"]["relationship_state"] = state
            with self.subTest(state=state):
                out = fw.compile_historical(data, as_of=HIST)
                self.assertFalse(out["qualified_for_owner_review"])
                self.assertIn("HOLD_RELATIONSHIP", out["hold_reasons"])

    def test_zero_or_unbounded_economics_rejected(self):
        for field, value in (("amount_minor", 0), ("quantity_max", 0), ("quantity_max", fw.MAX_QUANTITY + 1)):
            data = packet()
            data["economics"][field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(fw.FirewallError):
                    fw.compile_historical(data, as_of=HIST)

    def test_foreign_lease_seat_session_and_key_block_send(self):
        mutations = [
            ("seat", "other-seat", "HOLD_WRITER_LEASE_SEAT"),
            ("session_nonce", "other-session", "HOLD_WRITER_LEASE_SESSION"),
            ("collision_key", "f" * 64, "HOLD_WRITER_LEASE_KEY"),
        ]
        for field, value, reason in mutations:
            data = packet()
            data["writer_lease"][field] = value
            with self.subTest(field=field):
                out = fw.compile_current(data)
                self.assertFalse(out["authorized_to_send"])
                self.assertIn(reason, out["hold_reasons"])

    def test_expired_and_future_lease_block_send(self):
        data = packet()
        data["writer_lease"]["issued_at"] = "2025-01-01T00:00:00Z"
        data["writer_lease"]["expires_at"] = "2025-01-01T00:30:00Z"
        self.assertIn("HOLD_WRITER_LEASE_EXPIRED", fw.compile_current(data)["hold_reasons"])
        data = packet()
        data["writer_lease"]["issued_at"] = "2098-01-01T00:00:00Z"
        data["writer_lease"]["expires_at"] = "2098-01-01T00:30:00Z"
        self.assertIn("HOLD_WRITER_LEASE_NOT_YET_VALID", fw.compile_current(data)["hold_reasons"])


    def test_future_source_observation_holds(self):
        data = packet()
        data["source_packet"]["observed_at"] = "2026-09-18T00:00:00Z"
        resign_source(data)
        out = fw.compile_historical(data, as_of=HIST)
        self.assertFalse(out["qualified_for_owner_review"])
        self.assertIn("HOLD_SOURCE_FUTURE", out["hold_reasons"])

    def test_lease_lifetime_is_bounded(self):
        data = packet()
        data["writer_lease"]["issued_at"] = "2026-09-17T19:00:00Z"
        data["writer_lease"]["expires_at"] = "2026-09-17T20:00:01Z"
        with self.assertRaisesRegex(fw.FirewallError, "one-hour ceiling"):
            fw.compile_historical(data, as_of=HIST)

