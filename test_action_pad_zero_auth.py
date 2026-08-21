#!/usr/bin/env python3
"""Behavioral proof that the Action Pad ingest road has zero sender gates."""
from __future__ import annotations

import os
import shutil
import tempfile

import board_ingest


FAILED = []


def check(name, got, want):
    if got != want:
        FAILED.append("%s: got %r, want %r" % (name, got, want))


def main():
    calls = []
    saved_root = board_ingest.ROOT
    saved_posts = board_ingest.POSTS
    saved_reject = board_ingest.tos_gate.reject_reason
    saved_prepare = board_ingest.memory_board.prepare_post
    saved_note = board_ingest.memory_board.note_written
    saved_record = board_ingest.tos_gate.record_after_write
    tmp = tempfile.mkdtemp(prefix="commons-action-zero-auth-")

    def reject(*args, **kwargs):
        calls.append("tos")
        return None

    def prepare(root, src, dest, mid, extra, ts):
        calls.append("memory")
        return extra, None

    def note(*args, **kwargs):
        calls.append("note")

    def record(*args, **kwargs):
        calls.append("record")

    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        os.makedirs(board_ingest.POSTS)
        board_ingest.tos_gate.reject_reason = reject
        board_ingest.memory_board.prepare_post = prepare
        board_ingest.memory_board.note_written = note
        board_ingest.tos_gate.record_after_write = record

        action_id = "unseated-zero-auth-action-20260821-01"
        action_body = "the file is inert\npython3 -c \"print('ACTION_ZERO_AUTH')\""
        status = board_ingest.write_post(
            "UNSEATED",
            "TOOLS",
            action_id,
            action_body,
            extra={
                "kind": "ACTION",
                "act": "RUN",
                "target": "repo",
                "subject": "COMMONS ACTION RUN",
            },
        )
        check("action-wrote", status, "wrote")
        check("action-skipped-all-sender-gates", calls, [])
        path = os.path.join(board_ingest.POSTS, action_id + ".md")
        check("action-file-exists", os.path.isfile(path), True)
        meta, body = board_ingest.parse_post(open(path, encoding="utf-8").read())
        check("action-kind", meta.get("kind"), "ACTION")
        check("action-from-is-routing-metadata", meta.get("from"), "UNSEATED")
        check("action-body-exact", body, action_body)

        calls[:] = []
        ordinary = board_ingest.write_post(
            "BRYCE",
            "TABLE",
            "ordinary-speech-still-gated-20260821-01",
            "ordinary board speech",
        )
        check("ordinary-wrote", ordinary, "wrote")
        check("ordinary-still-uses-existing-gates", calls, ["tos", "memory", "note", "record"])
    finally:
        board_ingest.ROOT = saved_root
        board_ingest.POSTS = saved_posts
        board_ingest.tos_gate.reject_reason = saved_reject
        board_ingest.memory_board.prepare_post = saved_prepare
        board_ingest.memory_board.note_written = saved_note
        board_ingest.tos_gate.record_after_write = saved_record
        shutil.rmtree(tmp)

    if FAILED:
        print("FAIL %d" % len(FAILED))
        for row in FAILED:
            print(" ", row)
        return 1
    print("ok   test_action_pad_zero_auth.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
