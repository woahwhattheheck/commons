from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from revenue.outbound_send_authority.authority import AuthorityError, evaluate_bytes, main, verify_receipt_bytes

NOW = datetime(2026, 9, 13, 14, 42, 0, tzinfo=timezone.utc)


def canon(obj, newline=False, ascii_only=False):
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=ascii_only).encode("ascii" if ascii_only else "utf-8")
    return raw + (b"\n" if newline else b"")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def guard_receipt(decision="ALLOW_NEW", recipient="buyer@example.com", offer="pilot", generated_at="2026-09-13T14:41:30Z"):
    payload = {
        "schema_version": "outbound-send-guard-receipt/v1",
        "intent": {"intent_id": "intent-001", "recipient": recipient, "offer_id": offer, "requested_at": "2026-09-13T14:41:20Z", "route_kind": "email"},
        "evidence": {"generated_at": generated_at, "mailbox_complete": True, "mailbox_query_id": "mail-q", "slack_complete": True, "slack_query_id": "slack-q", "intent_sha256": "1" * 64, "evidence_sha256": "2" * 64, "matched_refs": []},
        "policy": {"cross_offer_cooldown_days": 30, "max_evidence_age_seconds": 900, "max_future_skew_seconds": 300},
        "decision": decision, "authority": "complete", "reasons": ["clean"],
        "latest_outbound_at": None, "latest_inbound_at": None, "reply_message_id": None,
        "side_effects_authorized": False,
    }
    return {"payload": payload, "receipt_sha256": sha(canon(payload, newline=True))}


def lease_receipt(guard_payload_digest, buyer="example.com", offer="pilot", claimant="Z-Example-123", claim_id="claim-001", decision="LEASE_HELD", held=True):
    seam = {"schema": "outbound-send-lease/v1", "buyer_scope": buyer, "offer_scope": offer}
    seam_sha = sha(canon(seam, ascii_only=True))
    obj = {
        "schema": "outbound-send-lease-receipt/v1", "seam_sha256": seam_sha,
        "lease_ref": f"refs/tags/outbound-lease-v1/{seam_sha}", "claim_id": claim_id,
        "claimant": claimant, "claim_started_at": "2026-09-13T14:41:35Z",
        "preflight_sha256": guard_payload_digest, "tag_object_sha": "a" * 40,
        "observed_ref_sha": "a" * 40 if held else "b" * 40,
        "lease_held_by_claimant": held, "decision": decision,
        "reason": "ACQUIRED_CREATE_201" if held else "HELD_BY_OTHER",
        "external_send_authorized": False,
    }
    obj["receipt_sha256"] = sha(canon(obj, ascii_only=True))
    return obj


def bundle(**changes):
    g = guard_receipt(changes.get("guard_decision", "ALLOW_NEW"), changes.get("recipient", "buyer@example.com"), changes.get("offer", "pilot"), changes.get("generated_at", "2026-09-13T14:41:30Z"))
    l = lease_receipt(g["receipt_sha256"], buyer=changes.get("buyer", "example.com"), offer=changes.get("lease_offer", changes.get("offer", "pilot")), claimant=changes.get("lease_claimant", "Z-Example-123"), claim_id=changes.get("lease_claim_id", "claim-001"), decision=changes.get("lease_decision", "LEASE_HELD"), held=changes.get("held", True))
    gb = json.dumps(g, sort_keys=True).encode(); lb = json.dumps(l, sort_keys=True).encode()
    intent = {
        "schema_version": "outbound-send-authority-intent/v1", "buyer_scope": changes.get("buyer", "example.com"),
        "offer_scope": changes.get("intent_offer", changes.get("offer", "pilot")),
        "recipient_sha256": changes.get("recipient_sha", sha(changes.get("recipient", "buyer@example.com").casefold().encode())),
        "claimant": changes.get("intent_claimant", "Z-Example-123"), "claim_id": changes.get("intent_claim_id", "claim-001"),
        "requested_at": changes.get("requested_at", "2026-09-13T14:41:20Z"), "route_kind": "email",
        "guard_receipt_sha256": sha(gb), "lease_receipt_sha256": sha(lb),
    }
    return json.dumps(intent, sort_keys=True).encode(), gb, lb


