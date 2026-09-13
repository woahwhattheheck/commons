from __future__ import annotations

import json
import unittest

from tools.outbound_send_guard import buyer_scope


class BuyerScopeCustodyEscapeTests(unittest.TestCase):
    @staticmethod
    def encoded(value):
        return json.dumps(value, sort_keys=True).encode("utf-8") + b"\n"

    @staticmethod
    def intent(*, offer_id="offer-a"):
        return {
            "schema_version": "outbound-send-intent/v1",
            "intent_id": "intent-1",
            "recipient": "ceo@buyer.test",
            "offer_id": offer_id,
            "requested_at": "2026-09-13T10:10:00Z",
            "route_kind": "email",
        }

    @staticmethod
    def evidence():
        return {
            "schema_version": "outbound-send-evidence/v1",
            "generated_at": "2026-09-13T10:09:00Z",
            "mailbox": {"complete": True, "query_id": "mail-parent", "messages": []},
            "slack": {"complete": True, "query_id": "slack-parent", "events": []},
        }

    @staticmethod
    def scope():
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
                }
            ],
        }

    def test_internal_custody_path_reparses_and_rejects_mismatched_bytes(self):
        intent = self.intent()
        evidence = self.evidence()
        scope = self.scope()
        with self.assertRaisesRegex(
            buyer_scope.ScopeError,
            "raw-byte custody does not match evaluated source objects",
        ):
            buyer_scope._evaluate(
                intent,
                evidence,
                scope,
                raw_bytes=(
                    self.encoded(self.intent(offer_id="different-offer")),
                    self.encoded(evidence),
                    self.encoded(scope),
                ),
            )

    def test_internal_custody_path_rejects_digest_like_strings(self):
        with self.assertRaisesRegex(
            buyer_scope.ScopeError,
            "exactly three byte strings",
        ):
            buyer_scope._evaluate(
                self.intent(),
                self.evidence(),
                self.scope(),
                raw_bytes=("0" * 64, b"{}", b"{}"),
            )


if __name__ == "__main__":
    unittest.main()
