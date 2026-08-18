#!/usr/bin/env python3
# INQUISITOR order 016 point 3: ingest the identical retained ntfy corpus twice;
# the second pass must produce zero filesystem diff and zero new conflict rows.
# Runs against a sandbox tree so the live record is never touched.
import hashlib
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest


def snapshot(root):
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            p = os.path.join(dirpath, name)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root)] = hashlib.sha256(f.read()).hexdigest()
    return out


def main():
    tmp = tempfile.mkdtemp(prefix="commons-dedupe-test-")
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        os.makedirs(board_ingest.POSTS, exist_ok=True)

        # corpus: one post lands, then the same id arrives with a different body
        # (same ntfy event id + transport ts every re-read, like the 72h window)
        ts = "2026-08-18T12:00:00Z"
        extra = {"carrier_ts": ts, "durable_ts": ts}

        st = board_ingest.write_post("W1", "TABLE", "test-post-0001", "body one", ts, dict(extra))
        assert st == "wrote", st

        st = board_ingest.write_post("W1", "TABLE", "test-post-0001", "body two", ts, dict(extra), event_id="evA")
        assert st == "conflict", st
        cpath = os.path.join(tmp, "conflicts", "test-post-0001.jsonl")
        rows = [json.loads(x) for x in open(cpath) if x.strip()]
        assert len(rows) == 1 and rows[0]["key"] and rows[0]["event_id"] == "evA", rows

        # second pass over the identical retained corpus (fresh durable_ts, as real
        # ingest stamps): landed copy -> exists, conflict copy -> conflict-seen,
        # and the tree is byte-identical.
        before = snapshot(tmp)
        extra2 = {"carrier_ts": ts, "durable_ts": "2026-08-18T13:00:00Z"}
        st = board_ingest.write_post("W1", "TABLE", "test-post-0001", "body one", ts, dict(extra2))
        assert st == "exists", st
        st = board_ingest.write_post("W1", "TABLE", "test-post-0001", "body two", ts, dict(extra2), event_id="evA")
        assert st == "conflict-seen", st
        after = snapshot(tmp)
        assert before == after, "second pass changed the filesystem"
        rows = [json.loads(x) for x in open(cpath) if x.strip()]
        assert len(rows) == 1, "second pass appended a conflict row"

        # a genuinely NEW conflict (different body, different event) still records
        st = board_ingest.write_post("W1", "TABLE", "test-post-0001", "body three", ts, dict(extra2), event_id="evB")
        assert st == "conflict", st
        rows = [json.loads(x) for x in open(cpath) if x.strip()]
        assert len(rows) == 2, rows

        # legacy rows (no key field) dedupe by recomputed key: strip the key from
        # row 1 on disk, re-offer the same evA conflict, expect conflict-seen
        legacy = []
        for r in rows:
            r = dict(r)
            r.pop("key", None)
            legacy.append(json.dumps(r, ensure_ascii=True))
        with open(cpath, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(legacy) + "\n")
        st = board_ingest.write_post("W1", "TABLE", "test-post-0001", "body two", ts, dict(extra2), event_id="evA")
        assert st == "conflict-seen", st

        print("CONFLICT DEDUPE TEST: ALL PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
