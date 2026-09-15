from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from tools.outbound_send_guard import muse_selection_gate as gate

NOW = datetime(2026, 9, 15, 0, 35, 0, tzinfo=timezone.utc)
MUSE = "U0C0TKRTQHZ"
DM = "D0C1U7TUZEC"
SENDER = "U0BRETUB5TK"
H = "a" * 64
J = "b" * 64
K = "c" * 64
L = "d" * 64


def candidate(worker="ZIQ-K4R9", candidate_id="cand-a", message_sha=J):
    return {
        "schema_version": gate.CANDIDATE_SCHEMA,
        "candidate_id": candidate_id,
        "worker_id": worker,
        "buyer_scope_sha256": H,
        "recipient_fingerprint": K,
        "offer_scope": "inventory-variance-desk-v1",
        "route_kind": "EMAIL",
        "message_sha256": message_sha,
        "requested_at": "2026-09-15T00:30:00Z",
        "lease": {
            "schema": gate.LEASE_RECEIPT_SCHEMA,
            "claimant": worker,
            "claim_id": "claim-001" if worker == "ZIQ-K4R9" else "claim-002",
            "lease_ref": "refs/heads/outbound-lease-v3/" + ("1" if worker == "ZIQ-K4R9" else "2") * 64,
            "claim_capability_sha256": L if worker == "ZIQ-K4R9" else "e" * 64,
            "receipt_sha256": "f" * 64 if worker == "ZIQ-K4R9" else "0" * 64,
        },
    }


def event(c, kind, message_id, observed_at, sender=None):
    n = gate.normalize_candidate(c)
    return {
        "message_id": message_id,
        "sender_user_id": sender or (MUSE if kind != "CANDIDATE" else SENDER),
        "observed_at": observed_at,
        "event_type": kind,
        "publication_key": gate.publication_key(n),
        "candidate_digest": gate.candidate_digest(n),
        "candidate_id": n["candidate_id"],
        "worker_id": n["worker_id"],
    }


def snapshot(events, **updates):
    value = {
        "schema_version": gate.SNAPSHOT_SCHEMA,
        "complete": True,
        "conversation_id": DM,
        "arbiter_user_id": MUSE,
        "coverage_started_at": "2026-09-15T00:29:00Z",
        "captured_at": "2026-09-15T00:34:30Z",
        "events": events,
    }
    value.update(updates)
    return value


def happy(c=None):
    c = c or candidate()
    return snapshot(
        [
            event(c, "CANDIDATE", "1789432205.000001", "2026-09-15T00:30:05Z"),
            event(c, "SELECTED", "1789432215.000002", "2026-09-15T00:30:15Z"),
        ]
    )


