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

        # TRUE legacy rows (order 027): neither key NOR event_id on disk, while
        # the resend of the same event now carries an event id — semantic
        # fallback must still return conflict-seen
        legacy = []
        for r in rows:
            r = dict(r)
            r.pop("key", None)
            r.pop("event_id", None)
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


def test_sweep_boundary():
    # INQUISITOR order 026 A/B/C gate: unlabeled exact envelope is eligible (A);
    # board-labeled without envelope is class B (close only if page exists,
    # never synthesize); everything else untouched (C).
    unlabeled_envelope = {
        "number": 1, "labels": [],
        "body": "from: W9\nto: TABLE\nid: sweep-test-0001\n\n---\n\nbody",
    }
    labeled_envelope = {
        "number": 2, "labels": [{"name": "board"}],
        "body": "from: W9\nto: TABLE\nid: sweep-test-0002\n\n---\n\nbody",
    }
    labeled_id_only = {
        "number": 3, "labels": [{"name": "board"}],
        "title": "some-landed-id-20260818-01",
        "body": "just words, no headers, no separator",
    }
    plain_issue = {
        "number": 4, "labels": [],
        "body": "The build breaks on Android 16, please fix",
    }
    assert board_ingest._envelope_class(unlabeled_envelope) == "A"
    assert board_ingest._envelope_class(labeled_envelope) == "A"
    assert board_ingest._envelope_class(labeled_id_only) == "A"
    assert board_ingest._envelope_class(plain_issue) == "C"
    print("SWEEP BOUNDARY TEST (026 A/B/C): ALL PASS")


if "test_sweep_boundary" in dir():
    test_sweep_boundary()
