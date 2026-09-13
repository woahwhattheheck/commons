from __future__ import annotations

import copy
import unittest

from . import BridgeError, create_operator_verification, load_json_strict, verify_operator_verification
from .fixtures import (
    NOW, OWNER_KEY, VERIFY_KEY, ZERO, contract, contract_verifier, schedule, verification,
)


class VerificationTests(unittest.TestCase):
    def bad(self, fn, *args, **kwargs):
        with self.assertRaises(BridgeError):
            fn(*args, **kwargs)

    def test_happy_verification(self):
        c = contract(); receipt = verification(c)
        verified, readback = verify_operator_verification(c, receipt, OWNER_KEY, VERIFY_KEY, trusted_now=NOW, contract_verifier=contract_verifier)
        self.assertEqual(verified["offer_sha256"], c["offer_sha256"]); self.assertEqual(readback, receipt)

    def test_exact_money_types(self):
        for value in (True, 1500000.0):
            c = contract(); c["offer"]["total_amount_minor"] = value
            self.bad(verification, c)

    def test_only_usd(self):
        c = contract(); c["offer"]["currency"] = "EUR"; self.bad(verification, c)

    def test_requires_captured_state(self):
        c = contract(); c["state"] = "READY_FOR_EXPLICIT_SEND"; self.bad(verification, c)

    def test_rejects_authority_escalation(self):
        for field in ("fulfillment_authorized", "payment_collected", "revenue_recognized", "buyer_acceptance_verified"):
            c = contract(); c["authority"][field] = True; self.bad(verification, c)

    def test_acceptance_offer_binding(self):
        c = contract(); c["buyer_acceptance"]["offer_sha256"] = ZERO; self.bad(verification, c)

    def test_acceptance_buyer_binding(self):
        c = contract(); c["buyer_acceptance"]["buyer_ref"] = "otherbuyer_001"; self.bad(verification, c)

    def test_acceptance_time_bounds(self):
        for stamp in ("2026-09-13T10:01:00Z", "2026-09-13T10:11:00Z"):
            c = contract(); c["buyer_acceptance"]["accepted_at"] = stamp; self.bad(verification, c)

    def test_schedule_acceptance_cannot_predate_offer(self):
        s = schedule(); s["accepted_at"] = "2026-09-13T10:02:30Z"; self.bad(verification, sched=s)

    def test_service_cannot_start_before_schedule_acceptance(self):
        s = schedule(); s["start"] = "2026-09-13T10:04:00Z"; self.bad(verification, sched=s)

    def test_schedule_window_must_advance(self):
        s = schedule(); s["end"] = s["start"]; self.bad(verification, sched=s)

    def test_schedule_acceptance_not_future(self):
        s = schedule(); s["accepted_at"] = "2026-09-13T10:11:00Z"; self.bad(verification, sched=s)

    def test_operator_verification_time_bounds(self):
        for stamp in ("2026-09-13T10:04:30Z", "2026-09-13T10:11:00Z"):
            self.bad(verification, verified_at=stamp)

    def test_public_ref_allowlist(self):
        self.bad(verification, public_ref="mailto:someone.invalid")

    def test_wrong_owner_key(self):
        self.bad(
            create_operator_verification, contract(), b"X" * 32, VERIFY_KEY,
            verifier_id="operator-001", key_id="acceptance-key-v1", verified_at="2026-09-13T10:06:00Z",
            public_ref="p/accepted-offer.md", schedule_acceptance=schedule(), trusted_now=NOW,
            contract_verifier=contract_verifier,
        )

    def test_wrong_verification_key(self):
        c = contract(); receipt = verification(c)
        self.bad(verify_operator_verification, c, receipt, OWNER_KEY, b"Y" * 32, trusted_now=NOW, contract_verifier=contract_verifier)

    def test_receipt_binding_tamper(self):
        c = contract(); receipt = verification(c); receipt["acceptance_evidence_sha256"] = ZERO
        self.bad(verify_operator_verification, c, receipt, OWNER_KEY, VERIFY_KEY, trusted_now=NOW, contract_verifier=contract_verifier)

    def test_schedule_tamper_breaks_hmac(self):
        c = contract(); receipt = verification(c); receipt["schedule_acceptance"]["end"] = "2026-09-19T21:00:00Z"
        self.bad(verify_operator_verification, c, receipt, OWNER_KEY, VERIFY_KEY, trusted_now=NOW, contract_verifier=contract_verifier)

    def test_unknown_verification_field(self):
        c = contract(); receipt = verification(c); receipt["surprise"] = True
        self.bad(verify_operator_verification, c, receipt, OWNER_KEY, VERIFY_KEY, trusted_now=NOW, contract_verifier=contract_verifier)

    def test_empty_exclusions_fail_closed(self):
        c = contract(); c["offer"]["exclusions"] = []; self.bad(verification, c)

    def test_strict_json(self):
        for raw in ('{"a":1,"a":2}', '{"a":1.5}', '{"a":NaN}'):
            self.bad(load_json_strict, raw)
        self.assertEqual(load_json_strict('{"a":1,"b":"x"}'), {"a": 1, "b": "x"})


if __name__ == "__main__":
    unittest.main()
