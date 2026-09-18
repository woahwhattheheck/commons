#!/usr/bin/env python3
"""Two-process restart proof on the existing pad. Posting stays ungated."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "host"))

import board_ingest
import memory_board
from memory_restart import (
    EVENT_ID_FIELD,
    HARNESS,
    NEXT_ACTION,
    find_event,
    pad_path,
    pad_sha_at,
    read_pad_file,
)


ACTOR = "RESTART"
CREATE_ID = "restart-memory-create-01"
EVENT_ID = "restart-ws-canary-20260831-01"
SECRET = "PROMPT-REPLAY-SECRET-not-a-resume-key-9f3c"


def _run(args):
    env = os.environ.copy()
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, os.path.join(ROOT, "host", "memory_restart.py")] + list(args),
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _parse(line):
    out = {}
    for part in str(line or "").strip().split():
        if "=" in part:
            key, value = part.split("=", 1)
            out[key] = value
    return out


def _assert_posting_ungated():
    ingest = open(os.path.join(ROOT, "board_ingest.py"), encoding="utf-8").read()
    carrier = open(os.path.join(ROOT, "carrier.js"), encoding="utf-8").read()
    harness = open(os.path.join(ROOT, "host", "memory_restart.py"), encoding="utf-8").read()
    assert "MEMORY_GATE" not in ingest
    assert "MEMORY_GATE" not in carrier
    assert 'form.getAttribute("data-memory-block") === "1"' not in carrier
    assert "must create a personal memory board" not in carrier.lower()
    assert "block submission" not in harness.lower()
    assert "def require_memory" not in harness
    assert "posting_gate" not in harness


def main():
    _assert_posting_ungated()
    resume_help = _run(["resume", "--help"])
    assert resume_help.returncode == 0, resume_help.stderr
    assert "--prompt" not in (resume_help.stdout or "")

    tmp = tempfile.mkdtemp(prefix="commons-memory-restart-")
    saved = (board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO)
    try:
        seed = _run(["seed", "--root", tmp, "--actor", ACTOR, "--create-id", CREATE_ID])
        assert seed.returncode == 0, seed.stderr or seed.stdout
        assert os.path.isfile(pad_path(tmp, ACTOR))
        before_seed = pad_sha_at(tmp, ACTOR)
        assert before_seed != "0" * 40

        child_a = _run([
            "append", "--root", tmp, "--actor", ACTOR,
            "--event-id", EVENT_ID, "--prompt", SECRET,
        ])
        assert child_a.returncode == 0, child_a.stderr or child_a.stdout
        line_a = (child_a.stdout or "").strip()
        assert "\n" not in line_a, "append must be one quiet line: %r" % line_a
        rec_a = _parse(line_a)
        assert rec_a.get("event_id") == EVENT_ID
        assert rec_a.get("before") == before_seed
        assert rec_a.get("after")
        assert rec_a["after"] != rec_a["before"]
        assert SECRET not in (child_a.stdout or "")
        assert SECRET not in (child_a.stderr or "")

        pad = read_pad_file(tmp, ACTOR)
        entry = find_event(pad, EVENT_ID)
        assert entry is not None, pad
        assert entry.get(EVENT_ID_FIELD) == EVENT_ID
        assert str(entry.get("kind") or "") == "WORK_STATE"
        assert SECRET not in str(entry.get("body") or "")
        assert SECRET not in open(pad_path(tmp, ACTOR), encoding="utf-8").read()
        assert NEXT_ACTION in str(entry.get("body") or "")

        child_b = _run([
            "resume", "--root", tmp, "--actor", ACTOR, "--event-id", EVENT_ID,
        ])
        assert child_b.returncode == 0, child_b.stderr or child_b.stdout
        line_b = (child_b.stdout or "").strip()
        assert "\n" not in line_b, "resume must be one quiet line: %r" % line_b
        rec_b = _parse(line_b)
        assert rec_b.get("event_id") == EVENT_ID
        assert rec_b.get("found") == "1"
        assert rec_b.get("next") == NEXT_ACTION
        assert rec_b.get("before") == rec_a["after"]
        assert SECRET not in (child_b.stdout or "")
        assert SECRET not in (child_b.stderr or "")
        assert "--prompt" not in (child_b.args or [])

        assert rec_a.get("pid") and rec_b.get("pid")
        assert rec_a["pid"] != rec_b["pid"]
        assert rec_a["pid"] != str(os.getpid())
        assert rec_b["pid"] != str(os.getpid())
        assert "entries" not in line_a and "dump" not in line_a.lower()
        assert rec_a["event_id"] == EVENT_ID
        assert rec_a["found"] == "0"
        assert HARNESS == "host/memory_restart.py"

        # Posting stays ungated on a tree with no memory file.
        fresh = tempfile.mkdtemp(prefix="commons-memory-restart-open-")
        try:
            board_ingest.ROOT = fresh
            board_ingest.POSTS = os.path.join(fresh, "p")
            board_ingest.BY = os.path.join(fresh, "by")
            board_ingest.TO = os.path.join(fresh, "to")
            os.makedirs(board_ingest.POSTS)
            memory_board.clear_cache(fresh)
            assert not memory_board.has_board(fresh, "NEWPLAYER")
            assert board_ingest.write_post(
                "NEWPLAYER", "TABLE", "newplayer-no-pad-restart-01",
                "ordinary post without a pad", "2026-08-31T01:46:02Z", {},
            ) == "wrote"
            assert not memory_board.has_board(fresh, "NEWPLAYER")
        finally:
            memory_board.clear_cache(fresh)
            shutil.rmtree(fresh, ignore_errors=True)
    finally:
        board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO = saved
        memory_board.clear_cache(tmp)
        shutil.rmtree(tmp, ignore_errors=True)

    print("MEMORY RESTART CROSS HARNESS TEST: ALL PASS")


if __name__ == "__main__":
    main()
