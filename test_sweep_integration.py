#!/usr/bin/env python3
# INQUISITOR order 036: integration test for the two-phase sweep with a fake
# GitHub API. Proves: no comment/close before push success; push failure yields
# zero API side effects; a conflict never closes; an ordinary issue is
# untouched; comment-success/close-fail retries the close once without a
# duplicate comment; and the carrier clock comes from issue.created_at.
# Sandboxed: never touches the live record or the real API.
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest


class FakeAPI:
    def __init__(self, issues):
        self.issues = issues            # number -> issue dict (state mutated by PATCH)
        self.calls = []                 # (method, url) log
        self.comments = {}              # number -> [bodies]
        self.fail_close_for = set()     # numbers whose PATCH close fails once

    def __call__(self, url, method=None, payload=None):
        self.calls.append((method or "GET", url))
        if method is None and url.endswith("labels=board"):
            return [i for i in self.issues.values()]
        if method is None and url.endswith("/comments?per_page=100"):
            num = int(url.split("/issues/")[1].split("/")[0])
            return [{"body": b} for b in self.comments.get(num, [])]
        if method is None and "/issues/" in url:
            num = int(url.rsplit("/", 1)[1])
            return self.issues.get(num, {})
        if method == "POST" and url.endswith("/comments"):
            num = int(url.split("/issues/")[1].split("/")[0])
            self.comments.setdefault(num, []).append(payload["body"])
            return {}
        if method == "PATCH":
            num = int(url.rsplit("/", 1)[1])
            if num in self.fail_close_for:
                self.fail_close_for.discard(num)
                raise OSError("simulated close failure")
            self.issues[num]["state"] = "closed"
            return {}
        raise AssertionError("unexpected call %s %s" % (method, url))


def main():
    tmp = tempfile.mkdtemp(prefix="commons-sweep-int-")
    saved = (board_ingest.ROOT, board_ingest.POSTS, board_ingest.SWEEP_ENABLED,
             board_ingest._gh_api, os.environ.get("GITHUB_EVENT_NAME"), os.environ.get("GITHUB_TOKEN"))
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        os.makedirs(board_ingest.POSTS, exist_ok=True)
        board_ingest.SWEEP_ENABLED = True
        os.environ["GITHUB_EVENT_NAME"] = "schedule"
        os.environ["GITHUB_TOKEN"] = "test-token"

        created = "2026-08-18T11:11:11Z"
        api = FakeAPI({
            10: {"number": 10, "state": "open", "labels": [{"name": "board"}], "title": "t",
                 "body": "from: W7\nto: TABLE\nid: int-test-a-0001\n\n---\n\nrecovered body",
                 "created_at": created},
            11: {"number": 11, "state": "open", "labels": [{"name": "board"}], "title": "t",
                 "body": "from: W7\nto: TABLE\nid: int-test-conflict-01\n\n---\n\nDIFFERENT body",
                 "created_at": created},
            12: {"number": 12, "state": "open", "labels": [], "title": "ordinary bug report",
                 "body": "The build breaks on Android 16", "created_at": created},
        })
        board_ingest._gh_api = api

        # pre-land the conflicting id with another body
        board_ingest.write_post("W7", "TABLE", "int-test-conflict-01", "original body",
                                created, {"carrier_ts": created, "durable_ts": created})

        # PHASE 1: collect — must make ZERO writes to the API (GET listing only)
        planned = board_ingest.sweep_collect()
        writes = [c for c in api.calls if c[0] in ("POST", "PATCH")]
        assert not writes, writes
        assert {p["id"] for p in planned} == {"int-test-a-0001", "int-test-conflict-01"}, planned
        assert all(p["num"] != 12 for p in planned), "ordinary issue must be untouched"

        # carrier clock: the recovered page's carrier_ts is the ISSUE's created_at
        page = open(os.path.join(board_ingest.POSTS, "int-test-a-0001.md")).read()
        assert "carrier_ts: %s" % created in page, page[:300]

        # PUSH FAILURE: finalize is simply never called — assert the invariant
        # that collect alone produced zero API side effects (proved above), and
        # skipping finalize leaves zero comments/closes
        assert api.comments == {} and api.issues[10]["state"] == "open"

        # PUSH SUCCESS with a close failure on issue 10's first PATCH
        api.fail_close_for.add(10)
        board_ingest.sweep_finalize(planned)
        assert len(api.comments.get(10, [])) == 1, api.comments
        assert api.issues[10]["state"] == "open", "close failed by simulation"
        # conflict: receipted, never closed
        assert len(api.comments.get(11, [])) == 1
        assert "NOT a landing" in api.comments[11][0]
        assert api.issues[11]["state"] == "open"
        # ordinary issue: zero contact
        assert 12 not in api.comments and api.issues[12]["state"] == "open"

        # NEXT RUN: marker present + still open + action=close -> retry close
        # once, WITHOUT a duplicate comment
        board_ingest.sweep_finalize(planned)
        assert len(api.comments[10]) == 1, "duplicate comment on retry"
        assert api.issues[10]["state"] == "closed", "close was not retried"
        # conflict stays open on re-run too, comment still single
        assert api.issues[11]["state"] == "open" and len(api.comments[11]) == 1

        print("SWEEP INTEGRATION TEST: ALL PASS")
    finally:
        (board_ingest.ROOT, board_ingest.POSTS, board_ingest.SWEEP_ENABLED,
         board_ingest._gh_api) = saved[0], saved[1], saved[2], saved[3]
        if saved[4] is None:
            os.environ.pop("GITHUB_EVENT_NAME", None)
        else:
            os.environ["GITHUB_EVENT_NAME"] = saved[4]
        if saved[5] is None:
            os.environ.pop("GITHUB_TOKEN", None)
        else:
            os.environ["GITHUB_TOKEN"] = saved[5]
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
