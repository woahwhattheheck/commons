from __future__ import annotations

import importlib
import unittest
from collections.abc import Mapping
from typing import Any, Iterator
from unittest import mock

from . import engine as direct_engine
from . import guarded as guard_module
from .acceptance import NOW, add, base_packet, offer_sent


class SharedFlippingPayload(Mapping[str, Any]):
    """One shared object changes canonical provider on a second traversal."""

    def __init__(self) -> None:
        self.provider_reads = 0
        self._data = {
            "provider_message_id": "shared-interest-message",
            "reply_to_event_id": "send-1",
        }

    def __getitem__(self, key: str) -> Any:
        if key == "provider":
            self.provider_reads += 1
            return "gmail" if self.provider_reads == 1 else "github"
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(("provider", *self._data))

    def __len__(self) -> int:
        return 3


class StatefulBoard(Mapping[str, Any]):
    """Board mapping exposes a different timestamp if traversed twice."""

    def __init__(self, board: Mapping[str, Any]) -> None:
        self._data = dict(board)
        self.evaluated_at_reads = 0

    def __getitem__(self, key: str) -> Any:
        if key == "evaluated_at":
            self.evaluated_at_reads += 1
            if self.evaluated_at_reads > 1:
                return "2099-01-01T00:00:00Z"
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        return key in self._data


class GraphSnapshotTests(unittest.TestCase):
    def test_shared_stateful_mapping_is_traversed_once_by_identity(self):
        packet = base_packet("shared-identity")
        offer_sent(packet)
        shared = SharedFlippingPayload()
        add(packet, "interest-1", "BUYER_INTEREST", "2026-09-13T12:20:00Z", shared)
        add(packet, "interest-2", "BUYER_INTEREST", "2026-09-13T12:21:00Z", shared)

        board = direct_engine.compile_board(packet, now=NOW)

        self.assertEqual(1, shared.provider_reads)
        self.assertEqual("HOLD", board["stage"])
        self.assertIn("PROVIDER_MESSAGE_ID_CONFLICT", board["reasons"])

    def test_memo_retains_identity_witness_and_rejects_stale_integer_alias(self):
        source = {"fresh": ["value"]}
        memo: dict[int, tuple[Any, Any]] = {}
        snapshot = guard_module._detach(source, _memo=memo)
        witness, retained = memo[id(source)]
        self.assertIs(witness, source)
        self.assertIs(retained, snapshot)

        later = {"different": "object"}
        stale_witness = {"old": "object"}
        poisoned = {id(later): (stale_witness, {"wrong": "snapshot"})}
        with self.assertRaisesRegex(direct_engine.ContractError, "identity collision"):
            guard_module._detach(later, _memo=poisoned)

    def test_cycle_is_contract_error_not_recursion(self):
        packet = base_packet("cycle")
        cycle: list[Any] = []
        cycle.append(cycle)
        packet["events"] = cycle
        with self.assertRaisesRegex(direct_engine.ContractError, "cyclic input graph"):
            direct_engine.compile_board(packet, now=NOW)

    def test_depth_is_bounded_before_core_validation(self):
        packet = base_packet("depth")
        deep: list[Any] = []
        cursor = deep
        for _ in range(guard_module._MAX_SNAPSHOT_DEPTH + 2):
            child: list[Any] = []
            cursor.append(child)
            cursor = child
        packet["unexpected-hostile-graph"] = deep
        with self.assertRaisesRegex(direct_engine.ContractError, "depth limit"):
            direct_engine.compile_board(packet, now=NOW)

    def test_node_budget_is_bounded_before_core_validation(self):
        packet = base_packet("budget")
        with mock.patch.object(guard_module, "_MAX_SNAPSHOT_NODES", 4):
            with self.assertRaisesRegex(direct_engine.ContractError, "node limit"):
                direct_engine.compile_board(packet, now=NOW)

    def test_verify_board_snapshots_stateful_board_once(self):
        packet = base_packet("board-stateful")
        offer_sent(packet)
        board = direct_engine.compile_board(packet, now=NOW)
        stateful = StatefulBoard(board)

        result = direct_engine.verify_board(packet, stateful, now=NOW)

        self.assertEqual(1, stateful.evaluated_at_reads)
        self.assertTrue(result["historical_valid"])
        self.assertEqual(board["receipt_sha256"], result["historical_receipt_sha256"])

    def test_verify_board_rejects_cyclic_board_graph_before_json(self):
        packet = base_packet("board-cycle")
        board = direct_engine.compile_board(packet, now=NOW)
        cycle: list[Any] = []
        cycle.append(cycle)
        board["hostile_graph"] = cycle

        with self.assertRaisesRegex(direct_engine.ContractError, "cyclic input graph"):
            direct_engine.verify_board(packet, board, now=NOW)

    def test_verify_board_rejects_deep_board_graph_before_core(self):
        packet = base_packet("board-depth")
        board = direct_engine.compile_board(packet, now=NOW)
        deep: list[Any] = []
        cursor = deep
        for _ in range(guard_module._MAX_SNAPSHOT_DEPTH + 2):
            child: list[Any] = []
            cursor.append(child)
            cursor = child
        board["hostile_graph"] = deep

        with self.assertRaisesRegex(direct_engine.ContractError, "depth limit"):
            direct_engine.verify_board(packet, board, now=NOW)

    def test_verify_board_enforces_shared_packet_board_node_budget(self):
        packet = base_packet("board-budget")
        board = direct_engine.compile_board(packet, now=NOW)
        board["hostile_graph"] = [{} for _ in range(200)]

        with mock.patch.object(guard_module, "_MAX_SNAPSHOT_NODES", 100):
            with self.assertRaisesRegex(direct_engine.ContractError, "node limit"):
                direct_engine.verify_board(packet, board, now=NOW)

    def test_engine_reload_keeps_graph_guard_installed(self):
        reloaded = importlib.reload(direct_engine)
        packet = base_packet("reload-cycle")
        cycle: list[Any] = []
        cycle.append(cycle)
        packet["events"] = cycle
        with self.assertRaisesRegex(reloaded.ContractError, "cyclic input graph"):
            reloaded.compile_board(packet, now=NOW)


if __name__ == "__main__":
    unittest.main()
