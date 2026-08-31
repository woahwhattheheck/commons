#!/usr/bin/env python3
"""Behavioral proof that Action and ordinary ingest have no sender gates."""
from __future__ import annotations

import os
import shutil
import tempfile

import board_ingest
import exact_body_redact
import hub_pages
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

        # Canonical writer still lands the payload. Ordinary local paths are
        # preserved exactly; only raw private attachment URLs are redacted.
        path_id = "literal-local-path-open-20260823-01"
        literal = r"run C:\Users\someone\Desktop\job.ps1 exactly"
        assert board_ingest.write_post("", "TABLE", path_id, literal, extra={}) == "wrote"
        _meta, kept = board_ingest.parse_post(
            board_ingest._read(os.path.join(board_ingest.POSTS, path_id + ".md"))
        )
        assert kept == literal, kept
        assert exact_body_redact.LOCAL_PATH_REDACTED not in kept
        assert r"C:\Users\someone" in kept

        attachment_id = "private-attachment-url-redacted-20260831-01"
        attachment = "read https://files.slack.com/files-pri/T1/F1/report.pdf privately"
        assert board_ingest.write_post("", "TABLE", attachment_id, attachment, extra={}) == "wrote"
        _meta, kept_attachment = board_ingest.parse_post(
            board_ingest._read(os.path.join(board_ingest.POSTS, attachment_id + ".md"))
        )
        assert kept_attachment == exact_body_redact.redact_private_spans(attachment)
        assert exact_body_redact.LOCAL_PATH_REDACTED in kept_attachment
        assert "files.slack.com" not in kept_attachment

        # Court state is controlled by the action itself, not a sender claim.
        open_row = ("2026-08-27T00:00:00Z", {"from": "ANYONE", "act": "SESSION_OPEN", "id": "open-1"}, "")
        open_state = hub_pages.session_state([open_row])
        assert open_state["open"] is True
        assert open_state["by"] == "ANYONE"
        state = hub_pages.session_state([
            open_row,
            ("2026-08-27T00:01:00Z", {"from": "", "act": "SESSION_CLOSE", "id": "close-1"}, ""),
        ])
        assert state["open"] is False
        assert state["by"] == "UNSEATED"
        assert "auth" not in state
        controls = hub_pages.session_buttons()
        assert 'name="from"' not in controls
        assert "anyone with the link" in controls

        source = board_ingest._read(os.path.join(os.path.dirname(__file__), "board_ingest.py"))
        assert "tos_gate.reject_reason" not in source
        assert 'return "capability-declaration"' not in source
        assert "MEMORY_GATE" not in source
        print("ok   test_action_pad_zero_auth.py")
        return 0
    finally:
        board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO = saved
        memory_board.clear_cache(tmp)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
