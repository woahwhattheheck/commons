from __future__ import annotations

import hashlib
import hmac
import inspect
import os
import sys
import unittest
from pathlib import Path

TEST_WRITER_KEY_HEX = "11" * 32
TEST_CONTEXT_KEY_HEX = "22" * 32
EVIL_KEY_HEX = "33" * 32

os.environ.setdefault("OUTREACH_WRITER_LEASE_AUTHORITY_KEY_HEX", TEST_WRITER_KEY_HEX)
os.environ.setdefault("OUTREACH_CONTEXT_AUTHORITY_KEY_HEX", TEST_CONTEXT_KEY_HEX)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import outreach_qualification_firewall as fw  # noqa: E402
import context_authority as context_impl  # noqa: E402
import firewall_decision as decision_impl  # noqa: E402
import writer_authority as writer_impl  # noqa: E402

HIST = "2026-09-17T20:00:00Z"


def packet():
    return fw.strict_json_loads((ROOT / "demo.json").read_text())


def context_message(kind, payload):
    return fw.canonical_json({
        "domain": "outreach-qualification-firewall.context.v2",
        "kind": kind,
        "payload": payload,
    })


def writer_message(row):
    return fw.canonical_json({
        key: row[key]
        for key in (
            "lease_id",
            "collision_key",
            "seat",
            "session_nonce",
            "issued_at",
            "expires_at",
            "status",
        )
    })


