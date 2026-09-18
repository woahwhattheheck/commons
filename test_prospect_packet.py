#!/usr/bin/env python3

from __future__ import annotations

import copy
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from prospect_packet import READY, SUPPRESSED, validate


def complete_packet():
    return {
        "schema_version": "commons-marketing-sales-prospect-packet/v1",
        "packet_id": "example-decision-maker-20260831-01",
        "organization": {
            "name": "Example Systems",
            "domain": "example.com",
            "evidence_url": "https://example.com/about",
        },
        "decision_maker": {
            "name": "Ada Buyer",
            "role": "Chief Operating Officer",
            "authority_evidence_url": "https://example.com/leadership",
            "public_professional_route": {
                "type": "email",
                "value": "ada@example.com",
                "evidence_url": "https://example.com/contact",
            },
        },
        "need": {
            "failure_sentence": "One accepted job can create two customer-visible actions after retry.",
            "evidence_url": "https://example.com/status/incident-7",
            "observed_at": "2026-08-31T00:00:00Z",
        },
        "offer": {
            "narrow_sku": "Exactly-once retry receipt",
            "diagnostic_price_usd": 199,
            "one_day_deliverable": "Replay fixture, event trace, and written failure finding.",
            "binary_acceptance": ["one input produces exactly one visible action"],
            "optional_proof_price_usd": 2500,
        },
        "dedupe": {
            "checked_at": "2026-08-31T00:05:00Z",
            "checks": [
                {"surface": "commons", "query": "example.com Ada Buyer", "result": "CLEAR"},
                {"surface": "gmail_sent", "query": "to:ada@example.com", "result": "CLEAR"},
            ],
        },
        "suppression": {"hard_do_not_resend": False, "prior_transport_found": False},
    }


class ProspectPacketTests(unittest.TestCase):
    def test_complete_packet_is_handoff_ready_but_never_transport_permission(self):
        result = validate(complete_packet())
        self.assertEqual(result["status"], READY)
        self.assertEqual(result["handoff_owner"], "MASTER_OF_ACCOUNTS")
        self.assertFalse(result["transport_permission"])
        self.assertEqual(result["external_actions"], 0)
        self.assertEqual(result["cash_usd"], 0)

    def test_missing_named_decision_maker_is_suppressed(self):
        packet = complete_packet()
        packet["decision_maker"]["name"] = ""
        result = validate(packet)
        self.assertEqual(result["status"], SUPPRESSED)
        self.assertTrue(any("decision_maker.name" in reason for reason in result["reasons"]))

    def test_generic_unsourced_route_is_suppressed(self):
        packet = complete_packet()
        packet["decision_maker"]["public_professional_route"]["evidence_url"] = ""
        self.assertEqual(validate(packet)["status"], SUPPRESSED)

    def test_broad_offer_without_binary_acceptance_is_suppressed(self):
        packet = complete_packet()
        packet["offer"]["binary_acceptance"] = []
        self.assertEqual(validate(packet)["status"], SUPPRESSED)

    def test_missing_sent_dedupe_is_suppressed(self):
        packet = complete_packet()
        packet["dedupe"]["checks"] = packet["dedupe"]["checks"][:1]
        result = validate(packet)
        self.assertEqual(result["status"], SUPPRESSED)
        self.assertTrue(any("gmail_sent" in reason for reason in result["reasons"]))

    def test_prior_transport_is_suppressed(self):
        packet = copy.deepcopy(complete_packet())
        packet["suppression"]["prior_transport_found"] = True
        result = validate(packet)
        self.assertEqual(result["status"], SUPPRESSED)
        self.assertTrue(any("prior_transport_found" in reason for reason in result["reasons"]))

    def test_non_object_never_crashes(self):
        result = validate(["not", "a", "packet"])
        self.assertEqual(result["status"], SUPPRESSED)
        self.assertEqual(result["external_actions"], 0)


if __name__ == "__main__":
    unittest.main()
