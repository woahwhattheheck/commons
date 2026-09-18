from __future__ import annotations

import hashlib
import hmac
import inspect
import json
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




def closure_cell(fn, name):
    names = fn.__code__.co_freevars
    if name not in names or fn.__closure__ is None:
        raise AssertionError(f"{fn!r} has no closure cell {name!r}")
    return fn.__closure__[names.index(name)]


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

    def test_reflective_interpreter_tamper_is_explicitly_out_of_scope(self):
        self.assertEqual(fw.THREAT_MODEL_ID, "trusted-python-interpreter-v1")
        self.assertIs(fw.REFLECTIVE_INTERPRETER_TAMPER_IN_SCOPE, False)
        self.assertIs(fw.REQUIRES_ISOLATED_PROCESS_FOR_UNTRUSTED_CODE, True)
        readme = (ROOT / "README.md").read_text()
        self.assertIn("outside this package's trust boundary", readme)
        self.assertIn("__closure__[...].cell_contents", readme)
        self.assertIn("separately isolated and authenticated process/provider boundary", readme)

    def test_out_of_scope_clock_cell_mutation_can_resurrect_old_current_time(self):
        self.assertIs(fw.REFLECTIVE_INTERPRETER_TAMPER_IN_SCOPE, False)
        cell = closure_cell(decision_impl.compile_current, "current_clock")
        original = cell.cell_contents
        try:
            cell.cell_contents = lambda: fw._utc(HIST, "reflective-tamper")
            out = fw.compile_current(packet())
        finally:
            cell.cell_contents = original

        # Boundary proof: malicious code already rewriting live closure state can
        # defeat an in-process current-time assertion. This is intentionally
        # documented as host-interpreter compromise, not a supported attacker.
        self.assertEqual(out["evaluation_mode"], "CURRENT_PROCESS")
        self.assertTrue(out["authorized_to_send"])

    def test_out_of_scope_context_compare_cell_can_forge_context_tags(self):
        self.assertIs(fw.REFLECTIVE_INTERPRETER_TAMPER_IN_SCOPE, False)
        data = packet()
        data["identity_binding"]["auth_tag_hex"] = "0" * 64
        data["contact"]["relationship_authority_tag_hex"] = "0" * 64
        cell = closure_cell(context_impl.verify_context_authority, "compare_digest")
        original = cell.cell_contents
        try:
            cell.cell_contents = lambda *_: True
            normalized = fw.normalize_packet(data)
        finally:
            cell.cell_contents = original

        self.assertTrue(normalized["identity_binding"]["authority_authenticated"])
        self.assertTrue(normalized["contact"]["relationship_authority_authenticated"])

    def test_out_of_scope_writer_compare_cell_can_forge_go_tag(self):
        self.assertIs(fw.REFLECTIVE_INTERPRETER_TAMPER_IN_SCOPE, False)
        data = packet()
        data["writer_lease"]["authority_tag_hex"] = "0" * 64
        cell = closure_cell(writer_impl.verify_writer_lease_authority, "compare_digest")
        original = cell.cell_contents
        try:
            cell.cell_contents = lambda *_: True
            normalized = fw.normalize_packet(data)
        finally:
            cell.cell_contents = original

        self.assertTrue(normalized["writer_lease"]["authority_authenticated"])

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

    def test_json_dumps_kwdefault_cannot_transplant_writer_tag(self):
        data = packet()
        authentic = dict(data["writer_lease"])
        replay = writer_message(authentic).decode("utf-8")
        authentic_tag = authentic["authority_tag_hex"]

        class ReplayEncoder(json.JSONEncoder):
            def encode(self, _value):
                return replay

        data["writer_lease"]["lease_id"] = "forged-lease"
        data["writer_lease"]["authority_tag_hex"] = authentic_tag
        kw = json.dumps.__kwdefaults__
        original_cls = kw["cls"]
        try:
            kw["cls"] = ReplayEncoder
            normalized = fw.normalize_packet(data)
        finally:
            kw["cls"] = original_cls

        self.assertFalse(
            normalized["writer_lease"]["authority_authenticated"]
        )

    def test_json_dumps_kwdefault_cannot_transplant_context_tag(self):
        data = packet()
        authentic = dict(data["identity_binding"])
        unsigned = {
            key: value
            for key, value in authentic.items()
            if key != "auth_tag_hex"
        }
        replay = context_message("IDENTITY", unsigned).decode("utf-8")
        authentic_tag = authentic["auth_tag_hex"]

        class ReplayEncoder(json.JSONEncoder):
            def encode(self, _value):
                return replay

        data["identity_binding"]["binding_id"] = "binding-forged"
        data["identity_binding"]["auth_tag_hex"] = authentic_tag
        kw = json.dumps.__kwdefaults__
        original_cls = kw["cls"]
        try:
            kw["cls"] = ReplayEncoder
            normalized = fw.normalize_packet(data)
        finally:
            kw["cls"] = original_cls

        self.assertFalse(
            normalized["identity_binding"]["authority_authenticated"]
        )

    def test_json_loads_kwdefault_cannot_bypass_duplicate_key_guard(self):
        class BypassDecoder(json.JSONDecoder):
            def decode(self, _raw):
                return {"accepted": True}

        kw = json.loads.__kwdefaults__
        original_cls = kw["cls"]
        try:
            kw["cls"] = BypassDecoder
            with self.assertRaises(ValueError):
                fw.strict_json_loads('{"x":1,"x":2}')
        finally:
            kw["cls"] = original_cls

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
