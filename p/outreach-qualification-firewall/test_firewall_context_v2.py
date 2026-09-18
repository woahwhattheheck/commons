from __future__ import annotations

import copy
import hashlib
import hmac
import os
import sys
import unittest
from datetime import timedelta
from pathlib import Path

TEST_WRITER_KEY_HEX = "11" * 32
TEST_CONTEXT_KEY_HEX = "22" * 32
EVIL_CONTEXT_KEY_HEX = "33" * 32
os.environ.setdefault("OUTREACH_WRITER_LEASE_AUTHORITY_KEY_HEX", TEST_WRITER_KEY_HEX)
os.environ.setdefault("OUTREACH_CONTEXT_AUTHORITY_KEY_HEX", TEST_CONTEXT_KEY_HEX)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import outreach_qualification_firewall as fw  # noqa: E402
import firewall_model as model_impl  # noqa: E402
import context_authority as context_impl  # noqa: E402

HIST = "2026-09-17T20:00:00Z"


def packet():
    return fw.strict_json_loads((ROOT / "demo.json").read_text())


def context_tag(kind, payload, key_hex=TEST_CONTEXT_KEY_HEX):
    return hmac.new(
        bytes.fromhex(key_hex),
        fw.canonical_json({
            "domain": "outreach-qualification-firewall.context.v2",
            "kind": kind,
            "payload": payload,
        }),
        hashlib.sha256,
    ).hexdigest()


def resign_identity(data, key_hex=TEST_CONTEXT_KEY_HEX):
    unsigned = {k: v for k, v in data["identity_binding"].items() if k != "auth_tag_hex"}
    data["identity_binding"]["auth_tag_hex"] = context_tag("IDENTITY", unsigned, key_hex)


def resign_relationship(data, observed=None, valid_until=None, key_hex=TEST_CONTEXT_KEY_HEX):
    if observed is not None:
        data["contact"]["relationship_observed_at"] = fw._utc_text(observed)
    if valid_until is not None:
        data["contact"]["relationship_valid_until"] = fw._utc_text(valid_until)
    source = fw._validate_source(copy.deepcopy(data["source_packet"]))
    contact = fw._validate_contact(copy.deepcopy(data["contact"]))
    payload = model_impl._relationship_authority_payload(
        source, data["source_packet_sha256"], contact, data["identity_binding"]
    )
    data["contact"]["relationship_authority_tag_hex"] = context_tag("RELATIONSHIP", payload, key_hex)


def rebind_and_resign_lease(data):
    normalized = fw.normalize_packet(data)
    data["writer_lease"]["collision_key"] = fw.compute_dedupe_key(
        normalized["source_packet"], normalized["contact"]
    )
    lease = data["writer_lease"]
    message = {
        k: lease[k]
        for k in ("lease_id", "collision_key", "seat", "session_nonce", "issued_at", "expires_at", "status")
    }
    lease["authority_tag_hex"] = hmac.new(
        bytes.fromhex(TEST_WRITER_KEY_HEX),
        fw.canonical_json(message),
        hashlib.sha256,
    ).hexdigest()


def prepare_current(data, *, relationship_state="OPEN", relationship_before_lease=False):
    now = fw._process_utc_now()
    data["writer_lease"]["issued_at"] = fw._utc_text(now - timedelta(seconds=60))
    data["writer_lease"]["expires_at"] = fw._utc_text(now + timedelta(seconds=300))
    data["writer_lease"]["status"] = "GO"
    data["contact"]["relationship_state"] = relationship_state
    relationship_observed = now - timedelta(seconds=120 if relationship_before_lease else 30)
    resign_relationship(data, relationship_observed, now + timedelta(seconds=240))
    rebind_and_resign_lease(data)
    return now


