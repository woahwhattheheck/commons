from __future__ import annotations

import unittest
from datetime import datetime, timezone

from tools.outbound_send_guard import muse_election_v2 as gate

MUSE = gate.MUSE_USER_ID
DM = gate.MUSE_DM_CONVERSATION_ID
SENDER = "U0BSAL3CZ4Y"
OTHER = "U0OTHER12345"
BASE = datetime(2026, 9, 15, 0, 30, 0, tzinfo=timezone.utc)
OBSERVED = "2026-09-15T00:31:10Z"
H = "a" * 64
J = "b" * 64
K = "c" * 64
L = "d" * 64
M = "e" * 64
N = "f" * 64


def z(seconds: int) -> str:
    return datetime.fromtimestamp(BASE.timestamp() + seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sts(seconds: int, frac: int = 1) -> str:
    return f"{int(BASE.timestamp()) + seconds}.{frac:06d}"


def candidate():
    return {
        "buyer_scope_sha256": H,
        "recipient_fingerprint": K,
        "offer_scope_sha256": L,
        "route_kind": "EMAIL",
        "intent_sha256": M,
        "body_sha256": J,
        "claimant": "ZIQ-K4R9",
        "operation_id": "OP-A",
        "lease_binding": {
            "schema_version": gate.LEASE_BINDING_SCHEMA,
            "receipt_schema": gate.LEASE_RECEIPT_SCHEMA,
            "claimant": "ZIQ-K4R9",
            "claim_id": "claim-a",
            "seam_sha256": "1" * 64,
            "lease_ref": "refs/heads/outbound-lease-v3/" + "1" * 64,
            "lease_commit_sha": "5" * 40,
            "claim_capability_sha256": N,
            "receipt_sha256": "3" * 64,
        },
    }


def request(rid="req-00000001", requested_at=None):
    return gate.prepare_request(candidate(), request_id=rid, requested_at=requested_at or z(0))


def msg(ts, author, text):
    return {"message_ts": ts, "author_user_id": author, "text": text}


def selected(req):
    p = req["payload"]
    return gate._decision_message("SELECTED", p["request_id"], p["publication_key"], p["candidate_sha256"])


def control(req, action="WITHDRAW", *, rid=None, pub=None, cand=None):
    p = req["payload"]
    return gate.requester_control_message(
        action,
        rid or p["request_id"],
        pub or p["publication_key"],
        cand or p["candidate_sha256"],
    )


def snap(messages, captured_at=None):
    return {
        "schema_version": gate.SNAPSHOT_SCHEMA,
        "complete": True,
        "channel_id": DM,
        "coverage_started_at": z(-600),
        "captured_at": captured_at or z(60),
        "messages": messages,
    }


def compile(req, messages, *, observed=OBSERVED, captured_at=None):
    return gate.compile_receipt(
        req,
        snap(messages, captured_at=captured_at),
        observed_at=observed,
        prior_receipts=(),
        ledger_complete=True,
    )


class MuseRequesterControlV2Tests(unittest.TestCase):
    def assert_controlled(self, receipt, action):
        self.assertEqual(receipt["payload"]["decision"], "HOLD")
        self.assertTrue(any(r.startswith(f"REQUESTER_CONTROL_ACTIVE:{action}:") for r in receipt["payload"]["reasons"]))
        self.assertIsNone(receipt["payload"]["selection_message_ts"])
        self.assertIsNone(receipt["payload"]["winner_request_id"])
        self.assertFalse(receipt["payload"]["external_send_authorized"])
        self.assertFalse(receipt["payload"]["side_effects_authorized"])
        self.assertTrue(gate.verify_receipt(receipt))

    def test_every_structured_control_before_selection_forces_hold(self):
        for action in sorted(gate.REQUESTER_CONTROL_ACTIONS):
            with self.subTest(action=action):
                req = request()
                receipt = compile(req, [
                    msg(sts(5, 1), SENDER, req["message"]),
                    msg(sts(10, 2), SENDER, control(req, action)),
                    msg(sts(15, 3), MUSE, selected(req)),
                ])
                self.assert_controlled(receipt, action)

    def test_control_after_selection_still_dominates(self):
        req = request()
        receipt = compile(req, [
            msg(sts(5), SENDER, req["message"]),
            msg(sts(15), MUSE, selected(req)),
            msg(sts(20), SENDER, control(req, "DO_NOT_SEND")),
        ])
        self.assert_controlled(receipt, "DO_NOT_SEND")

    def test_quoted_and_free_form_control_words_do_not_trigger(self):
        req = request()
        exact = control(req, "WITHDRAW")
        receipt = compile(req, [
            msg(sts(5), SENDER, req["message"]),
            msg(sts(8), SENDER, f'quoted example: "{exact}"'),
            msg(sts(9), SENDER, "DO NOT SEND"),
            msg(sts(15), MUSE, selected(req)),
        ])
        self.assertEqual(receipt["payload"]["decision"], "SELECTED")
        self.assertTrue(gate.verify_receipt(receipt))

    def test_wrong_binding_or_wrong_author_does_not_trigger(self):
        req = request()
        variants = [
            (OTHER, control(req, "HOLD")),
            (SENDER, control(req, "HOLD", rid="req-99999999")),
            (SENDER, control(req, "HOLD", pub="9" * 64)),
            (SENDER, control(req, "HOLD", cand="8" * 64)),
        ]
        for index, (author, wire) in enumerate(variants):
            with self.subTest(index=index):
                receipt = compile(req, [
                    msg(sts(5, 1), SENDER, req["message"]),
                    msg(sts(10, index + 2), author, wire),
                    msg(sts(15, 9), MUSE, selected(req)),
                ])
                self.assertEqual(receipt["payload"]["decision"], "SELECTED")
                self.assertTrue(gate.verify_receipt(receipt))

    def test_pre_request_control_does_not_trigger(self):
        req = request()
        receipt = compile(req, [
            msg(sts(4), SENDER, control(req, "CANCEL")),
            msg(sts(5), SENDER, req["message"]),
            msg(sts(15), MUSE, selected(req)),
        ])
        self.assertEqual(receipt["payload"]["decision"], "SELECTED")

    def test_controlled_request_cannot_be_reopened_by_later_selection(self):
        req = request()
        receipt = compile(req, [
            msg(sts(5), SENDER, req["message"]),
            msg(sts(10), SENDER, control(req, "WITHDRAW")),
            msg(sts(40), MUSE, selected(req)),
        ])
        self.assert_controlled(receipt, "WITHDRAW")

    def test_fresh_request_id_is_explicit_reopen(self):
        old = request("req-00000001", z(0))
        fresh = request("req-00000002", z(20))
        messages = [
            msg(sts(5), SENDER, old["message"]),
            msg(sts(10), SENDER, control(old, "WITHDRAW")),
            msg(sts(25), SENDER, fresh["message"]),
            msg(sts(35), MUSE, selected(fresh)),
        ]
        old_receipt = compile(old, messages)
        self.assertEqual(old_receipt["payload"]["decision"], "HOLD")
        fresh_receipt = compile(fresh, messages)
        self.assertEqual(fresh_receipt["payload"]["decision"], "SELECTED")
        self.assertTrue(gate.verify_receipt(fresh_receipt))
        self.assertEqual(gate.REQUESTER_CONTROL_REOPEN_POLICY, "FRESH_REQUEST_ID_REQUIRED")

    def test_unknown_control_action_is_rejected_by_wire_builder(self):
        req = request()
        p = req["payload"]
        with self.assertRaises(gate.MuseElectionV2Error):
            gate.requester_control_message("REOPEN", p["request_id"], p["publication_key"], p["candidate_sha256"])


if __name__ == "__main__":
    unittest.main()
