from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import revenue.outbound_send_authority.authority as auth

NOW = datetime(2026, 9, 13, 15, 35, 0, tzinfo=timezone.utc)
KEY = b"k" * 32


def canon(obj, newline=False, ascii_only=False):
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=ascii_only).encode("ascii" if ascii_only else "utf-8")
    return raw + (b"\n" if newline else b"")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def guard_receipt(*, offer="pilot", decision="ALLOW_NEW", recipient="buyer@example.com", generated="2026-09-13T15:34:30Z"):
    payload = {
        "schema_version": "outbound-send-guard-receipt/v1",
        "intent": {"intent_id": "intent-001", "recipient": recipient, "offer_id": offer, "requested_at": "2026-09-13T15:34:20Z", "route_kind": "email"},
        "evidence": {"generated_at": generated, "mailbox_complete": True, "mailbox_query_id": "mail-q", "slack_complete": True, "slack_query_id": "slack-q", "intent_sha256": "1"*64, "evidence_sha256": "2"*64, "matched_refs": []},
        "policy": {"cross_offer_cooldown_days": 30, "max_evidence_age_seconds": 900, "max_future_skew_seconds": 300},
        "decision": decision, "authority": "complete", "reasons": ["clean"],
        "latest_outbound_at": None, "latest_inbound_at": None, "reply_message_id": None,
        "side_effects_authorized": False,
    }
    return {"payload": payload, "receipt_sha256": sha(canon(payload, newline=True))}


def bundle(*, offer="pilot", commercial="opportunity-001", claimant="Z-Example", claim_id="claim-001", message=b"raw-rfc822", decision="ALLOW_NEW", issued=None):
    g = guard_receipt(offer=offer, decision=decision)
    gb = json.dumps(g, sort_keys=True).encode()
    l = {"synthetic": "lease-receipt-for-caller"}
    lb = json.dumps(l, sort_keys=True).encode()
    issued_dt = issued or NOW - timedelta(seconds=5)
    payload = {
        "schema_version": auth.APPROVAL_SCHEMA,
        "repo": "woahwhattheheck/commons",
        "buyer_scope": "buyer-001",
        "commercial_scope": commercial,
        "offer_scope": offer,
        "recipient_sha256": sha(b"buyer@example.com"),
        "message_sha256": sha(message),
        "claimant": claimant,
        "claim_id": claim_id,
        "claim_started_at": "2026-09-13T15:34:35Z",
        "anchor_sha": "a" * 40,
        "guard_receipt_sha256": sha(gb),
        "guard_payload_receipt_sha256": g["receipt_sha256"],
        "lease_receipt_sha256": sha(lb),
        "issued_at": auth._fmt(issued_dt),
        "expires_at": auth._fmt(issued_dt + timedelta(seconds=120)),
    }
    approval = auth.sign_host_approval(payload, host_key=KEY)
    ab = json.dumps(approval, sort_keys=True).encode()
    return ab, gb, lb, message


class ConsumeTransport:
    def __init__(self, *, ref_mode="normal"):
        self.refs = {}
        self.ref_mode = ref_mode
        self.calls = []
        self.last_tag_sha = None

    def __call__(self, method, path, body):
        self.calls.append((method, path, body))
        if method == "POST" and path.endswith("/git/tags"):
            self.last_tag_sha = ("a" if self.last_tag_sha is None else "b") * 40
            return 201, {"sha": self.last_tag_sha}
        if method == "POST" and path.endswith("/git/refs"):
            ref = body["ref"]
            if ref in self.refs:
                return 422, {"message": "exists"}
            self.refs[ref] = body["sha"]
            if self.ref_mode == "timeout-after-write":
                return 503, {"message": "unknown"}
            return 201, {"ref": ref, "object": {"sha": body["sha"]}}
        if method == "GET" and "/git/ref/" in path:
            suffix = path.split("/git/ref/", 1)[1]
            ref = "refs/" + suffix
            if ref in self.refs:
                return 200, {"ref": ref, "object": {"sha": self.refs[ref]}}
            return 404, {"message": "missing"}
        raise AssertionError((method, path, body))


class Sender:
    def __init__(self, status=200, body=None):
        self.status = status
        self.body = {"message_id": "provider-msg-1"} if body is None else body
        self.calls = []

    def __call__(self, message, consumption_id):
        self.calls.append((message, consumption_id))
        return self.status, self.body


