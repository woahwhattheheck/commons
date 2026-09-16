from __future__ import annotations

import copy
import unittest
from datetime import datetime, timedelta, timezone

from tools.outbound_send_guard import muse_current_authority_v2 as auth

NOW = datetime(2026, 9, 15, 1, 35, 0, tzinfo=timezone.utc)


def payload(decision="SELECTED", reasons=None):
    return {
        "schema_version": "outbound-muse-publication-election-receipt/v2",
        "request_sha256": "a" * 64,
        "request_id": "req-00000001",
        "publication_key": "b" * 64,
        "candidate_sha256": "c" * 64,
        "claimant": "ZIQ-K4R9",
        "operation_id": "OP-A",
        "lease_binding_sha256": "d" * 64,
        "snapshot_sha256": "e" * 64,
        "decision": decision,
        "reasons": [] if reasons is None else reasons,
        "compiled_at": "2000-01-01T00:00:00Z",
        "request_message_ts": "1789440000.000001",
        "selection_message_ts": "1789440010.000002" if decision == "SELECTED" else None,
        "selected_at": "2026-09-15T01:34:50Z" if decision == "SELECTED" else None,
        "selection_binding_sha256": "f" * 64 if decision == "SELECTED" else None,
        "winner_request_id": "req-00000001" if decision == "SELECTED" else None,
        "winner_candidate_sha256": "c" * 64 if decision == "SELECTED" else None,
        "winner_message_ts": "1789440010.000002" if decision == "SELECTED" else None,
        "muse_user_id": "U0C0TKRTQHZ",
        "muse_dm_conversation_id": "D0C1U7TUZEC",
        "requires_current_worker_lease_possession": True,
        "requires_fresh_provider_preflight": True,
        "external_send_authorized": False,
        "side_effects_authorized": False,
    }


def receipt(decision="SELECTED", reasons=None):
    p = payload(decision, reasons)
    return {"payload": p, "receipt_sha256": auth._digest(p)}


class CurrentAuthorityDonorTests(unittest.TestCase):
    def setUp(self):
        self.old = auth._utc_now
        auth._utc_now = lambda: NOW

    def tearDown(self):
        auth._utc_now = self.old

    def test_raw_selected_becomes_hold(self):
        out = auth.seal_untrusted_snapshot_receipt(receipt())
        self.assertEqual(out["payload"]["decision"], "HOLD")
        self.assertIn(auth.UNAUTHENTICATED_SNAPSHOT_REASON, out["payload"]["reasons"])
        self.assertIn(auth.CURRENT_POSITIVE_DISABLED_REASON, out["payload"]["reasons"])
        self.assertTrue(auth.verify_untrusted_snapshot_receipt(out))

    def test_seal_overwrites_caller_selected_clock(self):
        out = auth.seal_untrusted_snapshot_receipt(receipt())
        self.assertEqual(out["payload"]["compiled_at"], "2026-09-15T01:35:00Z")

    def test_selected_authority_fields_are_cleared(self):
        p = auth.seal_untrusted_snapshot_receipt(receipt())["payload"]
        for name in ("selection_message_ts", "selected_at", "selection_binding_sha256", "winner_request_id", "winner_candidate_sha256", "winner_message_ts", "valid_until"):
            self.assertIsNone(p[name])

    def test_side_effect_authority_stays_false(self):
        raw = receipt(); raw["payload"]["external_send_authorized"] = True; raw["payload"]["side_effects_authorized"] = True
        p = auth.seal_untrusted_snapshot_receipt(raw)["payload"]
        self.assertFalse(p["external_send_authorized"]); self.assertFalse(p["side_effects_authorized"])

    def test_forged_selected_with_recomputed_outer_digest_fails(self):
        out = auth.seal_untrusted_snapshot_receipt(receipt())
        out["payload"]["decision"] = "SELECTED"
        out["payload"]["reasons"] = []
        out["receipt_sha256"] = auth._digest(out["payload"])
        self.assertFalse(auth.verify_untrusted_snapshot_receipt(out))

    def test_forged_snapshot_authenticated_flag_fails(self):
        out = auth.seal_untrusted_snapshot_receipt(receipt())
        out["payload"]["snapshot_authenticated"] = True
        out["receipt_sha256"] = auth._digest(out["payload"])
        self.assertFalse(auth.verify_untrusted_snapshot_receipt(out))

    def test_forged_send_authority_fails(self):
        out = auth.seal_untrusted_snapshot_receipt(receipt())
        out["payload"]["external_send_authorized"] = True
        out["receipt_sha256"] = auth._digest(out["payload"])
        self.assertFalse(auth.verify_untrusted_snapshot_receipt(out))

    def test_future_compiled_at_fails_current_verifier(self):
        out = auth.seal_untrusted_snapshot_receipt(receipt())
        out["payload"]["compiled_at"] = "2026-09-15T01:36:00Z"
        out["receipt_sha256"] = auth._digest(out["payload"])
        self.assertFalse(auth.verify_untrusted_snapshot_receipt(out))

    def test_tampered_claimant_fails_inner_binding_even_with_outer_redigest(self):
        out = auth.seal_untrusted_snapshot_receipt(receipt())
        out["payload"]["claimant"] = "Z-TAMPER"
        out["receipt_sha256"] = auth._digest(out["payload"])
        self.assertFalse(auth.verify_untrusted_snapshot_receipt(out))

    def test_negative_receipt_remains_negative(self):
        out = auth.seal_untrusted_snapshot_receipt(receipt("NOT_SELECTED"))
        self.assertEqual(out["payload"]["decision"], "NOT_SELECTED")
        self.assertEqual(out["payload"]["reasons"], [])
        self.assertTrue(auth.verify_untrusted_snapshot_receipt(out))

    def test_other_winner_negative_is_sanitized_and_verifiable(self):
        raw = receipt("NOT_SELECTED")
        raw["payload"]["winner_request_id"] = "req-00000002"
        raw["payload"]["winner_candidate_sha256"] = "9" * 64
        raw["payload"]["winner_message_ts"] = "1789440010.000002"
        raw["receipt_sha256"] = auth._digest(raw["payload"])

        out = auth.seal_untrusted_snapshot_receipt(raw)
        self.assertEqual(out["payload"]["decision"], "NOT_SELECTED")
        for name in auth._SELECTION_FIELDS + auth._WINNER_FIELDS:
            self.assertIsNone(out["payload"][name])
        self.assertTrue(auth.verify_untrusted_snapshot_receipt(out))

    def test_hold_must_have_reason(self):
        raw = receipt("HOLD", [])
        with self.assertRaises(ValueError): auth.seal_untrusted_snapshot_receipt(raw)

    def test_non_selected_cannot_smuggle_selection_or_winner_fields(self):
        authority_fields = auth._SELECTION_FIELDS + auth._WINNER_FIELDS
        for field in authority_fields:
            with self.subTest(field=field):
                out = auth.seal_untrusted_snapshot_receipt(receipt("NOT_SELECTED"))
                out["payload"][field] = (
                    "2026-09-15T01:34:50Z" if field == "selected_at"
                    else "1789440010.000002" if field.endswith("_ts")
                    else "attacker-value"
                )
                out["receipt_sha256"] = auth._digest(out["payload"])
                self.assertFalse(auth.verify_untrusted_snapshot_receipt(out))


if __name__ == "__main__":
    unittest.main()
