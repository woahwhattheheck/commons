from __future__ import annotations

import copy
import importlib
import unittest
from collections.abc import Mapping
from typing import Any, Iterator

from revenue.outbound_connector_lease.key import SUPPORTED_REPLY_PROVIDERS

from . import engine as direct_engine
from .acceptance import D, E, NOW, add, base_packet, offer_sent
from .guarded import CANONICAL_MESSAGE_PROVIDERS, ContractError, compile_board, verify_board


class FlippingProviderPayload(Mapping[str, Any]):
    """Stable-key mapping whose provider value changes after N reads."""

    def __init__(self, payload: Mapping[str, Any], canonical_reads: int) -> None:
        self._payload = dict(payload)
        self._canonical_reads = canonical_reads
        self._provider_reads = 0

    def __getitem__(self, key: str) -> Any:
        if key == "provider":
            self._provider_reads += 1
            if self._provider_reads <= self._canonical_reads:
                return "gmail"
            return "gmail-api"
        return self._payload[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._payload)

    def __len__(self) -> int:
        return len(self._payload)


class SharedFlippingProviderPayload(Mapping[str, Any]):
    """One aliased payload that returns a different canonical provider per read."""

    def __init__(self) -> None:
        self._payload = {
            "provider": "gmail",
            "provider_message_id": "m-shared",
            "reply_to_event_id": "send-1",
        }
        self.provider_reads = 0

    def __getitem__(self, key: str) -> Any:
        if key == "provider":
            self.provider_reads += 1
            return "gmail" if self.provider_reads == 1 else "github"
        return self._payload[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._payload)

    def __len__(self) -> int:
        return len(self._payload)


def conflict_packet(name: str) -> dict[str, Any]:
    packet = base_packet(name)
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
    return packet


def shared_alias_packet(
    name: str, *, stateful: bool
) -> tuple[dict[str, Any], Mapping[str, Any]]:
    packet = base_packet(name)
    offer_sent(packet)
    shared: Mapping[str, Any]
    if stateful:
        shared = SharedFlippingProviderPayload()
    else:
        shared = {
            "provider": "gmail",
            "provider_message_id": "m-shared",
            "reply_to_event_id": "send-1",
        }
    add(packet, "interest-1", "BUYER_INTEREST", "2026-09-13T12:20:00Z", shared)
    add(packet, "interest-2", "BUYER_INTEREST", "2026-09-13T12:21:00Z", shared)
    return packet, shared