class Tests(unittest.TestCase):
    def pre(self, *args, expected_claimant="Z-Example", now=NOW):
        with patch.object(auth, "verify_authoritative_receipt", return_value=True):
            return auth._evaluate_at(
                *args[:3], host_key=KEY, lease_transport=lambda *x: (500, {}),
                expected_claimant=expected_claimant, expected_claim_id="claim-001",
                expected_claim_started_at="2026-09-13T15:34:35Z", expected_anchor_sha="a"*40,
                now=now,
            )

    def consume(self, args, consume, sender, **kwargs):
        with patch.object(auth, "verify_authoritative_receipt", return_value=kwargs.pop("lease_ok", True)), patch.object(auth, "_utcnow", return_value=NOW):
            return auth.consume_and_send(
                *args, host_key=KEY, lease_transport=lambda *x: (500, {}), consume_transport=consume,
                send_transport=sender, expected_claimant=kwargs.pop("expected_claimant", "Z-Example"),
                expected_claim_id=kwargs.pop("expected_claim_id", "claim-001"),
                expected_claim_started_at="2026-09-13T15:34:35Z", expected_anchor_sha="a"*40,
            )

    def test_preconditions_never_authorize_send(self):
        args = bundle()
        r = self.pre(*args)
        self.assertEqual(r["payload"]["decision"], "PRECONDITIONS_READY")
        self.assertFalse(r["payload"]["external_send_authorized"])
        self.assertTrue(r["payload"]["consumption_required"])

    def test_live_lease_failure_holds_fabricated_receipt(self):
        args = bundle()
        with patch.object(auth, "verify_authoritative_receipt", return_value=False):
            r = auth._evaluate_at(*args[:3], host_key=KEY, lease_transport=lambda *x: (404, {}), expected_claimant="Z-Example", expected_claim_id="claim-001", expected_claim_started_at="2026-09-13T15:34:35Z", expected_anchor_sha="a"*40, now=NOW)
        self.assertIn("LIVE_LEASE_AUTHORITY_FAILED", r["payload"]["reasons"])

    def test_copied_winner_under_other_current_claimant_holds(self):
        r = self.pre(*bundle(), expected_claimant="Z-Loser")
        self.assertIn("CALLER_CLAIMANT_MISMATCH", r["payload"]["reasons"])

    def test_host_mac_tamper_rejected(self):
        ab, gb, lb, msg = bundle()
        obj = json.loads(ab); obj["payload"]["commercial_scope"] = "other-opportunity"
        with self.assertRaises(auth.AuthorityError):
            self.pre(json.dumps(obj).encode(), gb, lb, msg)

    def test_stale_cannot_be_revived_by_public_clock(self):
        args = bundle(issued=NOW-timedelta(minutes=10))
        r = self.pre(*args, now=NOW)
        self.assertIn("APPROVAL_EXPIRED", r["payload"]["reasons"])
        self.assertFalse(r["payload"]["external_send_authorized"])

    def test_guard_non_allow_holds(self):
        r = self.pre(*bundle(decision="REPLY_ONLY"))
        self.assertIn("GUARD_NOT_ALLOW_NEW", r["payload"]["reasons"])

    def test_exact_message_mismatch_never_consumes(self):
        ab, gb, lb, msg = bundle()
        consume = ConsumeTransport(); sender = Sender()
        r = self.consume((ab, gb, lb, b"wrong"), consume, sender)
        self.assertIn("MESSAGE_EXACT_BYTES_MISMATCH", r["reasons"])
        self.assertEqual([], sender.calls)
        self.assertFalse(any(m == "POST" and p.endswith("/git/refs") for m,p,b in consume.calls))

    def test_clean_consumes_once_and_sends_once(self):
        args = bundle(); consume = ConsumeTransport(); sender = Sender()
        first = self.consume(args, consume, sender)
        second = self.consume(args, consume, sender)
        self.assertEqual(first["decision"], "SENT_CONFIRMED")
        self.assertEqual(second["decision"], "HOLD_RECONCILE_ONLY")
        self.assertEqual(len(sender.calls), 1)
        self.assertEqual(second["consumption_state"], "ALREADY_CONSUMED")

    def test_two_prices_same_commercial_scope_collide(self):
        consume = ConsumeTransport(); sender = Sender()
        first = bundle(offer="pilot-5000", commercial="lacsd-04254")
        second = bundle(offer="pilot-7500", commercial="lacsd-04254")
        r1 = self.consume(first, consume, sender)
        r2 = self.consume(second, consume, sender)
        self.assertEqual(r1["decision"], "SENT_CONFIRMED")
        self.assertEqual(r2["consumption_state"], "ALREADY_CONSUMED")
        self.assertEqual(len(sender.calls), 1)

    def test_timeout_after_ref_write_recovers_and_still_sends_once(self):
        args = bundle(); consume = ConsumeTransport(ref_mode="timeout-after-write"); sender = Sender()
        r = self.consume(args, consume, sender)
        self.assertEqual(r["consumption_state"], "ACQUIRED_READBACK")
        self.assertEqual(len(sender.calls), 1)

    def test_ambiguous_provider_send_is_never_retried(self):
        args = bundle(); consume = ConsumeTransport(); sender = Sender(status=503, body={})
        first = self.consume(args, consume, sender)
        second = self.consume(args, consume, sender)
        self.assertEqual(first["decision"], "PROVIDER_OUTCOME_UNKNOWN_RECONCILE_ONLY")
        self.assertEqual(second["decision"], "HOLD_RECONCILE_ONLY")
        self.assertEqual(len(sender.calls), 1)

    def test_provider_rejection_is_not_retried(self):
        args = bundle(); consume = ConsumeTransport(); sender = Sender(status=400, body={})
        first = self.consume(args, consume, sender)
        second = self.consume(args, consume, sender)
        self.assertEqual(first["decision"], "PROVIDER_REJECTED_RECONCILE_ONLY")
        self.assertEqual(second["consumption_state"], "ALREADY_CONSUMED")
        self.assertEqual(len(sender.calls), 1)

    def test_success_without_provider_message_id_is_ambiguous(self):
        args = bundle(); consume = ConsumeTransport(); sender = Sender(status=200, body={})
        r = self.consume(args, consume, sender)
        self.assertEqual(r["decision"], "PROVIDER_OUTCOME_UNKNOWN_RECONCILE_ONLY")
        self.assertIsNone(r["provider_message_id_sha256"])

    def test_host_key_too_short_rejected(self):
        payload = json.loads(bundle()[0])["payload"]
        with self.assertRaises(auth.AuthorityError):
            auth.sign_host_approval(payload, host_key=b"short")


if __name__ == "__main__":
    unittest.main()
