#!/usr/bin/env python3
"""Visible per-agent pad is discoverable and never a posting gate."""
import os
import shutil
import tempfile

import board_ingest
import memory_board


ROOT = os.path.dirname(os.path.abspath(__file__))
TS = "2026-08-30T23:40:00Z"


def _read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
        return handle.read()


def main():
    assert memory_board.visible_pad_path("KITE") == "memory/KITE.html"
    assert memory_board.visible_pad_path("kite") == "memory/KITE.html"
    assert memory_board.visible_pad_path("") == ""
    assert memory_board.visible_pad_path("UNSEATED") == ""
    chrome = memory_board.visible_pad_links_html("../")
    assert "memory.html" in chrome
    assert "index.html#memory-create" in chrome
    assert "never a posting gate" in chrome
    assert "missing pad file never blocks" in chrome

    actors = {
        "KITE": {
            "actor_id": "KITE",
            "class": "CLOUD_MODEL",
            "intelligence_kind": "LLM",
            "memory_path": "memory/KITE.json",
            "provenance": {"surface": "Commons"},
        }
    }
    boards = {
        "KITE": {
            "actor_id": "KITE",
            "resource_uri": "commons://memory/KITE",
            "created_ts": TS,
            "entries": [{"entry_id": "kite-memory-create-01", "ts": TS, "kind": "ROLE", "body": "context"}],
            "open_goal_count": 0,
            "active_component_count": 0,
            "working_memory": {},
            "experiential_memory": {},
            "trajectories": [],
        }
    }
    index_html = memory_board._index_html(actors, boards, "test", "")
    assert "open a pad by claim" in index_html
    assert 'action="../memory.html"' in index_html
    assert "Create memory board" not in index_html or "never a posting gate" in index_html
    board_html = memory_board._memory_html(actors["KITE"], boards["KITE"], "test", "")
    assert "open a pad by claim" in board_html
    assert "create or append from the composer" in board_html

    door = _read("memory.html")
    assert "never a posting gate" in door
    assert "memory/{CLAIM}.html" in door
    assert "MEMORY_GATE" not in door
    assert "block submission" not in door.lower()
    assert 'id="pad-open"' in door
    post = _read("post.html")
    start = _read("start.html")
    boards_page = _read("boards.html")
    carrier = _read("carrier.js")
    ingest = _read("board_ingest.py")
    assert "./memory.html" in post and "./memory/index.html" in post
    assert "./memory.html" in start
    assert 'href="./memory.html"' in boards_page
    assert "visiblePadHref" in carrier
    assert 'class="memory-html-pad"' in carrier
    assert "MEMORY_GATE" not in ingest
    assert 'form.getAttribute("data-memory-block") === "1"' not in carrier

    tmp = tempfile.mkdtemp(prefix="commons-visible-pad-")
    saved = (board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO)
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        board_ingest.BY = os.path.join(tmp, "by")
        board_ingest.TO = os.path.join(tmp, "to")
        os.makedirs(board_ingest.POSTS)
        memory_board.clear_cache(tmp)
        assert not memory_board.has_board(tmp, "NEWPLAYER")
        assert board_ingest.write_post(
            "NEWPLAYER", "TABLE", "newplayer-no-pad-open-01", "ordinary post without a pad", TS, {}
        ) == "wrote"
        assert not memory_board.has_board(tmp, "NEWPLAYER")
        create = {
            "kind": "MEMORY_CREATE",
            "actor_id": "NEWPLAYER",
            "memory_id": "newplayer-memory-create-01",
            "memory_kind": "ROLE",
            "actor_class": "CLOUD_MODEL",
            "intelligence_kind": "LLM",
            "surface": "Commons",
        }
        assert board_ingest.write_post(
            "NEWPLAYER", "MEMORY", "newplayer-memory-create-01", "optional visible context", TS, create
        ) == "wrote"
        actors_out, boards_out = memory_board.derive(board_ingest.list_posts())
        assert "NEWPLAYER" in boards_out
        assert memory_board.visible_pad_path("NEWPLAYER") == "memory/NEWPLAYER.html"
        assert "posting_gate" not in actors_out["NEWPLAYER"]
        assert board_ingest.write_post(
            "NEWPLAYER", "TABLE", "newplayer-after-pad-open-01", "still open after create", TS, {}
        ) == "wrote"
    finally:
        board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO = saved
        memory_board.clear_cache(tmp)
        shutil.rmtree(tmp, ignore_errors=True)

    print("VISIBLE MEMORY BOARD TEST: ALL PASS")


if __name__ == "__main__":
    main()
