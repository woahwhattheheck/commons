import hashlib
import hmac
import json
import os
import unittest
from datetime import datetime, timedelta, timezone

REAL_KEY_HEX = "31" * 32
REAL_KEY = bytes.fromhex(REAL_KEY_HEX)
EVIL_KEY = bytes.fromhex("22" * 32)
_PREIMPORT_KEY = os.environ.get("PAYOFF_PATH_EVIDENCE_AUTHORITY_KEY_HEX")
os.environ["PAYOFF_PATH_EVIDENCE_AUTHORITY_KEY_HEX"] = REAL_KEY_HEX

from revenue.payoff_path_ledger import core
A = "a" * 64
B = "b" * 64
C = "c" * 64


def ts(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def tag(kind, row, key):
    unsigned = {k: v for k, v in row.items() if k != "auth_tag_hex"}
    payload = {"domain": "commons-payoff-path-evidence/v2", "kind": kind, "row": unsigned}
    row["auth_tag_hex"] = hmac.new(key, canonical(payload), hashlib.sha256).hexdigest()
    return row


def make_packet(key=REAL_KEY):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    term = tag("TERM", {
        "evidence_id": "e1",
        "subject_work_id": "work-1",
        "subject_generation_sha256": A,
        "evidence_class": "BUG_BOUNTY",
        "source_id": "source-1",
        "source_sha256": B,
        "observed_at_utc": ts(now - timedelta(minutes=2)),
        "valid_until_utc": ts(now + timedelta(hours=2)),
        "amount_mode": "EXACT",
        "amount_minor": 9000,
        "currency": "USD",
        "auth_tag_hex": "0" * 64,
    }, key)
    p = {
        "schema": core.SCHEMA_INPUT,
        "subject_work_id": "work-1",
        "subject_generation_sha256": A,
        "payoff_class": "BUG_BOUNTY",
        "evidence_scope_status": "COMPLETE",
        "scope_attestation": None,
        "term_evidence": [term],
        "outcome_evidence": [],
        "conversion_plan": None,
    }
    census = hashlib.sha256(canonical({"term_evidence": p["term_evidence"], "outcome_evidence": []})).hexdigest()
    p["scope_attestation"] = tag("SCOPE", {
        "attestation_id": "scope-1",
        "subject_work_id": "work-1",
        "subject_generation_sha256": A,
        "census_source_id": "census-source",
        "census_source_sha256": C,
        "evidence_census_sha256": census,
        "observed_at_utc": ts(now - timedelta(minutes=1)),
        "valid_until_utc": ts(now + timedelta(hours=1)),
        "auth_tag_hex": "0" * 64,
    }, key)
    return p


class V4BoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = _PREIMPORT_KEY

    @classmethod
    def tearDownClass(cls):
        if cls.old is None:
            os.environ.pop(core.EVIDENCE_AUTH_ENV, None)
        else:
            os.environ[core.EVIDENCE_AUTH_ENV] = cls.old

    def test_legitimate_packet_survives_bytes_global_rebind(self):
        class FakeBytes:
            @staticmethod
            def fromhex(_raw):
                return EVIL_KEY
        core.bytes = FakeBytes
        try:
            self.assertEqual(core.compile_current(make_packet(REAL_KEY))["state"], "PAYOFF_BOUND")
        finally:
            del core.bytes

    def test_attacker_key_cannot_be_substituted_via_bytes_global(self):
        class FakeBytes:
            @staticmethod
            def fromhex(_raw):
                return EVIL_KEY
        core.bytes = FakeBytes
        try:
            with self.assertRaises(core.GateError):
                core.compile_current(make_packet(EVIL_KEY))
        finally:
            del core.bytes

    def test_builtin_type_names_rebind_do_not_change_compile(self):
        poison = object()
        names = ("str", "dict", "list", "set", "bool", "int", "len", "any", "all", "type")
        for name in names:
            setattr(core, name, poison)
        try:
            self.assertEqual(core.compile_current(make_packet(REAL_KEY))["state"], "PAYOFF_BOUND")
        finally:
            for name in names:
                delattr(core, name)

    def test_post_import_env_cannot_replace_captured_authority(self):
        old = os.environ.get(core.EVIDENCE_AUTH_ENV)
        os.environ[core.EVIDENCE_AUTH_ENV] = "22" * 32
        try:
            self.assertEqual(
                core.compile_current(make_packet(REAL_KEY))["state"],
                "PAYOFF_BOUND",
            )
            with self.assertRaises(core.GateError):
                core.compile_current(make_packet(EVIL_KEY))
        finally:
            if old is None:
                os.environ.pop(core.EVIDENCE_AUTH_ENV, None)
            else:
                os.environ[core.EVIDENCE_AUTH_ENV] = old

    def test_post_import_env_removal_or_malformed_value_is_inert(self):
        old = os.environ.get(core.EVIDENCE_AUTH_ENV)
        try:
            os.environ.pop(core.EVIDENCE_AUTH_ENV, None)
            self.assertEqual(
                core.compile_current(make_packet(REAL_KEY))["state"],
                "PAYOFF_BOUND",
            )
            os.environ[core.EVIDENCE_AUTH_ENV] = "not-lowercase-hex"
            self.assertEqual(
                core.compile_current(make_packet(REAL_KEY))["state"],
                "PAYOFF_BOUND",
            )
        finally:
            if old is None:
                os.environ.pop(core.EVIDENCE_AUTH_ENV, None)
            else:
                os.environ[core.EVIDENCE_AUTH_ENV] = old

    def test_raw_bytes_rejected_before_unbounded_parse(self):
        with self.assertRaisesRegex(core.GateError, "byte limit"):
            core.loads_strict_json(b" " * (core.MAX_JSON_INPUT_BYTES + 1))

    def test_raw_str_rejected_before_unbounded_parse(self):
        with self.assertRaisesRegex(core.GateError, "byte limit"):
            core.loads_strict_json(" " * (core.MAX_JSON_INPUT_BYTES + 1))

    def test_multibyte_str_enforces_encoded_byte_limit(self):
        raw = "é" * (core.MAX_JSON_INPUT_BYTES // 2 + 1)
        with self.assertRaisesRegex(core.GateError, "byte limit"):
            core.loads_strict_json(raw)

    def test_at_limit_small_valid_json_still_parses(self):
        self.assertEqual(core.loads_strict_json('{"a":1}'), {"a": 1})

    def test_v4_receipt_generation(self):
        packet = make_packet()
        receipt = core.compile_current(packet)
        self.assertEqual(receipt["schema"], "commons-payoff-path-receipt/v4")
        self.assertEqual(receipt["compiler_id"], "commons.payoff-path-ledger/v4")
        self.assertTrue(core.verify_integrity(packet, receipt))


if __name__ == "__main__":
    unittest.main()
