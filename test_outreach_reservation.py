#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from outreach_reservation import (
    ReservationConflict,
    ReservationError,
    assert_send_authority,
    conflicts_for,
    identity_fingerprints,
    mark_sent,
    prepare_reservation,
    release_reservation,
    validate_ledger,
)


def empty_ledger():
    return {
        "schema_version": 1,
        "kind": "OUTREACH_RESERVATION_LEDGER",
        "policy": {
            "authority": "main_blob_sha_compare_and_swap",
            "conflict_scope": "any matching org, recipient, or lead fingerprint",
            "slack_take_is_authority": False,
            "fail_closed_without_main": True,
            "sent_dnr_is_permanent": True,
        },
        "claims": [],
    }


class TestOutreachReservation(unittest.TestCase):
    def test_org_collision_blocks_different_people_at_same_company(self):
        ledger, rid = prepare_reservation(
            empty_ledger(),
            org_key="Acme, Inc.",
            owner="swarm-a",
            recipient="alice@acme.example",
            claimed_at="2026-09-13T22:00:00Z",
        )
        with self.assertRaises(ReservationConflict):
            prepare_reservation(
                ledger,
                org_key="ACME INC",
                owner="swarm-b",
                recipient="bob@acme.example",
                claimed_at="2026-09-13T22:00:01Z",
            )
        self.assertTrue(rid.startswith("outreach-"))

    def test_recipient_collision_catches_org_spelling_drift(self):
        ledger, _ = prepare_reservation(
            empty_ledger(),
            org_key="Acme",
            owner="swarm-a",
            recipient="HotLead@Example.COM",
            claimed_at="2026-09-13T22:00:00Z",
        )
        with self.assertRaises(ReservationConflict):
            prepare_reservation(
                ledger,
                org_key="Acme Holdings New Name",
                owner="swarm-b",
                recipient="hotlead@example.com",
                claimed_at="2026-09-13T22:00:01Z",
            )

    def test_provider_lead_ref_collision_catches_both_name_and_email_drift(self):
        ledger, _ = prepare_reservation(
            empty_ledger(),
            org_key="Acme",
            owner="swarm-a",
            recipient="first@acme.example",
            lead_ref="apollo:person:123",
            claimed_at="2026-09-13T22:00:00Z",
        )
        with self.assertRaises(ReservationConflict):
            prepare_reservation(
                ledger,
                org_key="Different Spelling",
                owner="swarm-b",
                recipient="second@other.example",
                lead_ref="APOLLO:PERSON:123",
                claimed_at="2026-09-13T22:00:01Z",
            )

    def test_slack_take_is_not_authority_and_uncommitted_copy_is_not_enough(self):
        original = empty_ledger()
        proposed, rid = prepare_reservation(
            original,
            org_key="Acme",
            owner="swarm-a",
            claimed_at="2026-09-13T22:00:00Z",
        )
        with self.assertRaises(ReservationError):
            assert_send_authority(
                original,
                reservation_id=rid,
                owner="swarm-a",
                org_key="Acme",
            )
        self.assertEqual(
            assert_send_authority(
                proposed,
                reservation_id=rid,
                owner="swarm-a",
                org_key="Acme",
            )["state"],
            "RESERVED",
        )

    def test_wrong_owner_or_identity_fails_closed(self):
        ledger, rid = prepare_reservation(
            empty_ledger(),
            org_key="Acme",
            owner="swarm-a",
            recipient="alice@acme.example",
            claimed_at="2026-09-13T22:00:00Z",
        )
        with self.assertRaises(ReservationError):
            assert_send_authority(
                ledger,
                reservation_id=rid,
                owner="swarm-b",
                org_key="Acme",
                recipient="alice@acme.example",
            )
        with self.assertRaises(ReservationError):
            assert_send_authority(
                ledger,
                reservation_id=rid,
                owner="swarm-a",
                org_key="Acme",
                recipient="bob@acme.example",
            )

    def test_sent_is_permanent_dnr(self):
        ledger, rid = prepare_reservation(
            empty_ledger(),
            org_key="Acme",
            owner="swarm-a",
            claimed_at="2026-09-13T22:00:00Z",
        )
        sent = mark_sent(
            ledger,
            reservation_id=rid,
            owner="swarm-a",
            sent_at="2026-09-13T22:01:00Z",
            source_ref="gmail:message:abc",
        )
        self.assertEqual(sent["claims"][0]["state"], "SENT_DNR")
        with self.assertRaises(ReservationConflict):
            prepare_reservation(
                sent,
                org_key="Acme",
                owner="swarm-b",
                claimed_at="2026-09-13T22:02:00Z",
            )
        with self.assertRaises(ReservationError):
            release_reservation(
                sent,
                reservation_id=rid,
                owner="swarm-a",
                released_at="2026-09-13T22:03:00Z",
            )

    def test_unsent_release_allows_new_owner(self):
        ledger, rid = prepare_reservation(
            empty_ledger(),
            org_key="Acme",
            owner="swarm-a",
            claimed_at="2026-09-13T22:00:00Z",
        )
        released = release_reservation(
            ledger,
            reservation_id=rid,
            owner="swarm-a",
            released_at="2026-09-13T22:01:00Z",
            reason="no transport occurred",
        )
        next_ledger, next_id = prepare_reservation(
            released,
            org_key="Acme",
            owner="swarm-b",
            claimed_at="2026-09-13T22:02:00Z",
        )
        self.assertNotEqual(rid, next_id)
        self.assertEqual(next_ledger["claims"][-1]["state"], "RESERVED")

    def test_validator_rejects_manual_double_active_claim(self):
        ledger, rid = prepare_reservation(
            empty_ledger(),
            org_key="Acme",
            owner="swarm-a",
            claimed_at="2026-09-13T22:00:00Z",
        )
        bad = copy.deepcopy(ledger)
        clone = copy.deepcopy(bad["claims"][0])
        clone["reservation_id"] = "manual-race"
        clone["owner"] = "swarm-b"
        bad["claims"].append(clone)
        with self.assertRaises(ReservationError):
            validate_ledger(bad)

    def test_live_seed_ledger_valid_and_known_dnr_blocks(self):
        path = os.path.join(ROOT, "revenue", "payment_ready", "outreach_reservations.json")
        with open(path, encoding="utf-8") as handle:
            ledger = json.load(handle)
        validate_ledger(ledger)
        for org in (
            "PayPal",
            "Stripe",
            "Mailchimp",
            "Square",
            "LM Studio",
            "Ollama",
            "AnythingLLM",
            "Parallel Wireless",
            "NextGen Federal",
            "Lyceum Technology",
        ):
            self.assertTrue(
                conflicts_for(ledger, identity_fingerprints(org)),
                f"legacy do-not-resend missing for {org}",
            )


if __name__ == "__main__":
    unittest.main()