class AuthorityTests(unittest.TestCase):
    def eval(self, **changes):
        return evaluate_bytes(*bundle(**changes), as_of=NOW)

    def test_clean_is_send_ready(self):
        r = self.eval(); self.assertEqual(r["payload"]["decision"], "SEND_READY"); self.assertIs(r["payload"]["external_send_authorized"], True)

    def test_guard_non_allow_states_hold(self):
        for state in ("HOLD", "REPLY_ONLY", "DO_NOT_RESEND"):
            with self.subTest(state=state): self.assertEqual(self.eval(guard_decision=state)["payload"]["decision"], "HOLD")

    def test_lease_not_held(self):
        self.assertIn("LEASE_NOT_HELD", self.eval(lease_decision="HOLD", held=False)["payload"]["reasons"])

    def test_claimant_and_claim_id_mismatch(self):
        self.assertIn("LEASE_CLAIMANT_MISMATCH", self.eval(intent_claimant="Z-Other-456")["payload"]["reasons"])
        self.assertIn("LEASE_CLAIM_ID_MISMATCH", self.eval(intent_claim_id="claim-999")["payload"]["reasons"])

    def test_seam_mismatch(self):
        r = self.eval(intent_offer="different"); self.assertIn("GUARD_OFFER_MISMATCH", r["payload"]["reasons"]); self.assertIn("LEASE_SEAM_MISMATCH", r["payload"]["reasons"])

    def test_recipient_hash_mismatch(self):
        self.assertIn("GUARD_RECIPIENT_MISMATCH", self.eval(recipient_sha="f" * 64)["payload"]["reasons"])

    def test_preflight_mismatch(self):
        ib, gb, lb = bundle(); lease = json.loads(lb); lease["preflight_sha256"] = "3" * 64
        material = dict(lease); material.pop("receipt_sha256"); lease["receipt_sha256"] = sha(canon(material, ascii_only=True))
        lb2 = json.dumps(lease, sort_keys=True).encode(); intent = json.loads(ib); intent["lease_receipt_sha256"] = sha(lb2)
        r = evaluate_bytes(json.dumps(intent, sort_keys=True).encode(), gb, lb2, as_of=NOW); self.assertIn("PREFLIGHT_RECEIPT_MISMATCH", r["payload"]["reasons"])

    def test_tampered_guard_digest_rejected(self):
        ib, gb, lb = bundle(); g = json.loads(gb); g["payload"]["reasons"] = ["tamper"]
        with self.assertRaises(AuthorityError): evaluate_bytes(ib, json.dumps(g).encode(), lb, as_of=NOW)

    def test_tampered_lease_digest_rejected(self):
        ib, gb, lb = bundle(); l = json.loads(lb); l["reason"] = "tamper"
        with self.assertRaises(AuthorityError): evaluate_bytes(ib, gb, json.dumps(l).encode(), as_of=NOW)

    def test_stale_and_future(self):
        self.assertIn("GUARD_STALE", self.eval(generated_at="2026-09-13T14:30:00Z")["payload"]["reasons"])
        r = evaluate_bytes(*bundle(), as_of=datetime(2026, 9, 13, 14, 40, 0, tzinfo=timezone.utc)); self.assertTrue(any(x.endswith("_FUTURE") for x in r["payload"]["reasons"]))

    def test_exact_receipt_bytes_are_bound(self):
        ib, gb, lb = bundle(); gb2 = json.dumps(json.loads(gb), separators=(",", ":")).encode(); r = evaluate_bytes(ib, gb2, lb, as_of=NOW)
        self.assertIn("GUARD_RECEIPT_BYTES_MISMATCH", r["payload"]["reasons"])

    def test_duplicate_key_rejected(self):
        ib, gb, lb = bundle(); bad = ib[:-1] + b',"route_kind":"email"}'
        with self.assertRaises(AuthorityError): evaluate_bytes(bad, gb, lb, as_of=NOW)

    def test_nonfinite_rejected(self):
        ib, gb, lb = bundle(); bad = ib[:-1] + b',"x":NaN}'
        with self.assertRaises(AuthorityError): evaluate_bytes(bad, gb, lb, as_of=NOW)

    def test_bool_int_policy_alias_rejected(self):
        with self.assertRaises(AuthorityError): evaluate_bytes(*bundle(), as_of=NOW, max_age_seconds=True)

    def test_unknown_intent_field_rejected(self):
        ib, gb, lb = bundle(); obj = json.loads(ib); obj["extra"] = 1
        with self.assertRaises(AuthorityError): evaluate_bytes(json.dumps(obj).encode(), gb, lb, as_of=NOW)

    def test_unsupported_schema_rejected(self):
        ib, gb, lb = bundle(); obj = json.loads(ib); obj["schema_version"] = "v999"
        with self.assertRaises(AuthorityError): evaluate_bytes(json.dumps(obj).encode(), gb, lb, as_of=NOW)

    def test_deterministic(self):
        args = bundle(); self.assertEqual(evaluate_bytes(*args, as_of=NOW), evaluate_bytes(*args, as_of=NOW))

    def test_verify_recompiles(self):
        args = bundle(); r = evaluate_bytes(*args, as_of=NOW); rb = json.dumps(r, sort_keys=True).encode(); self.assertTrue(verify_receipt_bytes(rb, *args, as_of=NOW))
        tampered = json.loads(rb); tampered["payload"]["decision"] = "HOLD"
        with self.assertRaises(AuthorityError): verify_receipt_bytes(json.dumps(tampered).encode(), *args, as_of=NOW)

    def test_cli_create_exclusive_and_refuses_symlink(self):
        ib, gb, lb = bundle()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, raw in (("i.json", ib), ("g.json", gb), ("l.json", lb)): (root / name).write_bytes(raw)
            argv = ["--intent", str(root/"i.json"), "--guard-receipt", str(root/"g.json"), "--lease-receipt", str(root/"l.json"), "--as-of", "2026-09-13T14:42:00Z"]
            out = root / "out.json"; self.assertEqual(main(argv + ["--out", str(out)]), 0); self.assertTrue(out.exists()); self.assertEqual(main(argv + ["--out", str(out)]), 2)
            link = root / "link.json"; link.symlink_to(root / "fresh-target.json"); self.assertEqual(main(argv + ["--out", str(link)]), 2)


if __name__ == "__main__":
    unittest.main()