class ContextAuthorityV2Tests(unittest.TestCase):
    def test_aliases_converge_to_same_canonical_dedupe_key(self):
        a = packet()
        b = packet()
        b["contact"]["org_ref"] = "synthetic-org-alias"
        b["contact"]["purpose_ref"] = "qualification-alias"
        b["identity_binding"]["org_ref"] = "synthetic-org-alias"
        b["identity_binding"]["purpose_ref"] = "qualification-alias"
        resign_identity(b)

        na = fw.normalize_packet(a)
        nb = fw.normalize_packet(b)
        self.assertTrue(nb["identity_binding"]["authority_authenticated"])
        self.assertEqual(
            fw.compute_dedupe_key(na["source_packet"], na["contact"]),
            fw.compute_dedupe_key(nb["source_packet"], nb["contact"]),
        )

    def test_genuinely_distinct_canonical_purpose_remains_distinct(self):
        a = packet()
        b = packet()
        b["identity_binding"]["canonical_purpose_id"] = "purpose:distinct"
        resign_identity(b)
        resign_relationship(b)

        na = fw.normalize_packet(a)
        nb = fw.normalize_packet(b)
        self.assertNotEqual(
            fw.compute_dedupe_key(na["source_packet"], na["contact"]),
            fw.compute_dedupe_key(nb["source_packet"], nb["contact"]),
        )

    def test_alias_remint_without_identity_authority_holds(self):
        data = packet()
        data["contact"]["org_ref"] = "synthetic-org-alias"
        data["identity_binding"]["org_ref"] = "synthetic-org-alias"
        out = fw.compile_historical(data, as_of=HIST)
        self.assertFalse(out["qualified_for_owner_review"])
        self.assertIn("HOLD_IDENTITY_AUTHORITY", out["hold_reasons"])

    def test_relationship_head_tamper_without_authority_holds(self):
        data = packet()
        data["contact"]["relationship_head_sha256"] = "6" * 64
        out = fw.compile_historical(data, as_of=HIST)
        self.assertFalse(out["qualified_for_owner_review"])
        self.assertIn("HOLD_RELATIONSHIP_AUTHORITY", out["hold_reasons"])

    def test_old_open_plus_fresh_go_cannot_authorize(self):
        data = packet()
        prepare_current(data, relationship_before_lease=True)
        out = fw.compile_current(data)
        self.assertTrue(out["qualified_for_owner_review"])
        self.assertFalse(out["authorized_to_send"])
        self.assertIn("HOLD_RELATIONSHIP_PRECEDES_LEASE", out["hold_reasons"])

    def test_post_lease_current_open_can_authorize(self):
        data = packet()
        prepare_current(data)
        out = fw.compile_current(data)
        self.assertTrue(out["qualified_for_owner_review"])
        self.assertTrue(out["authorized_to_send"])
        self.assertEqual(out["send_state"], "AUTHORIZED_TO_SEND")
        self.assertTrue(fw.verify_receipt(data, out))

    def test_newer_authenticated_dnr_after_lease_blocks(self):
        data = packet()
        prepare_current(data, relationship_state="DNR")
        out = fw.compile_current(data)
        self.assertFalse(out["qualified_for_owner_review"])
        self.assertFalse(out["authorized_to_send"])
        self.assertIn("HOLD_RELATIONSHIP", out["hold_reasons"])

    def test_expired_relationship_snapshot_holds(self):
        data = packet()
        observed = fw._utc("2026-09-17T19:50:00Z", "observed")
        valid_until = fw._utc("2026-09-17T19:55:00Z", "valid")
        resign_relationship(data, observed, valid_until)
        out = fw.compile_historical(data, as_of=HIST)
        self.assertFalse(out["qualified_for_owner_review"])
        self.assertIn("HOLD_RELATIONSHIP_STALE", out["hold_reasons"])

    def test_identity_binding_is_exact_source_generation_bound(self):
        data = packet()
        data["identity_binding"]["source_packet_sha256"] = "f" * 64
        resign_identity(data)
        with self.assertRaisesRegex(fw.FirewallError, "source/opportunity mismatch"):
            fw.normalize_packet(data)

    def test_process_context_key_default_resists_late_global_rebind(self):
        data = packet()
        original = context_impl._PROCESS_CONTEXT_AUTHORITY_KEY
        try:
            context_impl._PROCESS_CONTEXT_AUTHORITY_KEY = bytes.fromhex(EVIL_CONTEXT_KEY_HEX)
            resign_identity(data, EVIL_CONTEXT_KEY_HEX)
            resign_relationship(data, key_hex=EVIL_CONTEXT_KEY_HEX)
            out = fw.compile_historical(data, as_of=HIST)
        finally:
            context_impl._PROCESS_CONTEXT_AUTHORITY_KEY = original
        self.assertFalse(out["qualified_for_owner_review"])
        self.assertIn("HOLD_IDENTITY_AUTHORITY", out["hold_reasons"])
        self.assertIn("HOLD_RELATIONSHIP_AUTHORITY", out["hold_reasons"])


if __name__ == "__main__":
    unittest.main()
