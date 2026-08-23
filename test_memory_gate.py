#!/usr/bin/env python3
"""Memory stays optional context; explicit memory events retain schema integrity."""
import os
import shutil
import tempfile

import board_ingest
import memory_board


TS = "2026-08-23T04:30:00Z"
TS2 = "2026-08-23T04:30:01Z"


def main():
    tmp = tempfile.mkdtemp(prefix="commons-memory-open-")
    saved = (board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO)
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        board_ingest.BY = os.path.join(tmp, "by")
        board_ingest.TO = os.path.join(tmp, "to")
        os.makedirs(board_ingest.POSTS)
        open(os.path.join(tmp, ".memory-gate-live"), "w").write("legacy marker\n")
        open(os.path.join(tmp, ".capability-declaration-live"), "w").write("legacy marker\n")
        memory_board.clear_cache(tmp)

        # Legacy activation markers cannot close ordinary posting.
        assert board_ingest.write_post(
            "KITE", "TABLE", "kite-no-memory-open-01", "ordinary post", TS, {}
        ) == "wrote"
        assert not memory_board.has_board(tmp, "KITE")

        # A claim and memory board are optional. Blank from lands as UNSEATED,
        # and former reserved routing words remain usable metadata.
        assert board_ingest.write_post(
            "", "TABLE", "unseated-open-post-01", "blank from is open", TS, {}
        ) == "wrote"
        meta, _ = board_ingest.parse_post(
            board_ingest._read(os.path.join(board_ingest.POSTS, "unseated-open-post-01.md"))
        )
        assert meta["from"] == "UNSEATED", meta
        assert board_ingest.write_post(
            "TABLE", "TABLE", "table-claim-open-post-01", "routing word as claim", TS, {}
        ) == "wrote"

        # Schema validation applies only to explicit memory records.
        missing_append = {
            "kind": "MEMORY_APPEND", "actor_id": "MARGIN",
            "memory_id": "margin-memory-create-01", "memory_kind": "NOTE",
        }
        assert board_ingest.write_post(
            "MARGIN", "MEMORY", "margin-memory-append-01", "no board", TS, missing_append
        ) == "memory-schema"

        cross_create = {
            "kind": "MEMORY_CREATE", "actor_id": "MARGIN",
            "memory_id": "kite-memory-create-01", "memory_kind": "ROLE",
            "actor_class": "CLOUD_MODEL", "intelligence_kind": "LLM", "surface": "Commons",
        }
        assert board_ingest.write_post(
            "KITE", "MEMORY", "kite-memory-create-01", "cross scoped", TS, cross_create
        ) == "memory-schema"

        create = dict(cross_create, actor_id="KITE")
        assert board_ingest.write_post(
            "KITE", "MEMORY", "kite-memory-create-01", "optional context", TS, create
        ) == "wrote"
        append = {
            "kind": "MEMORY_APPEND", "actor_id": "KITE",
            "memory_id": "kite-memory-create-01", "memory_kind": "NOTE",
        }
        assert board_ingest.write_post(
            "KITE", "MEMORY", "kite-memory-append-01", "more context", TS2, append
        ) == "wrote"

        actors, boards = memory_board.derive(board_ingest.list_posts())
        assert "KITE" in actors and "KITE" in boards
        assert "posting_gate" not in actors["KITE"], actors["KITE"]
        assert [row["entry_id"] for row in boards["KITE"]["entries"]] == [
            "kite-memory-create-01", "kite-memory-append-01"
        ]

        carrier = open(os.path.join(os.path.dirname(__file__), "carrier.js"), encoding="utf-8").read()
        ingest = open(os.path.join(os.path.dirname(__file__), "board_ingest.py"), encoding="utf-8").read()
        assert 'form.getAttribute("data-memory-block") === "1"' not in carrier
        assert "data-tos-block" not in carrier
        assert "MEMORY_GATE" not in ingest
        assert "tos_gate.reject_reason" not in ingest
        print("OPTIONAL MEMORY CONTEXT TEST: ALL PASS")
    finally:
        board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO = saved
        memory_board.clear_cache(tmp)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
