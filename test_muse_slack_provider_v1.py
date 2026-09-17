from __future__ import annotations

import copy
import json
import os
import unittest
from datetime import datetime, timezone
from unittest import mock

from tools.outbound_send_guard import muse_election_v2 as gate
from tools.outbound_send_guard import muse_slack_provider_v1 as provider

BASE = datetime(2026, 9, 17, 7, 20, 0, tzinfo=timezone.utc)
CAPTURE = datetime(2026, 9, 17, 7, 21, 10, tzinfo=timezone.utc)
SENDER = "U0BSAL3CZ4Y"
H = "a" * 64
J = "b" * 64
K = "c" * 64
L = "d" * 64
M = "e" * 64
N = "f" * 64


def z(seconds: int) -> str:
    return datetime.fromtimestamp(BASE.timestamp() + seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sts(seconds: int, frac: int = 1) -> str:
    whole = int(BASE.timestamp()) + seconds
    return f"{whole}.{frac:06d}"


def candidate():
    seam = "1" * 64
    return {
        "buyer_scope_sha256": H,
        "recipient_fingerprint": K,
        "offer_scope_sha256": L,
        "route_kind": "EMAIL",
        "intent_sha256": M,
        "body_sha256": J,
        "claimant": "Z-TEST",
        "operation_id": "OP-MUSE-PROVIDER-TEST",
        "lease_binding": {
            "schema_version": gate.LEASE_BINDING_SCHEMA,
            "receipt_schema": gate.LEASE_RECEIPT_SCHEMA,
            "claimant": "Z-TEST",
            "claim_id": "claim-provider-test",
            "seam_sha256": seam,
            "lease_ref": "refs/heads/outbound-lease-v3/" + seam,
            "lease_commit_sha": "5" * 40,
            "claim_capability_sha256": N,
            "receipt_sha256": "3" * 64,
        },
    }


def request():
    return gate.prepare_request(candidate(), request_id="req-provider-0001", requested_at=z(0))


def selected_text(req, kind="SELECTED"):
    p = req["payload"]
    return gate._decision_message(kind, p["request_id"], p["publication_key"], p["candidate_sha256"])


class FakeSlack:
    def __init__(
        self,
        req,
        *,
        selected=True,
        control=None,
        ambiguous=False,
        paginated=False,
        malformed=False,
        web_edited=False,
    ):
        self.req = req
        self.selected = selected
        self.control = control
        self.ambiguous = ambiguous
        self.paginated = paginated
        self.malformed = malformed
        self.web_edited = web_edited
        self.calls = []

    def __call__(self, method, params, token):
        self.calls.append((method, dict(params), token))
        if token != "x-test-token":
            raise AssertionError("unexpected token")
        if method == "auth.test":
            return {"ok": True, "team_id": provider.TEAM_ID}
        if method == "conversations.info":
            return {
                "ok": True,
                "channel": {
                    "id": provider.MUSE_DM_CONVERSATION_ID,
                    "is_im": True,
                    "user": provider.MUSE_USER_ID,
                },
            }
        if method == "conversations.history":
            if self.malformed:
                return {
                    "ok": True,
                    "messages": [{"ts": sts(5), "text": self.req["message"], "subtype": "message_changed"}],
                    "response_metadata": {"next_cursor": ""},
                }
            cursor = params.get("cursor", "")
            parent = {
                "ts": sts(5),
                "user": SENDER,
                "text": self.req["message"],
                "reply_count": 1 if self.selected else 0,
            }
            if self.web_edited:
                parent["edited"] = {"user": SENDER, "ts": sts(6)}
            extra = []
            if self.control:
                extra.append({
                    "ts": sts(20),
                    "user": SENDER,
                    "text": provider._control_text(self.control, self.req["payload"]),
                })
            if self.ambiguous:
                extra.append({
                    "ts": sts(21),
                    "user": SENDER,
                    "text": "UPDATE HOLD " + self.req["payload"]["request_id"],
                })
            if self.paginated and not cursor:
                return {
                    "ok": True,
                    "messages": [parent],
                    "has_more": True,
                    "response_metadata": {"next_cursor": "page-2"},
                }
            if self.paginated and cursor == "page-2":
                return {"ok": True, "messages": extra, "response_metadata": {"next_cursor": ""}}
            return {"ok": True, "messages": [parent] + extra, "response_metadata": {"next_cursor": ""}}
        if method == "conversations.replies":
            parent = {"ts": sts(5), "user": SENDER, "text": self.req["message"]}
            rows = [parent]
            if self.selected:
                rows.append({
                    "ts": sts(15, 2),
                    "user": provider.MUSE_USER_ID,
                    "text": selected_text(self.req),
                })
            return {"ok": True, "messages": rows, "response_metadata": {"next_cursor": ""}}
        raise AssertionError(method)


class MuseSlackProviderV1Tests(unittest.TestCase):
    def setUp(self):
        self.req = request()
        self.env = mock.patch.dict(os.environ, {provider.TOKEN_ENV: "x-test-token"}, clear=False)
        self.clock = mock.patch.object(provider, "_utc_now", return_value=CAPTURE)
        self.env.start()
        self.clock.start()

    def tearDown(self):
        self.clock.stop()
        self.env.stop()

    def compile(self, fake):
        with mock.patch.object(provider, "_slack_api", side_effect=fake):
            return provider.compile_provider_evidence(self.req)

    def verify(self, fake, receipt):
        with mock.patch.object(provider, "_slack_api", side_effect=fake):
            return provider.verify_provider_evidence(self.req, receipt)

    def test_selected_provider_observation_is_current_visible_but_never_terminal_authority(self):
        fake = FakeSlack(self.req, selected=True)
        receipt = self.compile(fake)
        p = receipt["payload"]
        self.assertEqual(p["muse_observed_decision"], "SELECTED")
        self.assertEqual(p["current_visible_effective_observation"], "SELECTED")
        self.assertEqual(p["visibility_model"], provider.VISIBILITY_MODEL)
        self.assertFalse(p["deleted_history_authenticated"])
        self.assertFalse(p["requester_control_history_authenticated"])
        self.assertFalse(p["prior_receipt_ledger_authenticated"])
        self.assertFalse(p["terminal_election_authorized"])
        self.assertFalse(p["external_send_authorized"])
        self.assertFalse(p["side_effects_authorized"])
        self.assertTrue(p["requires_current_worker_lease_possession"])
        self.assertTrue(p["requires_fresh_provider_preflight"])
        self.assertEqual(p["requester_user_id"], SENDER)
        self.assertIn("SLACK_WEB_API_HISTORY_CURRENT_VISIBLE_ONLY", p["provider_reasons"])
        self.assertNotIn("x-test-token", json.dumps(receipt, sort_keys=True))

    def test_verifier_rereads_provider_and_reproduces_exact_boundary(self):
        receipt = self.compile(FakeSlack(self.req, selected=True))
        fake = FakeSlack(self.req, selected=True)
        self.assertTrue(self.verify(fake, receipt))
        methods = [call[0] for call in fake.calls]
        self.assertIn("auth.test", methods)
        self.assertIn("conversations.info", methods)
        self.assertIn("conversations.history", methods)
        self.assertIn("conversations.replies", methods)

    def test_provider_change_breaks_verification(self):
        receipt = self.compile(FakeSlack(self.req, selected=True))
        changed = FakeSlack(self.req, selected=False)
        self.assertFalse(self.verify(changed, receipt))

    def test_requester_hold_dominates_later_visible_muse_selection(self):
        receipt = self.compile(FakeSlack(self.req, selected=True, control="HOLD"))
        p = receipt["payload"]
        self.assertEqual(p["muse_observed_decision"], "SELECTED")
        self.assertEqual(p["current_visible_effective_observation"], "HOLD")
        self.assertEqual(p["control_action"], "HOLD")
        self.assertIn("REQUESTER_CONTROL_HOLD", p["provider_reasons"])

    def test_requester_withdraw_and_cancel_dominate_while_visible(self):
        for action in ("WITHDRAW", "CANCEL"):
            with self.subTest(action=action):
                receipt = self.compile(FakeSlack(self.req, selected=True, control=action))
                self.assertEqual(receipt["payload"]["current_visible_effective_observation"], "HOLD")
                self.assertEqual(receipt["payload"]["control_action"], action)

    def test_ambiguous_requester_followup_mentioning_exact_request_fails_closed(self):
        receipt = self.compile(FakeSlack(self.req, selected=True, ambiguous=True))
        p = receipt["payload"]
        self.assertEqual(p["current_visible_effective_observation"], "HOLD")
        self.assertTrue(any(x.startswith("AMBIGUOUS_REQUESTER_FOLLOWUP:") for x in p["provider_reasons"]))

    def test_resume_requires_newer_visible_muse_decision(self):
        receipt = self.compile(FakeSlack(self.req, selected=True, control="RESUME"))
        p = receipt["payload"]
        self.assertEqual(p["current_visible_effective_observation"], "HOLD")
        self.assertIn("REQUESTER_RESUME_REQUIRES_LATER_MUSE_DECISION", p["provider_reasons"])

    def test_web_api_edited_metadata_fails_closed(self):
        with mock.patch.object(provider, "_slack_api", side_effect=FakeSlack(self.req, web_edited=True)):
            with self.assertRaisesRegex(provider.MuseSlackProviderError, "edited Slack message unsupported"):
                provider.compile_provider_evidence(self.req)

    def test_deleted_control_cannot_be_authenticated_by_history_transport(self):
        visible_hold = self.compile(FakeSlack(self.req, selected=True, control="HOLD"))["payload"]
        absent_control = self.compile(FakeSlack(self.req, selected=True))["payload"]
        self.assertEqual(visible_hold["current_visible_effective_observation"], "HOLD")
        self.assertEqual(absent_control["current_visible_effective_observation"], "SELECTED")
        for payload in (visible_hold, absent_control):
            self.assertFalse(payload["deleted_history_authenticated"])
            self.assertFalse(payload["requester_control_history_authenticated"])
            self.assertFalse(payload["terminal_election_authorized"])
            self.assertFalse(payload["external_send_authorized"])
            self.assertFalse(payload["side_effects_authorized"])

    def test_thread_reply_is_included_in_provider_snapshot(self):
        receipt = self.compile(FakeSlack(self.req, selected=True))
        self.assertEqual(receipt["payload"]["selection_message_ts"], sts(15, 2))

    def test_history_pagination_is_exhausted(self):
        fake = FakeSlack(self.req, selected=False, control="HOLD", paginated=True)
        receipt = self.compile(fake)
        self.assertEqual(receipt["payload"]["control_action"], "HOLD")
        history_calls = [c for c in fake.calls if c[0] == "conversations.history"]
        self.assertEqual(len(history_calls), 2)

    def test_workspace_mismatch_fails_closed(self):
        def wrong(method, params, token):
            if method == "auth.test":
                return {"ok": True, "team_id": "T-WRONG"}
            raise AssertionError("must stop before later reads")
        with mock.patch.object(provider, "_slack_api", side_effect=wrong):
            with self.assertRaises(provider.MuseSlackProviderError):
                provider.compile_provider_evidence(self.req)

    def test_dm_peer_mismatch_fails_closed(self):
        def wrong(method, params, token):
            if method == "auth.test":
                return {"ok": True, "team_id": provider.TEAM_ID}
            if method == "conversations.info":
                return {"ok": True, "channel": {"id": provider.MUSE_DM_CONVERSATION_ID, "is_im": True, "user": "U0OTHER12345"}}
            raise AssertionError("must stop before history")
        with mock.patch.object(provider, "_slack_api", side_effect=wrong):
            with self.assertRaises(provider.MuseSlackProviderError):
                provider.compile_provider_evidence(self.req)

    def test_events_api_changed_subtype_fails_closed(self):
        with mock.patch.object(provider, "_slack_api", side_effect=FakeSlack(self.req, malformed=True)):
            with self.assertRaises(provider.MuseSlackProviderError):
                provider.compile_provider_evidence(self.req)

    def test_forged_authority_bits_fail_even_with_rehashed_outer_receipt(self):
        receipt = self.compile(FakeSlack(self.req, selected=True))
        forged = copy.deepcopy(receipt)
        forged["payload"]["terminal_election_authorized"] = True
        forged["receipt_sha256"] = provider._digest(forged["payload"])
        self.assertFalse(self.verify(FakeSlack(self.req, selected=True), forged))

    def test_forged_deleted_history_authentication_fails_even_if_rehashed(self):
        receipt = self.compile(FakeSlack(self.req, selected=True))
        forged = copy.deepcopy(receipt)
        forged["payload"]["deleted_history_authenticated"] = True
        forged["receipt_sha256"] = provider._digest(forged["payload"])
        self.assertFalse(self.verify(FakeSlack(self.req, selected=True), forged))

    def test_stale_receipt_fails_without_provider_read(self):
        receipt = self.compile(FakeSlack(self.req, selected=True))
        later = CAPTURE.replace(minute=22)
        with mock.patch.object(provider, "_utc_now", return_value=later):
            with mock.patch.object(provider, "_slack_api") as api:
                self.assertFalse(provider.verify_provider_evidence(self.req, receipt))
                api.assert_not_called()


if __name__ == "__main__":
    unittest.main()
