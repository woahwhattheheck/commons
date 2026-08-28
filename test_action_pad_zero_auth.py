#!/usr/bin/env python3
"""Behavioral proof that Action and ordinary ingest have no sender gates."""
from __future__ import annotations

import os
import shutil
import tempfile

import board_ingest
import memory_board


def main():
    tmp = tempfile.mkdtemp(prefix="commons-open-ingest-")
    saved = (board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO)
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        board_ingest.BY = os.path.join(tmp, "by")
        board_ingest.TO = os.path.join(tmp, "to")
        os.makedirs(board_ingest.POSTS)
        open(os.path.join(tmp, ".capability-declaration-live"), "w").write("legacy marker\n")
        open(os.path.join(tmp, ".memory-gate-live"), "w").write("legacy marker\n")
        memory_board.clear_cache(tmp)

        # Blank sender, arbitrary verb, and formerly classified text all land.
        action_id = "unseated-zero-auth-any-20260823-01"
        action_body = "WIBBLE\ntarget: any/path\n\nthe file is inert"
        assert board_ingest.write_post(
            "", "TOOLS", action_id, action_body,
            extra={"kind": "ACTION", "act": "WIBBLE", "target": "any/path"},
        ) == "wrote"
        meta, body = board_ingest.parse_post(
            board_ingest._read(os.path.join(board_ingest.POSTS, action_id + ".md"))
        )
        assert meta["from"] == "UNSEATED" and meta["act"] == "WIBBLE"
        assert body == action_body

        # Ordinary posting is equally open without memory or capability fields.
        ordinary_id = "ordinary-speech-open-20260823-01"
        assert board_ingest.write_post(
            "BRYCE", "TABLE", ordinary_id, "the file is inert", extra={}
        ) == "wrote"
        assert os.path.isfile(os.path.join(board_ingest.POSTS, ordinary_id + ".md"))

        # The canonical writer preserves the exact payload, including local
        # paths, instead of treating a path as a permission/privacy gate.
        path_id = "literal-local-path-open-20260823-01"
        literal = r"run C:\Users\someone\Desktop\job.ps1 exactly"
        assert board_ingest.write_post("", "TABLE", path_id, literal, extra={}) == "wrote"
        _meta, kept = board_ingest.parse_post(
            board_ingest._read(os.path.join(board_ingest.POSTS, path_id + ".md"))
        )
        assert kept == literal, kept

        source = board_ingest._read(os.path.join(os.path.dirname(__file__), "board_ingest.py"))
        assert "tos_gate.reject_reason" not in source
        assert 'return "capability-declaration"' not in source
        assert "MEMORY_GATE" not in source
        for deleted in ("tos_gate.py", "test_tos_gate.py", "tos_bans.json", "appeals.json", "ground/TOS.md"):
            assert not os.path.exists(os.path.join(os.path.dirname(__file__), deleted))
        print("ok   test_action_pad_zero_auth.py")
        return 0
    finally:
        board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO = saved
        memory_board.clear_cache(tmp)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
