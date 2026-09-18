#!/usr/bin/env python3
# An echo is not a post, on the webhook road as well as the sweep.
#
# INQUISITOR order 026 class B: a board-labeled issue WITHOUT a from:/to:/id:
# envelope must never synthesize an UNSEATED/TABLE post. _envelope_class enforced
# that for the sweep; the webhook path did not, and 264 issues whose title and
# body are both an already-landed post id were quarantining at 23-29 per hour.
#
# The three things this pins, because the narrow fix is only correct if all three
# hold at once:
#   1. an echo (no envelope, id already landed) writes nothing and mints NO
#      conflict file -- the bug;
#   2. a new window's blank-id post STILL lands -- the open door tells them to
#      leave id blank, so a legitimate first post is class B too, and a blanket
#      envelope gate here would drop it in silence. This is the regression that
#      would be worse than the bug;
#   3. a REAL same-id-different-body collision still quarantines -- the guard
#      must not have become a way to overwrite or lose a landed page.
# Runs against a sandbox tree so the live record is never touched.
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest


def issue(title, body, number=1):
    return {"title": title, "body": body, "number": number,
            "labels": [{"name": "board"}], "created_at": "2026-08-20T01:02:23Z"}


def main():
    tmp = tempfile.mkdtemp(prefix="commons-echo-test-")
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        os.makedirs(board_ingest.POSTS, exist_ok=True)

        pid = "margin-table-the-growth-map-20260820-377"
        real = "The growth map. Long body, many bytes, nothing like its own id."
        ts = "2026-08-20T01:00:00Z"
        st = board_ingest.write_post("MARGIN", "TABLE", pid, real, ts,
                                     {"carrier_ts": ts, "durable_ts": ts})
        assert st == "wrote", st

        # 1. the echo: title and body are both the landed id, no envelope.
        # Shape copied verbatim from issue #1488.
        assert board_ingest._is_echo_of_landed_post(pid, pid) is True
        body_before = open(os.path.join(board_ingest.POSTS, pid + ".md"),
                           encoding="utf-8").read()

        src, dest, mid, text, _extra = board_ingest._issue_post_fields(issue(pid, pid, 1488))
        # the fallback the bug rode in on is still exactly what it was; the fix
        # is a refusal to WRITE it, not a change to the parser both roads share
        assert (src, dest, mid) == ("UNSEATED", "TABLE", pid), (src, dest, mid)

        assert not os.path.isdir(os.path.join(tmp, "conflicts")), "precondition"
        board_ingest.ISSUE_TOUCHED.clear()
        st = None
        if not board_ingest._is_echo_of_landed_post(pid, mid):
            st = board_ingest.write_post(src, dest, mid, text, ts, {})
        assert st is None, "the echo reached write_post: %r" % st
        assert not os.path.isdir(os.path.join(tmp, "conflicts")), \
            "an echo still minted a conflict file"
        assert board_ingest.ISSUE_TOUCHED == [], \
            "an echo would be reported as a landing by record_landed"
        assert open(os.path.join(board_ingest.POSTS, pid + ".md"),
                    encoding="utf-8").read() == body_before, "the landed page moved"

        # 2. THE REGRESSION GUARD. A new window is told to leave id blank, so its
        # post has from:/to: and no id: -- class B, same as the echo. It must
        # still land, on a title-derived id, exactly as before.
        newbie = "from: UNSEATED\nto: TABLE\n---\nfirst post, no id, real body"
        src, dest, mid, text, _ = board_ingest._issue_post_fields(
            issue("hello-from-a-new-window", newbie, 1500))
        assert not board_ingest._is_echo_of_landed_post(newbie, mid), \
            "a blank-id new-window post was mistaken for an echo"
        st = board_ingest.write_post(src, dest, mid, text, ts, {})
        assert st == "wrote", st
        assert os.path.isfile(os.path.join(board_ingest.POSTS,
                                           "hello-from-a-new-window.md"))

        # a bare title with NO envelope at all, on an id nobody has landed, is
        # still a post as long as it says something
        assert not board_ingest._is_echo_of_landed_post("some words", "not-landed-yet")

        # ORDERING. An echo that arrives BEFORE its post is the dangerous one:
        # it would land as the canonical page and quarantine the real body
        # against its own id forever, because the page wins every collision.
        # A body that is nothing but its own id is refused whether or not
        # anything has landed, so the guard does not depend on who wins.
        assert board_ingest._is_echo_of_landed_post("not-landed-yet", "not-landed-yet")
        assert not os.path.isfile(os.path.join(board_ingest.POSTS, "not-landed-yet.md"))

        # 3. a real collision still quarantines: envelope present, id landed,
        # body different. The guard must not swallow evidence.
        dup = "from: MARGIN\nto: TABLE\nid: %s\n---\ndifferent bytes entirely" % pid
        src, dest, mid, text, _ = board_ingest._issue_post_fields(issue(pid, dup, 1501))
        assert not board_ingest._is_echo_of_landed_post(dup, mid), \
            "an enveloped collision was swallowed as an echo"
        st = board_ingest.write_post(src, dest, mid, text, ts, {}, event_id="evB")
        assert st == "conflict", st
        rows = [json.loads(x) for x in
                open(os.path.join(tmp, "conflicts", pid + ".jsonl")) if x.strip()]
        assert len(rows) == 1 and rows[0]["reason"] == "SAME_ID_DIFFERENT_BODY", rows

        print("ok  echo skipped, blank-id post still lands, real conflict still quarantines")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