class TrustRootClosureTests(unittest.TestCase):
    def test_public_current_and_verifier_signatures_have_no_injection_kwargs(self):
        current = inspect.signature(fw.compile_current)
        self.assertEqual(list(current.parameters), ["payload"])

        historical = inspect.signature(fw.compile_historical)
        self.assertEqual(list(historical.parameters), ["payload", "as_of"])
        self.assertEqual(
            historical.parameters["as_of"].kind,
            inspect.Parameter.KEYWORD_ONLY,
        )

        verifier = inspect.signature(fw.verify_receipt)
        self.assertEqual(list(verifier.parameters), ["payload", "decision"])

        with self.assertRaises(TypeError):
            fw.compile_current(packet(), _now=lambda: fw._utc(HIST, "fake"))
        receipt = fw.compile_historical(packet(), as_of=HIST)
        with self.assertRaises(TypeError):
            fw.verify_receipt(
                packet(),
                receipt,
                _now=lambda: fw._utc(HIST, "fake"),
            )

    def test_module_clock_rebind_cannot_move_current_evaluation(self):
        original = decision_impl._CURRENT_CLOCK
        decision_impl._CURRENT_CLOCK = lambda: fw._utc(
            "2000-01-01T00:00:00Z",
            "fake",
        )
        try:
            out = fw.compile_current(packet())
        finally:
            decision_impl._CURRENT_CLOCK = original
        self.assertFalse(out["evaluated_at"].startswith("2000-"))

    def test_context_verifier_kwdefaults_poison_cannot_forge_identity(self):
        data = packet()
        unsigned = {
            key: value
            for key, value in data["identity_binding"].items()
            if key != "auth_tag_hex"
        }
        data["identity_binding"]["auth_tag_hex"] = hmac.new(
            bytes.fromhex(EVIL_KEY_HEX),
            context_message("IDENTITY", unsigned),
            hashlib.sha256,
        ).hexdigest()

        original = context_impl.verify_context_authority.__kwdefaults__
        context_impl.verify_context_authority.__kwdefaults__ = {
            "_key": bytes.fromhex(EVIL_KEY_HEX),
            "_compare": lambda *_: True,
            "_message": lambda *_: b"attacker",
        }
        try:
            out = fw.compile_historical(data, as_of=HIST)
        finally:
            context_impl.verify_context_authority.__kwdefaults__ = original

        self.assertFalse(out["qualified_for_owner_review"])
        self.assertIn("HOLD_IDENTITY_AUTHORITY", out["hold_reasons"])

    def test_writer_verifier_kwdefaults_poison_cannot_forge_go(self):
        data = packet()
        data["writer_lease"]["authority_tag_hex"] = hmac.new(
            bytes.fromhex(EVIL_KEY_HEX),
            writer_message(data["writer_lease"]),
            hashlib.sha256,
        ).hexdigest()

        original = writer_impl.verify_writer_lease_authority.__kwdefaults__
        writer_impl.verify_writer_lease_authority.__kwdefaults__ = {
            "_key": bytes.fromhex(EVIL_KEY_HEX),
            "_compare_digest": lambda *_: True,
            "_message": lambda *_: b"attacker",
        }
        try:
            out = fw.compile_historical(data, as_of=HIST)
            normalized = fw.normalize_packet(data)
        finally:
            writer_impl.verify_writer_lease_authority.__kwdefaults__ = original

        self.assertIn("HOLD_HISTORICAL_EVALUATION", out["hold_reasons"])
        self.assertFalse(normalized["writer_lease"]["authority_authenticated"])

    def test_hard_false_defaults_and_module_rebind_cannot_widen_authority(self):
        fn = decision_impl._hard_false_authority
        original_defaults = fn.__defaults__
        original_kwdefaults = fn.__kwdefaults__
        original_global = decision_impl._hard_false_authority

        fn.__defaults__ = ((
            ("package_performs_send", True),
            ("cash_or_revenue_authority", True),
        ),)
        fn.__kwdefaults__ = {"_items": (("cash_or_revenue_authority", True),)}
        decision_impl._hard_false_authority = lambda: {
            "package_performs_send": True,
            "buyer_qualified_or_interested": True,
            "submission_authorized": True,
            "signature_or_contract_authority": True,
            "award_or_payment_authority": True,
            "cash_or_revenue_authority": True,
        }
        try:
            out = fw.compile_historical(packet(), as_of=HIST)
            self.assertTrue(fw.verify_receipt(packet(), out))
        finally:
            fn.__defaults__ = original_defaults
            fn.__kwdefaults__ = original_kwdefaults
            decision_impl._hard_false_authority = original_global

        self.assertEqual(
            out["authority"],
            {
                "package_performs_send": False,
                "buyer_qualified_or_interested": False,
                "submission_authorized": False,
                "signature_or_contract_authority": False,
                "award_or_payment_authority": False,
                "cash_or_revenue_authority": False,
            },
        )

    def test_sealed_codec_and_hmac_public_leaves_have_no_behavior_defaults(self):
        for fn in (
            fw.canonical_json,
            fw.sha256_hex,
            fw._utc,
            fw._process_utc_now,
            context_impl.context_authority_message,
            context_impl.verify_context_authority,
            writer_impl.writer_lease_message,
            writer_impl.verify_writer_lease_authority,
        ):
            with self.subTest(fn=fn.__name__):
                self.assertIsNone(fn.__defaults__)
                self.assertIsNone(fn.__kwdefaults__)

    def test_context_and_writer_process_key_globals_are_not_live_trust_roots(self):
        data = packet()
        context_original = context_impl._PROCESS_CONTEXT_AUTHORITY_KEY
        writer_original = writer_impl._PROCESS_WRITER_AUTHORITY_KEY
        try:
            context_impl._PROCESS_CONTEXT_AUTHORITY_KEY = bytes.fromhex(EVIL_KEY_HEX)
            writer_impl._PROCESS_WRITER_AUTHORITY_KEY = bytes.fromhex(EVIL_KEY_HEX)
            normalized = fw.normalize_packet(data)
        finally:
            context_impl._PROCESS_CONTEXT_AUTHORITY_KEY = context_original
            writer_impl._PROCESS_WRITER_AUTHORITY_KEY = writer_original

        self.assertTrue(normalized["identity_binding"]["authority_authenticated"])
        self.assertTrue(normalized["contact"]["relationship_authority_authenticated"])
        self.assertTrue(normalized["writer_lease"]["authority_authenticated"])


if __name__ == "__main__":
    unittest.main()
