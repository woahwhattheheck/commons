from __future__ import annotations

import copy
import unittest

from revenue.outbound_connector_lease.key import SUPPORTED_REPLY_PROVIDERS

from . import engine as direct_engine
from .acceptance import D, E, NOW, add, base_packet, offer_sent
from .guarded import CANONICAL_MESSAGE_PROVIDERS, ContractError, compile_board, verify_board


class GuardedProviderTests(unittest.TestCase):
    def test_registry_is_shared_with_outbound_reply_lease(self):
        self.assertIs(CANONICAL_MESSAGE_PROVIDERS, SUPPORTED_REPLY_PROVIDERS)

    def test_all_canonical_message_providers_are_accepted(self):
        for provider in sorted(CANONICAL_MESSAGE_PROVIDERS):
            with self.subTest(provider=provider):
                packet = base_packet(f"canonical-{provider}")
                offer_sent(packet)
                packet["events"][0]["payload"]["provider"] = provider
                board = compile_board(packet, now=NOW)
                self.assertEqual(board["stage"], "AWAITING_BUYER")

    def test_known_aliases_and_unknown_spellings_are_rejected(self):
        for provider in ("email", "googlemail", "gmail-api", "github-api", "slack-api", "webform", "GMAIL", "gmail.com", "smtp", ""):
            with self.subTest(provider=provider):
                packet = base_packet("alias")
                offer_sent(packet)
                packet["events"][0]["payload"]["provider"] = provider
                with self.assertRaises(ContractError):
                    compile_board(packet, now=NOW)

    def test_malformed_provider_type_is_contract_error(self):
        packet = base_packet("malformed")
        offer_sent(packet)
        packet["events"][0]["payload"]["provider"] = ["gmail"]
        with self.assertRaises(ContractError):
            compile_board(packet, now=NOW)

    def test_alias_cannot_split_one_message_across_semantic_facts(self):
        packet = base_packet("split")
        add(
            packet,
            "send-1",
            "OFFER_SENT",
            "2026-09-13T12:10:00Z",
            {
                "provider": "gmail",
                "provider_message_id": "m-shared",
                "scope_sha256": D,
                "terms_sha256": E,
            },
        )
        add(
            packet,
            "interest-1",
            "BUYER_INTEREST",
            "2026-09-13T12:20:00Z",
            {
                "provider": "googlemail",
                "provider_message_id": "m-shared",
                "reply_to_event_id": "send-1",
            },
        )
        with self.assertRaises(ContractError):
            compile_board(packet, now=NOW)

    def test_direct_engine_compile_is_guarded_after_package_import(self):
        packet = base_packet("direct-engine")
        offer_sent(packet)
        packet["events"][0]["payload"]["provider"] = "gmail-api"
        with self.assertRaises(ContractError):
            direct_engine.compile_board(packet, now=NOW)

    def test_canonical_same_message_conflict_still_holds_in_engine(self):
        packet = base_packet("canonical-conflict")
        add(
            packet,
            "send-1",
            "OFFER_SENT",
            "2026-09-13T12:10:00Z",
            {
                "provider": "gmail",
                "provider_message_id": "m-shared",
                "scope_sha256": D,
                "terms_sha256": E,
            },
        )
        add(
            packet,
            "interest-1",
            "BUYER_INTEREST",
            "2026-09-13T12:20:00Z",
            {
                "provider": "gmail",
                "provider_message_id": "m-shared",
                "reply_to_event_id": "send-1",
            },
        )
        board = compile_board(packet, now=NOW)
        self.assertEqual(board["stage"], "HOLD")
        self.assertIn("PROVIDER_MESSAGE_ID_CONFLICT", board["reasons"])

    def test_verify_rejects_alias_even_for_preexisting_board(self):
        packet = base_packet("verify")
        offer_sent(packet)
        board = compile_board(packet, now=NOW)
        aliased = copy.deepcopy(packet)
        aliased["events"][0]["payload"]["provider"] = "gmail-api"
        with self.assertRaises(ContractError):
            verify_board(aliased, board, now=NOW)


if __name__ == "__main__":
    unittest.main()
