#!/usr/bin/env python3
"""Per-session memory is opt-in, delta-only, and compaction-resumable."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import memory_board
from host import observatory


CREATE_TS = "2026-08-29T06:00:00Z"


def memory_rows():
    create_id = "kite-memory-create-01"
    return [
        (CREATE_TS, {
            "from": "KITE", "to": "MEMORY", "id": create_id,
            "ts": CREATE_TS, "kind": "MEMORY_CREATE", "actor_id": "KITE",
            "memory_id": create_id, "memory_kind": "ROLE",
            "actor_class": "CLOUD_MODEL", "intelligence_kind": "LLM",
            "surface": "Commons",
        }, "builder role"),
        ("2026-08-29T06:00:01Z", {
            "from": "KITE", "to": "MEMORY", "id": "kite-memory-note-0001",
            "ts": "2026-08-29T06:00:01Z", "kind": "MEMORY_APPEND",
            "actor_id": "KITE", "memory_id": create_id,
            "memory_kind": "DECISION",
        }, "continue the additive lane"),
        ("2026-08-29T06:00:02Z", {
            "from": "KITE", "to": "MEMORY", "id": "kite-session-bind-0001",
            "ts": "2026-08-29T06:00:02Z", "kind": "SESSION_MEMORY",
            "actor_id": "KITE", "session_id": "provider-session-0001",
            "memory_id": create_id,
        }, "optional session context"),
    ]


class TestSessionMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="commons-session-memory-")
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, "memory"))
        actors, boards = memory_board.derive(memory_rows())
        del actors
        with open(os.path.join(self.root, "memory", "KITE.json"), "w", encoding="utf-8") as handle:
            json.dump(boards["KITE"], handle)
        with open(os.path.join(self.root, "memory", "sessions.json"), "w", encoding="utf-8") as handle:
            json.dump(memory_board.derive_session_bindings(memory_rows(), boards), handle)

    def tearDown(self):
        self.tmp.cleanup()

    def packet(self, **kwargs):
        return memory_board.session_memory_packet(
            self.root, "provider-session-0001", **kwargs
        )

    def test_unbound_session_never_blocks(self):
        row = memory_board.session_memory_packet(self.root, "unbound-session")
        self.assertEqual(row["state"], "NO_OPT_IN")
        self.assertFalse(row["should_insert"])
        self.assertFalse(row["posting_gate"])

    def test_rebuild_projects_explicit_binding(self):
        def write(path, content):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)

        memory_board.rebuild(self.root, memory_rows(), write, "test", "")
        with open(os.path.join(self.root, "memory", "sessions.json"), encoding="utf-8") as handle:
            projection = json.load(handle)
        self.assertFalse(projection["posting_gate"])
        self.assertEqual(
            projection["sessions"][0]["session_id"], "provider-session-0001"
        )

    def test_initial_insert_then_no_delta(self):
        first = self.packet()
        self.assertEqual(first["state"], "INSERT")
        self.assertEqual(first["reason"], "INITIAL_INSERT")
        self.assertEqual(len(first["entries"]), 2)
        self.assertIn(memory_board.UNTRUSTED_DATA_LABEL, first["entries"][0]["data_trust"])
        second = self.packet(after_entry_id=first["next_entry_id"])
        self.assertEqual(second["state"], "NO_DELTA")
        self.assertFalse(second["should_insert"])

    def test_only_new_entries_follow_cursor(self):
        board_path = os.path.join(self.root, "memory", "KITE.json")
        with open(board_path, encoding="utf-8") as handle:
            board = json.load(handle)
        board["entries"].append({
            "entry_id": "kite-memory-note-0002", "ts": "2026-08-29T06:00:03Z",
            "kind": "HANDOFF", "body": "new delta only",
        })
        with open(board_path, "w", encoding="utf-8") as handle:
            json.dump(board, handle)
        row = self.packet(after_entry_id="kite-memory-note-0001")
        self.assertEqual(row["reason"], "DELTA")
        self.assertEqual([entry["entry_id"] for entry in row["entries"]], ["kite-memory-note-0002"])

    def test_compaction_reinserts_once(self):
        first = self.packet(
            after_entry_id="kite-memory-note-0001",
            compaction_epoch="compact-2",
            acknowledged_compaction_epoch="compact-1",
        )
        self.assertEqual(first["reason"], "COMPACTION_REINSERT")
        self.assertEqual(len(first["entries"]), 2)
        second = self.packet(
            after_entry_id=first["next_entry_id"],
            compaction_epoch="compact-2",
            acknowledged_compaction_epoch=first["acknowledge_compaction_epoch"],
        )
        self.assertEqual(second["state"], "NO_DELTA")

    def test_observatory_continuation_carries_resume_context(self):
        result = observatory.continue_from(self.root, {"session_id": "provider-session-0001"})
        self.assertTrue(result["session_memory"]["should_insert"])
        self.assertEqual(result["resume_context"], [result["session_memory"]["context"]])
        self.assertFalse(result["authority"])
        self.assertFalse(result["replay_finished_prompt"])


if __name__ == "__main__":
    unittest.main()
