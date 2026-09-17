from __future__ import annotations

import copy
import hashlib
import hmac
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

TEST_WRITER_KEY_HEX = "11" * 32
os.environ.setdefault("OUTREACH_WRITER_LEASE_AUTHORITY_KEY_HEX", TEST_WRITER_KEY_HEX)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import outreach_qualification_firewall as fw  # noqa: E402
import firewall_codec as codec  # noqa: E402
import firewall_decision as decision_impl  # noqa: E402

HIST = "2026-09-17T20:00:00Z"


def packet():
    return fw.strict_json_loads((ROOT / "demo.json").read_text())


def resign_source(data):
    source = fw._validate_source(copy.deepcopy(data["source_packet"]))
    data["source_packet"] = source
    data["source_packet_sha256"] = fw.sha256_hex(fw.canonical_json(source))


def resign_lease(data):
    lease = data["writer_lease"]
    message = {k: lease[k] for k in ("lease_id", "collision_key", "seat", "session_nonce", "issued_at", "expires_at", "status")}
    lease["authority_tag_hex"] = hmac.new(
        bytes.fromhex(TEST_WRITER_KEY_HEX), fw.canonical_json(message), hashlib.sha256
    ).hexdigest()


class FirewallHostileTests(unittest.TestCase):
    def test_invalid_url_port_is_domain_error(self):
        data = packet(); data["source_packet"]["source_uri"] = "https://example.com:abc/opportunity/001"
        with self.assertRaises(fw.FirewallError): resign_source(data)

    def test_route_and_contact_aliases_converge_semantic_dedupe(self):
        a = packet(); b = packet(); b["contact"]["route"] = "OTHER@EXAMPLE.COM"; b["contact"]["contact_ref"] = "different-contact"
        na = fw.normalize_packet(a); nb = fw.normalize_packet(b)
        self.assertEqual(fw.compute_dedupe_key(na["source_packet"], na["contact"]), fw.compute_dedupe_key(nb["source_packet"], nb["contact"]))

    def test_missing_lease_holds_send_without_blocking_owner_review(self):
        data = packet(); data["writer_lease"] = None; out = fw.compile_current(data)
        self.assertTrue(out["qualified_for_owner_review"]); self.assertFalse(out["authorized_to_send"]); self.assertIn("HOLD_WRITER_LEASE_MISSING", out["hold_reasons"])

    def test_forged_go_without_valid_host_tag_never_authorizes(self):
        data = packet(); now = fw._process_utc_now()
        data["writer_lease"]["issued_at"] = fw._utc_text(now - timedelta(seconds=30))
        data["writer_lease"]["expires_at"] = fw._utc_text(now + timedelta(seconds=300))
        data["writer_lease"]["authority_tag_hex"] = "0" * 64
        out = fw.compile_current(data)
        self.assertFalse(out["authorized_to_send"])
        self.assertIn("HOLD_WRITER_LEASE_UNAUTHENTICATED", out["hold_reasons"])

    def test_alternate_submission_route_without_bound_digest_rejected(self):
        data = packet(); data["source_packet"]["submission_route"] = "https://example.com/alternate"
        with self.assertRaisesRegex(fw.FirewallError, "source_packet digest mismatch"): fw.compile_historical(data, as_of=HIST)

    def test_source_tamper_without_digest_rejected(self):
        data = packet(); data["source_packet"]["deadline_at"] = "2098-01-01T00:00:00Z"
        with self.assertRaisesRegex(fw.FirewallError, "source_packet digest mismatch"): fw.compile_historical(data, as_of=HIST)

    def test_submission_route_must_be_canonical_and_registration_coherent(self):
        data = packet(); data["source_packet"]["submission_route"] = "HTTP://example.com/submit"
        with self.assertRaises(fw.FirewallError): resign_source(data)
        data = packet(); data["source_packet"]["registration_required"] = False; data["source_packet"]["registration_state"] = "READY"
        with self.assertRaises(fw.FirewallError): resign_source(data)

    def test_strict_json_hostiles(self):
        for raw in ('{"a":1,"a":2}', '{"a":1.2}', '{"a":NaN}', '{"a":"\\u200b"}', '{"a":111111111111111111111}'):
            with self.subTest(raw=raw):
                with self.assertRaises(fw.FirewallError): fw.strict_json_loads(raw)

    def test_bool_int_alias_rejected(self):
        data = packet(); data["economics"]["amount_minor"] = True
        with self.assertRaises(fw.FirewallError): fw.compile_historical(data, as_of=HIST)

    def test_current_clock_ignores_ordinary_datetime_global_rebind(self):
        class FakeDatetime:
            @staticmethod
            def fromisoformat(value): return fw._datetime.fromisoformat(value)
            @staticmethod
            def fromtimestamp(*_): return fw._datetime(2000, 1, 1, tzinfo=fw._timezone.utc)
        original = fw._datetime; fw._datetime = FakeDatetime
        try: out = fw.compile_current(packet())
        finally: fw._datetime = original
        self.assertFalse(out["evaluated_at"].startswith("2000-"))

    def test_receipt_tamper_and_reseal_rejected_semantically(self):
        data = packet(); out = fw.compile_historical(data, as_of=HIST); tampered = copy.deepcopy(out); tampered["qualified_for_owner_review"] = False
        unsigned = dict(tampered); unsigned.pop("receipt_sha256"); tampered["receipt_sha256"] = fw.sha256_hex(fw.canonical_json(unsigned))
        with self.assertRaisesRegex(fw.FirewallError, "semantic receipt mismatch"): fw.verify_receipt(data, tampered)

    def test_authority_widening_rejected(self):
        data = packet(); out = fw.compile_historical(data, as_of=HIST); tampered = copy.deepcopy(out); tampered["authority"]["cash_or_revenue_authority"] = True
        unsigned = dict(tampered); unsigned.pop("receipt_sha256"); tampered["receipt_sha256"] = fw.sha256_hex(fw.canonical_json(unsigned))
        with self.assertRaisesRegex(fw.FirewallError, "authority ceiling changed"): fw.verify_receipt(data, tampered)

    def test_mutable_legacy_authority_mapping_cannot_widen_trust_path(self):
        original = dict(codec.AUTHORITY_FALSE)
        try:
            codec.AUTHORITY_FALSE["cash_or_revenue_authority"] = True
            out = fw.compile_historical(packet(), as_of=HIST)
            self.assertFalse(out["authority"]["cash_or_revenue_authority"])
            self.assertTrue(fw.verify_receipt(packet(), out))
        finally:
            codec.AUTHORITY_FALSE.clear(); codec.AUTHORITY_FALSE.update(original)

    def test_current_receipt_replay_after_lease_expiry_is_rejected(self):
        data = packet()
        old = fw._utc("2026-09-17T20:00:00Z", "old")
        data["writer_lease"]["issued_at"] = "2026-09-17T19:59:00Z"
        data["writer_lease"]["expires_at"] = "2026-09-17T20:01:00Z"
        resign_lease(data)
        normalized = fw.normalize_packet(data)
        receipt = decision_impl._evaluate(normalized, old, current_process=True)
        self.assertTrue(receipt["authorized_to_send"])
        with self.assertRaisesRegex(fw.FirewallError, "current send authorization is stale"):
            fw.verify_receipt(data, receipt)

    def test_required_issue_fixtures(self):
        too_short = fw.strict_json_loads((ROOT / "fixture_too_short_unqualified.json").read_text()); out = fw.compile_historical(too_short, as_of=HIST)
        self.assertFalse(out["qualified_for_owner_review"]); self.assertIn("HOLD_RUNWAY", out["hold_reasons"]); self.assertIn("HOLD_QUALIFICATION_UNKNOWN", out["hold_reasons"])
        no_lease = fw.strict_json_loads((ROOT / "fixture_owner_review_no_lease.json").read_text()); out = fw.compile_historical(no_lease, as_of=HIST)
        self.assertTrue(out["qualified_for_owner_review"]); self.assertFalse(out["authorized_to_send"]); self.assertIn("HOLD_WRITER_LEASE_MISSING", out["hold_reasons"])

    def test_cli_historical_current_verify_and_symlink_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ)
            hist = subprocess.run([sys.executable, str(ROOT / "cli.py"), "historical", str(ROOT / "demo.json"), "--as-of", HIST], text=True, capture_output=True, env=env)
            self.assertEqual(hist.returncode, 0, hist.stderr)
            decision_path = Path(td) / "decision.json"; decision_path.write_text(hist.stdout)
            checked = subprocess.run([sys.executable, str(ROOT / "cli.py"), "verify-receipt", str(ROOT / "demo.json"), str(decision_path)], text=True, capture_output=True, env=env)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            current = subprocess.run([sys.executable, str(ROOT / "cli.py"), "current", str(ROOT / "demo.json")], text=True, capture_output=True, env=env)
            self.assertEqual(current.returncode, 0, current.stderr)
            if hasattr(os, "symlink"):
                link = Path(td) / "packet.json"; os.symlink(ROOT / "demo.json", link)
                rejected = subprocess.run([sys.executable, str(ROOT / "cli.py"), "historical", str(link), "--as-of", HIST], text=True, capture_output=True, env=env)
                self.assertEqual(rejected.returncode, 2); self.assertIn("regular non-symlink", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
