from __future__ import annotations

import copy
import unittest

from tools.outbound_send_guard import buyer_scope


class BuyerScopeGuardTests(unittest.TestCase):
    def intent(self, *, recipient: str = "ceo@buyer.test", offer_id: str = "offer-a"):
        return {
            "schema_version": "outbound-send-intent/v1",
            "intent_id": "intent-1",
            "recipient": recipient,
            "offer_id": offer_id,
            "requested_at": "2026-09-13T10:10:00Z",
            "route_kind": "email",
        }

    def evidence(self, *, messages=None, events=None):
        return {
            "schema_version": "outbound-send-evidence/v1",
            "generated_at": "2026-09-13T10:09:00Z",
            "mailbox": {
                "complete": True,
                "query_id": "mail-parent",
                "messages": list(messages or []),
            },
            "slack": {
                "complete": True,
                "query_id": "slack-parent",
                "events": list(events or []),
            },
        }

    def scope(self):
        return {
            "schema_version": "outbound-send-buyer-scope/v1",
            "scope_id": "buyer-1",
            "members": [
                {
                    "email": "ceo@buyer.test",
                    "mailbox_complete": True,
                    "mailbox_query_id": "mail-ceo",
                    "slack_complete": True,
                    "slack_query_id": "slack-ceo",
                },
                {
                    "email": "info@buyer.test",
                    "mailbox_complete": True,
                    "mailbox_query_id": "mail-info",
                    "slack_complete": True,
                    "slack_query_id": "slack-info",
                },
            ],
        }

    def outbound(self, *, message_id="m1", counterparty="info@buyer.test", offer_id="offer-a", observed_at="2026-09-13T10:00:00Z"):
        return {
            "message_id": message_id,
            "direction": "outbound",
            "counterparty": counterparty,
            "observed_at": observed_at,
            "offer_id": offer_id,
        }

    def inbound(self, *, message_id="m-in", counterparty="info@buyer.test", observed_at="2026-09-13T10:05:00Z"):
        return {
            "message_id": message_id,
            "direction": "inbound",
            "counterparty": counterparty,
            "observed_at": observed_at,
            "offer_id": None,
        }

    def slack_event(self, *, event_id="s1", kind="hard_dnr", recipient="info@buyer.test", offer_id=None, observed_at="2026-09-13T10:01:00Z"):
        return {
            "event_id": event_id,
            "kind": kind,
            "recipient": recipient,
            "observed_at": observed_at,
            "offer_id": offer_id,
            "provider_message_id": None,
        }

    def test_same_offer_outbound_on_alias_blocks_net_new(self):
        result = buyer_scope.evaluate(
            self.intent(),
            self.evidence(messages=[self.outbound()]),
            self.scope(),
        )
        self.assertEqual(result["payload"]["decision"], "DO_NOT_RESEND")
        self.assertIn("mail:m1", result["payload"]["core"]["evidence"]["matched_refs"])

    def test_newer_inbound_on_alias_reopens_reply_only(self):
        result = buyer_scope.evaluate(
            self.intent(),
            self.evidence(
                messages=[
                    self.outbound(observed_at="2026-09-13T09:55:00Z"),
                    self.inbound(),
                ]
            ),
            self.scope(),
        )
        self.assertEqual(result["payload"]["decision"], "REPLY_ONLY")
        self.assertEqual(result["payload"]["core"]["reply_message_id"], "m-in")

    def test_hard_dnr_on_alias_is_terminal(self):
        result = buyer_scope.evaluate(
            self.intent(),
            self.evidence(events=[self.slack_event()]),
            self.scope(),
        )
        self.assertEqual(result["payload"]["decision"], "DO_NOT_RESEND")
        self.assertIn("slack:s1", result["payload"]["core"]["evidence"]["matched_refs"])

    def test_any_incomplete_member_mailbox_forces_hold(self):
        scope = self.scope()
        scope["members"][1]["mailbox_complete"] = False
        result = buyer_scope.evaluate(self.intent(), self.evidence(), scope)
        self.assertEqual(result["payload"]["decision"], "HOLD")
        self.assertFalse(result["payload"]["core"]["evidence"]["mailbox_complete"])

    def test_any_incomplete_member_slack_forces_hold(self):
        scope = self.scope()
        scope["members"][1]["slack_complete"] = False
        result = buyer_scope.evaluate(self.intent(), self.evidence(), scope)
        self.assertEqual(result["payload"]["decision"], "HOLD")
        self.assertFalse(result["payload"]["core"]["evidence"]["slack_complete"])

    def test_undeclared_address_does_not_widen_authority(self):
        outsider = self.outbound(counterparty="other@buyer.test")
        result = buyer_scope.evaluate(
            self.intent(),
            self.evidence(messages=[outsider]),
            self.scope(),
        )
        self.assertEqual(result["payload"]["decision"], "ALLOW_NEW")
        self.assertNotIn("mail:m1", result["payload"]["core"]["evidence"]["matched_refs"])

    def test_other_offer_on_alias_obeys_core_cooldown(self):
        result = buyer_scope.evaluate(
            self.intent(offer_id="offer-new"),
            self.evidence(messages=[self.outbound(offer_id="offer-old")]),
            self.scope(),
        )
        self.assertEqual(result["payload"]["decision"], "HOLD")
        self.assertIn("cross-offer cooldown", " ".join(result["payload"]["core"]["reasons"]))

    def test_intended_recipient_must_be_declared(self):
        with self.assertRaisesRegex(buyer_scope.ScopeError, "declared buyer-scope member"):
            buyer_scope.evaluate(
                self.intent(recipient="new@buyer.test"),
                self.evidence(),
                self.scope(),
            )

    def test_duplicate_normalized_member_is_rejected(self):
        scope = self.scope()
        duplicate = copy.deepcopy(scope["members"][0])
        duplicate["email"] = "CEO@BUYER.TEST"
        scope["members"].append(duplicate)
        with self.assertRaisesRegex(buyer_scope.ScopeError, "duplicate normalized email"):
            buyer_scope.evaluate(self.intent(), self.evidence(), scope)

    def test_completeness_flags_are_type_strict(self):
        scope = self.scope()
        scope["members"][0]["mailbox_complete"] = 1
        with self.assertRaisesRegex(buyer_scope.ScopeError, "must be a boolean"):
            buyer_scope.evaluate(self.intent(), self.evidence(), scope)

    def test_evaluation_does_not_mutate_source_objects(self):
        intent = self.intent()
        evidence = self.evidence(messages=[self.outbound()])
        scope = self.scope()
        intent_before = copy.deepcopy(intent)
        evidence_before = copy.deepcopy(evidence)
        scope_before = copy.deepcopy(scope)
        buyer_scope.evaluate(intent, evidence, scope)
        self.assertEqual(intent, intent_before)
        self.assertEqual(evidence, evidence_before)
        self.assertEqual(scope, scope_before)

    def test_receipt_is_deterministic_and_binds_source_plus_scoped_evidence(self):
        intent = self.intent()
        evidence = self.evidence(messages=[self.outbound()])
        scope = self.scope()
        first = buyer_scope.evaluate(intent, evidence, scope)
        second = buyer_scope.evaluate(intent, evidence, scope)
        self.assertEqual(first, second)
        self.assertFalse(first["payload"]["side_effects_authorized"])
        self.assertNotEqual(
            first["payload"]["source"]["evidence_sha256"],
            first["payload"]["source"]["scoped_evidence_sha256"],
        )
        self.assertEqual(
            first["payload"]["core_receipt_sha256"],
            buyer_scope.guard.digest_object(first["payload"]["core"]),
        )

    def test_member_order_does_not_change_decision_or_sorted_member_projection(self):
        scope_a = self.scope()
        scope_b = self.scope()
        scope_b["members"].reverse()
        first = buyer_scope.evaluate(self.intent(), self.evidence(), scope_a)
        second = buyer_scope.evaluate(self.intent(), self.evidence(), scope_b)
        self.assertEqual(first["payload"]["decision"], second["payload"]["decision"])
        self.assertEqual(
            first["payload"]["buyer_scope"]["members"],
            second["payload"]["buyer_scope"]["members"],
        )
        self.assertNotEqual(
            first["payload"]["buyer_scope"]["scope_sha256"],
            second["payload"]["buyer_scope"]["scope_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
