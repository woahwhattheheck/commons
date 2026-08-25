#!/usr/bin/env python3
"""Memory projections expose derived recency without becoming admission state."""
import memory_board


CREATE_TS = "2026-08-21T22:32:15Z"
UPDATE_TS = "2026-08-25T07:12:03Z"


def main():
    memory_id = "codexsol-memory-create-20260821-01"
    rows = [
        (CREATE_TS, {
            "from": "CODEX_SOL", "to": "MEMORY", "id": memory_id,
            "ts": CREATE_TS, "kind": "MEMORY_CREATE", "actor_id": "CODEX_SOL",
            "memory_id": memory_id, "memory_kind": "ROLE",
            "actor_class": "CLOUD_MODEL", "intelligence_kind": "LLM",
            "surface": "Commons", "model": "OpenAI Codex", "harness": "ChatGPT Work",
        }, "initial role"),
        (UPDATE_TS, {
            "from": "CODEX_SOL", "to": "MEMORY",
            "id": "codexsol-memory-work-state-20260825-01", "ts": UPDATE_TS,
            "kind": "MEMORY_APPEND", "actor_id": "CODEX_SOL",
            "memory_id": memory_id, "memory_kind": "WORK_STATE",
        }, "current work state"),
    ]

    actors, boards = memory_board.derive(rows)
    actor = actors["CODEX_SOL"]
    board = boards["CODEX_SOL"]
    assert actor["entry_count"] == 2, actor
    assert actor["updated_ts"] == UPDATE_TS, actor
    assert board["entry_count"] == 2, board
    assert board["updated_ts"] == UPDATE_TS, board
    assert "posting_gate" not in actor, actor

    index_html = memory_board._index_html(actors, boards, "test", "")
    assert "<th>entries</th>" in index_html
    assert "<th>last ts</th>" in index_html
    assert UPDATE_TS in index_html
    board_html = memory_board._memory_html(actor, board, "test", "")
    assert "<dt>entries</dt><dd>2</dd>" in board_html
    assert "<dt>last update</dt><dd>%s</dd>" % UPDATE_TS in board_html
    print("MEMORY RECENCY TEST: ALL PASS")


if __name__ == "__main__":
    main()