class GuardedProviderTests(unittest.TestCase):
    def test_registry_is_shared_with_outbound_reply_lease(self):
        self.assertIs(CANONICAL_MESSAGE_PROVIDERS, SUPPORTED_REPLY_PROVIDERS)

    def test_all_canonical_message_providers_are_accepted(self):
        for provider in sorted(CANONICAL_MESSAGE_PROVIDERS):
            with self.subTest(provider=provider):
                packet = base_packet(f"canonical-{provider}")
                offer_sent(packet)
                packet["events"][0]["payload"]["provider"] = provider
                self.assertEqual(compile_board(packet, now=NOW)["stage"], "AWAITING_BUYER")

    def test_aliases_and_malformed_provider_are_rejected(self):
        for provider in (
            "email",
            "googlemail",
            "gmail-api",
            "github-api",
            "slack-api",
            "webform",
            "GMAIL",
            "gmail.com",
            "smtp",
            "",
            ["gmail"],
        ):
            with self.subTest(provider=provider):
                packet = base_packet("alias")
                offer_sent(packet)
                packet["events"][0]["payload"]["provider"] = provider
                with self.assertRaises(ContractError):
                    compile_board(packet, now=NOW)

    def test_alias_cannot_split_one_message_across_semantic_facts(self):
        packet = conflict_packet("split")
        packet["events"][1]["payload"]["provider"] = "googlemail"
        with self.assertRaises(ContractError):
            compile_board(packet, now=NOW)

    def test_direct_engine_alias_is_rejected_after_package_import(self):
        packet = base_packet("direct-engine")
        offer_sent(packet)
        packet["events"][0]["payload"]["provider"] = "gmail-api"
        with self.assertRaises(ContractError):
            direct_engine.compile_board(packet, now=NOW)

    def test_canonical_same_message_conflict_still_holds(self):
        board = compile_board(conflict_packet("canonical-conflict"), now=NOW)
        self.assertEqual(board["stage"], "HOLD")
        self.assertIn("PROVIDER_MESSAGE_ID_CONFLICT", board["reasons"])

    def test_package_compile_consumes_same_snapshot_it_validates(self):
        packet = conflict_packet("package-flip")
        original = packet["events"][0]["payload"]
        packet["events"][0]["payload"] = FlippingProviderPayload(
            original, canonical_reads=2
        )
        board = compile_board(packet, now=NOW)
        self.assertEqual(board["stage"], "HOLD")
        self.assertIn("PROVIDER_MESSAGE_ID_CONFLICT", board["reasons"])

    def test_direct_engine_compile_consumes_same_snapshot_it_validates(self):
        packet = conflict_packet("direct-flip")
        original = packet["events"][0]["payload"]
        packet["events"][0]["payload"] = FlippingProviderPayload(
            original, canonical_reads=1
        )
        board = direct_engine.compile_board(packet, now=NOW)
        self.assertEqual(board["stage"], "HOLD")
        self.assertIn("PROVIDER_MESSAGE_ID_CONFLICT", board["reasons"])

    def test_package_verify_uses_one_generation_for_both_evaluations(self):
        canonical = conflict_packet("verify-flip")
        board = compile_board(canonical, now=NOW)
        hostile = copy.deepcopy(canonical)
        original = hostile["events"][0]["payload"]
        hostile["events"][0]["payload"] = FlippingProviderPayload(
            original, canonical_reads=2
        )
        result = verify_board(hostile, board, now=NOW)
        self.assertTrue(result["historical_valid"])
        self.assertEqual(result["current_stage"], "HOLD")
        self.assertIn("PROVIDER_MESSAGE_ID_CONFLICT", result["current_reasons"])

    def test_direct_engine_verify_uses_one_generation_for_both_evaluations(self):
        canonical = conflict_packet("direct-verify-flip")
        board = compile_board(canonical, now=NOW)
        hostile = copy.deepcopy(canonical)
        original = hostile["events"][0]["payload"]
        hostile["events"][0]["payload"] = FlippingProviderPayload(
            original, canonical_reads=1
        )
        result = direct_engine.verify_board(hostile, board, now=NOW)
        self.assertTrue(result["historical_valid"])
        self.assertEqual(result["current_stage"], "HOLD")
        self.assertIn("PROVIDER_MESSAGE_ID_CONFLICT", result["current_reasons"])

    def test_verify_rejects_plain_alias_even_for_preexisting_board(self):
        packet = base_packet("verify-alias")
        offer_sent(packet)
        board = compile_board(packet, now=NOW)
        aliased = copy.deepcopy(packet)
        aliased["events"][0]["payload"]["provider"] = "gmail-api"
        with self.assertRaises(ContractError):
            verify_board(aliased, board, now=NOW)

    def test_shared_payload_alias_is_read_once_by_package_compile(self):
        packet, shared = shared_alias_packet("shared-package", stateful=True)
        board = compile_board(packet, now=NOW)
        self.assertEqual(shared.provider_reads, 1)
        self.assertEqual(board["stage"], "HOLD")
        self.assertIn("PROVIDER_MESSAGE_ID_CONFLICT", board["reasons"])

    def test_shared_payload_alias_is_read_once_by_direct_compile(self):
        packet, shared = shared_alias_packet("shared-direct", stateful=True)
        board = direct_engine.compile_board(packet, now=NOW)
        self.assertEqual(shared.provider_reads, 1)
        self.assertEqual(board["stage"], "HOLD")
        self.assertIn("PROVIDER_MESSAGE_ID_CONFLICT", board["reasons"])

    def test_shared_payload_alias_is_read_once_by_package_verify(self):
        canonical, _ = shared_alias_packet("shared-verify", stateful=False)
        board = compile_board(canonical, now=NOW)
        hostile, shared = shared_alias_packet("shared-verify", stateful=True)
        result = verify_board(hostile, board, now=NOW)
        self.assertEqual(shared.provider_reads, 1)
        self.assertTrue(result["historical_valid"])
        self.assertEqual(result["current_stage"], "HOLD")
        self.assertIn("PROVIDER_MESSAGE_ID_CONFLICT", result["current_reasons"])

    def test_shared_payload_alias_is_read_once_by_direct_verify(self):
        canonical, _ = shared_alias_packet("shared-direct-verify", stateful=False)
        board = compile_board(canonical, now=NOW)
        hostile, shared = shared_alias_packet("shared-direct-verify", stateful=True)
        result = direct_engine.verify_board(hostile, board, now=NOW)
        self.assertEqual(shared.provider_reads, 1)
        self.assertTrue(result["historical_valid"])
        self.assertEqual(result["current_stage"], "HOLD")
        self.assertIn("PROVIDER_MESSAGE_ID_CONFLICT", result["current_reasons"])

    def test_cyclic_mapping_fails_closed_before_core_recursion(self):
        packet = base_packet("mapping-cycle")
        packet["cycle"] = packet
        with self.assertRaisesRegex(ContractError, "cyclic mapping"):
            compile_board(packet, now=NOW)

    def test_cyclic_sequence_fails_closed_before_core_recursion(self):
        packet = base_packet("sequence-cycle")
        loop: list[Any] = []
        loop.append(loop)
        packet["cycle"] = loop
        with self.assertRaisesRegex(ContractError, "cyclic sequence"):
            compile_board(packet, now=NOW)

    def test_snapshot_depth_is_bounded(self):
        packet = base_packet("depth")
        cursor: dict[str, Any] = {}
        packet["padding"] = cursor
        for _ in range(70):
            child: dict[str, Any] = {}
            cursor["next"] = child
            cursor = child
        with self.assertRaisesRegex(ContractError, "depth limit"):
            compile_board(packet, now=NOW)

    def test_snapshot_nodes_are_bounded(self):
        packet = base_packet("nodes")
        packet["padding"] = [None] * 250_001
        with self.assertRaisesRegex(ContractError, "node limit"):
            compile_board(packet, now=NOW)

    def test_engine_reload_reinstalls_direct_guards(self):
        reloaded = importlib.reload(direct_engine)
        self.assertIs(reloaded.compile_board, compile_board)
        self.assertIs(reloaded.verify_board, verify_board)

        packet = base_packet("reload-alias")
        offer_sent(packet)
        packet["events"][0]["payload"]["provider"] = "gmail-api"
        with self.assertRaises(ContractError):
            reloaded.compile_board(packet, now=NOW)

        shared_packet, shared = shared_alias_packet("reload-shared", stateful=True)
        board = reloaded.compile_board(shared_packet, now=NOW)
        self.assertEqual(shared.provider_reads, 1)
        self.assertEqual(board["stage"], "HOLD")
        self.assertIn("PROVIDER_MESSAGE_ID_CONFLICT", board["reasons"])


if __name__ == "__main__":
    unittest.main()
