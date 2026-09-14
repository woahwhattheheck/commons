from __future__ import annotations

import copy
import json
import unittest
from datetime import timedelta

from revenue.paid_pilot_admission.acceptance import fixture
from revenue.paid_pilot_admission.gate import AdmissionError, READY, digest, evaluate, markdown, normalize_packet, verify
from revenue.paid_pilot_admission.strict_json import StrictJSONError, loads


class GateTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.now = fixture()

    def test_ready_and_verify(self):
        result = evaluate(self.packet, now=self.now)
        self.assertEqual(result.status, READY)
        self.assertTrue(verify(self.packet, result.receipt))
        self.assertIn("Authority ceiling", markdown(result.receipt))
        self.assertTrue(all(value is False for value in result.receipt["external_authority"].values()))

    def test_order_invariant_input(self):
        original = evaluate(self.packet, now=self.now).receipt
        reordered = json.loads(json.dumps(self.packet, sort_keys=True))
        self.assertEqual(original, evaluate(reordered, now=self.now).receipt)

    def test_hold_variants(self):
        variants = []
        def add(name, mutate):
            p = copy.deepcopy(self.packet); mutate(p); variants.append((name, p))
        add("partial", lambda p: p["funding"].__setitem__("amount_minor", 299999))
        add("over quoted price", lambda p: p["funding"].__setitem__("amount_minor", 600001))
        add("authorized", lambda p: p["funding"].__setitem__("status", "AUTHORIZED"))
        add("currency", lambda p: p["funding"].__setitem__("currency", "EUR"))
        add("funding offer", lambda p: p["funding"].__setitem__("offer_id", "x"))
        add("acceptance offer", lambda p: p["acceptance"].__setitem__("offer_id", "x"))
        add("funding digest", lambda p: p["funding"].__setitem__("offer_sha256", "c" * 64))
        add("acceptance digest", lambda p: p["acceptance"].__setitem__("offer_sha256", "c" * 64))
        add("changed price", lambda p: p["offer"].__setitem__("price_minor", 600001))
        add("changed scope", lambda p: p["offer"]["scope"].__setitem__(0, "changed scope"))
        add("changed acceptance", lambda p: p["offer"]["acceptance_criteria"].__setitem__(0, "changed criterion"))
        add("stale", lambda p: p["funding"].__setitem__("observed_at", (self.now - timedelta(days=2)).isoformat().replace("+00:00", "Z")))
        add("future funding", lambda p: p["funding"].__setitem__("observed_at", (self.now + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")))
        add("future acceptance", lambda p: p["acceptance"].__setitem__("accepted_at", (self.now + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")))
        add("acceptance before offer", lambda p: p["acceptance"].__setitem__("accepted_at", (self.now - timedelta(hours=3)).isoformat().replace("+00:00", "Z")))
        add("funding before offer", lambda p: p["funding"].__setitem__("observed_at", (self.now - timedelta(hours=3)).isoformat().replace("+00:00", "Z")))
        add("offer future", lambda p: (p["offer"].__setitem__("issued_at", (self.now + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")), p["offer"].__setitem__("expires_at", (self.now + timedelta(days=2)).isoformat().replace("+00:00", "Z"))))
        add("expired", lambda p: p["offer"].__setitem__("expires_at", (self.now - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")))
        for name, packet in variants:
            with self.subTest(name=name):
                self.assertNotEqual(evaluate(packet, now=self.now).status, READY)

    def test_acceptance_after_funding(self):
        p = copy.deepcopy(self.packet)
        p["acceptance"]["accepted_at"] = (self.now - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        p["funding"]["observed_at"] = (self.now - timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
        self.assertIn("HOLD_ACCEPTANCE_AFTER_FUNDING", evaluate(p, now=self.now).reasons)

    def test_tampered_receipt_rejected(self):
        receipt = evaluate(self.packet, now=self.now).receipt
        for key, value in [("status", "X"), ("price_minor", 1), ("funding_evidence_sha256", "c" * 64)]:
            with self.subTest(key=key):
                p = copy.deepcopy(receipt); p[key] = value
                self.assertFalse(verify(self.packet, p))

    def test_strict_shape_and_values(self):
        bad = []
        def variant(mutate):
            p = copy.deepcopy(self.packet); mutate(p); bad.append(p)
        variant(lambda p: p.__setitem__("extra", 1))
        variant(lambda p: p["offer"].__setitem__("currency", "usd"))
        variant(lambda p: p["offer"].__setitem__("price_minor", True))
        variant(lambda p: p["offer"].__setitem__("admission_funding_minor", 0))
        variant(lambda p: p["offer"].__setitem__("admission_funding_minor", 600001))
        variant(lambda p: p["offer"].__setitem__("scope", []))
        variant(lambda p: p["offer"].__setitem__("scope", ["b", "a"]))
        variant(lambda p: p["offer"].__setitem__("scope", ["a", "a"]))
        variant(lambda p: p["offer"].__setitem__("funding_freshness_seconds", 59))
        variant(lambda p: p["acceptance"].__setitem__("evidence_sha256", "BAD"))
        variant(lambda p: p["funding"].__setitem__("source_authority", ""))
        variant(lambda p: p["funding"].__setitem__("source_authority", "UNVERIFIED_SCREENSHOT"))
        for packet in bad:
            with self.assertRaises(AdmissionError):
                normalize_packet(packet)

    def test_duplicate_json_rejected(self):
        with self.assertRaises(StrictJSONError):
            loads('{"x":1,"x":2}')
        with self.assertRaises(StrictJSONError):
            loads('{"x":NaN}')

    def test_exact_offer_hash(self):
        normalized = normalize_packet(self.packet)
        self.assertEqual(normalized["derived"]["offer_sha256"], digest(normalized["offer"]))


if __name__ == "__main__":
    unittest.main()
