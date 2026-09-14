from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from bidveil.canonical import BidVeilError, load_json_strict
from bidveil.engine import prove, verify_receipt_integrity, verify_replay

ROOT = Path(__file__).resolve().parents[1]
AT = "2026-09-13T12:00:00Z"


def fixture(name: str):
    return load_json_strict(ROOT / "fixtures" / name)


class BidVeilTests(unittest.TestCase):
    def setUp(self):
        self.opp = fixture("opportunity.json")
        self.profile = fixture("private-profile.json")

    def test_happy_path_qualified(self):
        receipt = prove(self.opp, self.profile, AT)
        self.assertEqual(receipt["decision"], "QUALIFIED")
        self.assertTrue(all(r["status"] == "SATISFIED" for r in receipt["revealed_results"]))
        self.assertFalse(receipt["onchain_proof_verified"])

    def test_receipt_does_not_reveal_private_values(self):
        rendered = json.dumps(prove(self.opp, self.profile, AT), sort_keys=True)
        for forbidden in ["750000", "US-IN", "carrier-a", "auditor-a", "0123456789abcdef"]:
            self.assertNotIn(forbidden, rendered)

    def test_integrity_and_replay_verify(self):
        receipt = prove(self.opp, self.profile, AT)
        self.assertTrue(verify_receipt_integrity(receipt))
        self.assertTrue(verify_replay(self.opp, self.profile, receipt, AT))

    def test_tampered_receipt_fails(self):
        receipt = prove(self.opp, self.profile, AT)
        receipt["decision"] = "NOT_QUALIFIED"
        self.assertFalse(verify_receipt_integrity(receipt))
        self.assertFalse(verify_replay(self.opp, self.profile, receipt, AT))

    def test_claim_order_is_invariant(self):
        first = prove(self.opp, self.profile, AT)
        changed = deepcopy(self.profile)
        changed["claims"].reverse()
        self.assertEqual(first, prove(self.opp, changed, AT))

    def test_requirement_order_is_invariant(self):
        first = prove(self.opp, self.profile, AT)
        changed = deepcopy(self.opp)
        changed["requirements"].reverse()
        self.assertEqual(first, prove(changed, self.profile, AT))

    def test_wrong_issuer_holds(self):
        changed = deepcopy(self.profile)
        changed["claims"][0]["issuer_id"] = "fake-carrier"
        receipt = prove(self.opp, changed, AT)
        self.assertEqual(receipt["decision"], "HOLD")
        self.assertIn("HOLD_WRONG_ISSUER", [r["status"] for r in receipt["revealed_results"]])

    def test_minimum_below_threshold_not_qualified(self):
        changed = deepcopy(self.profile)
        next(c for c in changed["claims"] if c["requirement_id"] == "annual-revenue-usd")["value"] = 249999
        self.assertEqual(prove(self.opp, changed, AT)["decision"], "NOT_QUALIFIED")

    def test_boolean_mismatch_not_qualified(self):
        changed = deepcopy(self.profile)
        next(c for c in changed["claims"] if c["requirement_id"] == "general-liability-active")["value"] = False
        self.assertEqual(prove(self.opp, changed, AT)["decision"], "NOT_QUALIFIED")

    def test_enum_mismatch_not_qualified(self):
        changed = deepcopy(self.profile)
        next(c for c in changed["claims"] if c["requirement_id"] == "service-region")["value"] = "US-OH"
        self.assertEqual(prove(self.opp, changed, AT)["decision"], "NOT_QUALIFIED")

    def test_missing_claim_not_qualified(self):
        changed = deepcopy(self.profile)
        changed["claims"] = [c for c in changed["claims"] if c["requirement_id"] != "service-region"]
        receipt = prove(self.opp, changed, AT)
        self.assertEqual(receipt["decision"], "NOT_QUALIFIED")
        self.assertIn("MISSING", [r["status"] for r in receipt["revealed_results"]])

    def test_future_evidence_holds(self):
        changed = deepcopy(self.profile)
        changed["claims"][0]["observed_at"] = "2026-09-14T12:00:00Z"
        changed["claims"][0]["expires_at"] = "2027-09-14T12:00:00Z"
        self.assertEqual(prove(self.opp, changed, AT)["decision"], "HOLD")

    def test_expired_evidence_not_qualified(self):
        changed = deepcopy(self.profile)
        changed["claims"][0]["expires_at"] = "2026-09-13T12:00:00Z"
        self.assertEqual(prove(self.opp, changed, AT)["decision"], "NOT_QUALIFIED")

    def test_stale_evidence_not_qualified(self):
        changed = deepcopy(self.opp)
        req = next(r for r in changed["requirements"] if r["id"] == "general-liability-active")
        req["max_age_seconds"] = 60
        self.assertEqual(prove(changed, self.profile, AT)["decision"], "NOT_QUALIFIED")

    def test_opportunity_expired_holds(self):
        receipt = prove(self.opp, self.profile, "2026-10-01T00:00:00Z")
        self.assertEqual(receipt["decision"], "HOLD")
        self.assertTrue(all(r["status"] == "HOLD_OPPORTUNITY_EXPIRED" for r in receipt["revealed_results"]))

    def test_unknown_claim_holds(self):
        changed = deepcopy(self.profile)
        extra = deepcopy(changed["claims"][0])
        extra["requirement_id"] = "not-in-opportunity"
        changed["claims"].append(extra)
        receipt = prove(self.opp, changed, AT)
        self.assertEqual(receipt["decision"], "HOLD")
        self.assertEqual(receipt["revealed_results"][-1], {"requirement_id": "__profile__", "status": "HOLD_UNKNOWN_CLAIMS"})

    def test_duplicate_claim_rejected(self):
        changed = deepcopy(self.profile)
        changed["claims"].append(deepcopy(changed["claims"][0]))
        with self.assertRaises(BidVeilError):
            prove(self.opp, changed, AT)

    def test_duplicate_requirement_rejected(self):
        changed = deepcopy(self.opp)
        changed["requirements"].append(deepcopy(changed["requirements"][0]))
        with self.assertRaises(BidVeilError):
            prove(changed, self.profile, AT)

    def test_generation_change_changes_nullifier(self):
        first = prove(self.opp, self.profile, AT)
        changed = deepcopy(self.opp)
        changed["generation"] = 2
        second = prove(changed, self.profile, AT)
        self.assertNotEqual(first["opportunity_digest"], second["opportunity_digest"])
        self.assertNotEqual(first["nullifier"], second["nullifier"])
        self.assertNotEqual(first["subject_commitment"], second["subject_commitment"])

    def test_profile_transplant_fails_replay(self):
        receipt = prove(self.opp, self.profile, AT)
        changed = deepcopy(self.profile)
        changed["subject_secret_hex"] = "f" * 64
        self.assertFalse(verify_replay(self.opp, changed, receipt, AT))

    def test_type_mismatch_holds(self):
        changed = deepcopy(self.profile)
        next(c for c in changed["claims"] if c["requirement_id"] == "annual-revenue-usd")["value"] = True
        self.assertEqual(prove(self.opp, changed, AT)["decision"], "HOLD")

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            with self.assertRaises(BidVeilError):
                load_json_strict(path)

    def test_float_json_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"x":1.5}', encoding="utf-8")
            with self.assertRaises(BidVeilError):
                load_json_strict(path)

    def test_noncanonical_time_rejected(self):
        changed = deepcopy(self.opp)
        changed["issued_at"] = "2026-09-01T00:00:00+00:00"
        with self.assertRaises(BidVeilError):
            prove(changed, self.profile, AT)


if __name__ == "__main__":
    unittest.main()