class MuseSelectionTests(unittest.TestCase):
    def compile(self, c=None, s=None, **kwargs):
        c = c or candidate()
        s = s or happy(c)
        return gate.compile_selection(
            c,
            s,
            expected_conversation_id=DM,
            expected_arbiter_user_id=MUSE,
            now=NOW,
            **kwargs,
        )

    def test_happy_selected_and_verifiable(self):
        c = candidate()
        receipt = self.compile(c)
        self.assertEqual(receipt["decision"], gate.SELECTED)
        self.assertTrue(gate.verify_receipt(receipt))
        self.assertTrue(gate.verify_selected_binding(c, receipt))
        self.assertFalse(receipt["side_effects_authorized"])
        self.assertTrue(receipt["requires_current_worker_lease_possession"])
        self.assertRegex(receipt["selection_binding_sha256"], r"^[0-9a-f]{64}$")

    def test_publication_key_collides_across_worker_and_copy(self):
        a = gate.normalize_candidate(candidate())
        b = gate.normalize_candidate(candidate("Z-OTHER", "cand-b", "9" * 64))
        self.assertEqual(gate.publication_key(a), gate.publication_key(b))
        self.assertNotEqual(gate.candidate_digest(a), gate.candidate_digest(b))

    def test_other_workers_selection_does_not_select_caller(self):
        a = candidate()
        b = candidate("Z-OTHER", "cand-b", "9" * 64)
        s = snapshot(
            [
                event(b, "CANDIDATE", "1789432206.000001", "2026-09-15T00:30:06Z"),
                event(a, "SELECTED", "1789432215.000003", "2026-09-15T00:30:15Z"),
            ]
        )
        receipt = self.compile(b, s)
        self.assertEqual(receipt["decision"], gate.NOT_SELECTED)
        self.assertFalse(gate.verify_selected_binding(b, receipt))

    def test_multiple_distinct_winners_hold(self):
        a = candidate()
        b = candidate("Z-OTHER", "cand-b", "9" * 64)
        s = snapshot(
            [
                event(a, "CANDIDATE", "1789432205.000021", "2026-09-15T00:30:05Z"),
                event(a, "SELECTED", "1789432215.000022", "2026-09-15T00:30:15Z"),
                event(b, "SELECTED", "1789432216.000023", "2026-09-15T00:30:16Z"),
            ]
        )
        receipt = self.compile(a, s)
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("MULTIPLE_DISTINCT_WINNERS", receipt["reasons"])

    def test_decision_from_non_arbiter_holds(self):
        c = candidate()
        s = happy(c)
        s["events"][1]["sender_user_id"] = "U0OTHER12345"
        receipt = self.compile(c, s)
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertTrue(any(x.startswith("DECISION_NOT_FROM_ARBITER") for x in receipt["reasons"]))

    def test_wrong_conversation_holds(self):
        s = happy()
        s["conversation_id"] = "D0OTHER12345"
        receipt = self.compile(s=s)
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("WRONG_CONVERSATION", receipt["reasons"])

    def test_incomplete_snapshot_holds(self):
        s = happy()
        s["complete"] = False
        receipt = self.compile(s=s)
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("SNAPSHOT_INCOMPLETE", receipt["reasons"])

    def test_stale_snapshot_holds(self):
        s = happy()
        s["captured_at"] = "2026-09-15T00:31:00Z"
        receipt = self.compile(s=s)
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("SNAPSHOT_STALE", receipt["reasons"])

    def test_future_snapshot_holds(self):
        s = happy()
        s["captured_at"] = "2026-09-15T00:36:00Z"
        receipt = self.compile(s=s)
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("SNAPSHOT_IN_FUTURE", receipt["reasons"])

    def test_selection_expiry_holds(self):
        receipt = gate.compile_selection(
            candidate(),
            happy(),
            expected_conversation_id=DM,
            expected_arbiter_user_id=MUSE,
            now=datetime(2026, 9, 15, 0, 45, 0, tzinfo=timezone.utc),
            max_snapshot_age_seconds=1000,
            selection_ttl_seconds=300,
        )
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("SELECTION_EXPIRED", receipt["reasons"])

    def test_selection_after_ten_minute_latency_holds(self):
        c = candidate()
        s = snapshot(
            [
                event(c, "CANDIDATE", "1789432205.000031", "2026-09-15T00:30:05Z"),
                event(c, "SELECTED", "1789432806.000032", "2026-09-15T00:40:06Z"),
            ],
            captured_at="2026-09-15T00:40:10Z",
        )
        receipt = gate.compile_selection(
            c,
            s,
            expected_conversation_id=DM,
            expected_arbiter_user_id=MUSE,
            now=datetime(2026, 9, 15, 0, 40, 20, tzinfo=timezone.utc),
        )
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertTrue(any(x.startswith("DECISION_AFTER_LATENCY_LIMIT") for x in receipt["reasons"]))

    def test_selected_then_cancelled_is_not_selected(self):
        c = candidate()
        s = snapshot(
            [
                event(c, "CANDIDATE", "1789432205.000041", "2026-09-15T00:30:05Z"),
                event(c, "SELECTED", "1789432215.000042", "2026-09-15T00:30:15Z"),
                event(c, "CANCELLED", "1789432216.000043", "2026-09-15T00:30:16Z"),
            ]
        )
        receipt = self.compile(c, s)
        self.assertEqual(receipt["decision"], gate.NOT_SELECTED)
        self.assertIsNone(receipt["selection_binding_sha256"])

    def test_no_decision_holds(self):
        c = candidate()
        s = snapshot([event(c, "CANDIDATE", "1789432205.000051", "2026-09-15T00:30:05Z")])
        receipt = self.compile(c, s)
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("NO_ARBITER_DECISION", receipt["reasons"])

    def test_conflicting_duplicate_message_id_holds(self):
        c = candidate()
        request = event(c, "CANDIDATE", "1789432205.000061", "2026-09-15T00:30:05Z")
        selected = event(c, "SELECTED", "1789432215.000062", "2026-09-15T00:30:15Z")
        conflict = copy.deepcopy(selected)
        conflict["event_type"] = "NOT_SELECTED"
        s = snapshot([request, selected, conflict])
        receipt = self.compile(c, s)
        self.assertEqual(receipt["decision"], gate.HOLD)
        self.assertIn("CONFLICTING_MESSAGE_ID:1789432215.000062", receipt["reasons"])

    def test_exact_duplicate_message_is_idempotent(self):
        c = candidate()
        s = happy(c)
        s["events"].append(copy.deepcopy(s["events"][1]))
        receipt = self.compile(c, s)
        self.assertEqual(receipt["decision"], gate.SELECTED)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(gate.DuplicateKeyError):
            gate.parse_json_bytes(b'{"a":1,"a":2}', "x")

    def test_unknown_candidate_field_rejected(self):
        c = candidate()
        c["mystery"] = True
        with self.assertRaises(gate.MuseSelectionError):
            gate.normalize_candidate(c)

    def test_lease_claimant_must_equal_worker(self):
        c = candidate()
        c["lease"]["claimant"] = "Z-OTHER"
        with self.assertRaises(gate.MuseSelectionError):
            gate.normalize_candidate(c)

    def test_tampered_receipt_fails_verification(self):
        receipt = self.compile()
        receipt["worker_id"] = "Z-TAMPER"
        self.assertFalse(gate.verify_receipt(receipt))

    def test_selected_receipt_cannot_be_rebound_to_other_candidate(self):
        receipt = self.compile()
        b = candidate("Z-OTHER", "cand-b", "9" * 64)
        self.assertFalse(gate.verify_selected_binding(b, receipt))

    def test_recomputed_outer_digest_cannot_forge_selection_binding(self):
        receipt = self.compile()
        receipt["selection_binding_sha256"] = "1" * 64
        material = dict(receipt)
        material.pop("receipt_digest")
        receipt["receipt_digest"] = gate.digest_object(material)
        self.assertFalse(gate.verify_receipt(receipt))

    def test_noncanonical_slack_message_id_rejected(self):
        c = candidate()
        s = happy(c)
        s["events"][1]["message_id"] = "short.1"
        with self.assertRaises(gate.MuseSelectionError):
            gate.normalize_snapshot(s)

    def test_cli_semantic_exit_codes(self):
        now = datetime.now(timezone.utc)
        def z(dt):
            return dt.isoformat(timespec="seconds").replace("+00:00", "Z")
        c = candidate()
        c["requested_at"] = z(now - timedelta(seconds=30))
        s = snapshot(
            [
                event(c, "CANDIDATE", "1789432205.000071", z(now - timedelta(seconds=25))),
                event(c, "SELECTED", "1789432215.000072", z(now - timedelta(seconds=15))),
            ],
            coverage_started_at=z(now - timedelta(seconds=60)),
            captured_at=z(now - timedelta(seconds=5)),
        )
        with tempfile.TemporaryDirectory() as td:
            cp = os.path.join(td, "candidate.json")
            sp = os.path.join(td, "snapshot.json")
            with open(cp, "w", encoding="utf-8") as f:
                json.dump(c, f)
            with open(sp, "w", encoding="utf-8") as f:
                json.dump(s, f)
            proc = subprocess.run(
                [sys.executable, "-m", "tools.outbound_send_guard.muse_selection_gate", "--candidate", cp, "--snapshot", sp, "--conversation-id", DM, "--arbiter-user-id", MUSE],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())
            parsed = json.loads(proc.stdout)
            self.assertEqual(parsed["decision"], gate.SELECTED)


if __name__ == "__main__":
    unittest.main()
