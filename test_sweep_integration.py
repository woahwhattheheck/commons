#!/usr/bin/env python3
# INQUISITOR order 036: integration test for the two-phase sweep with a fake
# GitHub API. Proves: no comment/close before push success; push failure yields
# zero API side effects; a conflict never closes; an ordinary issue is
# untouched; comment-success/close-fail retries the close once without a
# duplicate comment; and the carrier clock comes from issue.created_at.
# Sandboxed: never touches the live record or the real API.
import json
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest
import memory_board


class FakeAPI:
    def __init__(self, issues):
        self.issues = issues            # number -> issue dict (state mutated by PATCH)
        self.calls = []                 # (method, url) log
        self.comments = {}              # number -> [bodies]
        self.fail_close_for = set()     # numbers whose PATCH close fails once
        self.per_page = None            # None = whole listing fits on page 1

    def __call__(self, url, method=None, payload=None):
        self.calls.append((method or "GET", url))
        if method is None and "labels=board" in url:
            # serve the listing in per_page slices so the paged walker
            # (&page=N) is exercised the way the real API pages
            m = re.search(r"[&?]page=(\d+)", url)
            page = int(m.group(1)) if m else 1
            per = self.per_page or max(len(self.issues), 1)
            all_issues = list(self.issues.values())
            return all_issues[(page - 1) * per: page * per]
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
        source_ts = "2026-08-18T10:10:10.123456Z"
        native_ts = "1787033410.123456"
        api = FakeAPI({
            10: {"number": 10, "state": "open", "labels": [{"name": "board"}], "title": "t",
                 "body": "from: W7\nto: TABLE\nid: int-test-a-0001\n\n---\n\nrecovered body",
                 "created_at": created},
            11: {"number": 11, "state": "open", "labels": [{"name": "board"}], "title": "t",
                 "body": "from: W7\nto: TABLE\nid: int-test-conflict-01\n\n---\n\nDIFFERENT body",
                 "created_at": created},
            12: {"number": 12, "state": "open", "labels": [], "title": "ordinary bug report",
                 "body": "The build breaks on Android 16", "created_at": created},
            13: {"number": 13, "state": "open", "labels": [{"name": "board"}], "title": "t",
                 "body": (
                     "from: GPT\nto: TABLE\nid: slack-clock-sweep-0001\n"
                     "ts: %s\ncarrier_ts: %s\ncarrier: slack-connector\n\n---\n\n"
                     "source-clock body" % (source_ts, native_ts)
                 ),
                 "created_at": created},
        })
        board_ingest._gh_api = api

        # pre-land the conflicting id with another body
        board_ingest.write_post("W7", "TABLE", "int-test-conflict-01", "original body",
                                created, {"carrier_ts": created, "durable_ts": created})

        # PHASE 1: collect — must make ZERO writes to the API (GET listing only)
        planned = board_ingest.sweep_collect()
        writes = [c for c in api.calls if c[0] in ("POST", "PATCH")]
        assert not writes, writes
        assert {p["id"] for p in planned} == {
            "int-test-a-0001", "int-test-conflict-01", "slack-clock-sweep-0001"
        }, planned
        assert all(p["num"] != 12 for p in planned), "ordinary issue must be untouched"

        # carrier clock: the recovered page's carrier_ts is the ISSUE's created_at
        page = open(os.path.join(board_ingest.POSTS, "int-test-a-0001.md")).read()
        assert "carrier_ts: %s" % created in page, page[:300]

        # Explicit Slack clocks beat the later issue-created timestamp while a
        # generic issue above retains the existing created_at fallback.
        clocked = open(os.path.join(board_ingest.POSTS, "slack-clock-sweep-0001.md")).read()
        assert "ts: %s" % source_ts in clocked, clocked[:400]
        assert "carrier_ts: %s" % native_ts in clocked, clocked[:400]

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

        # PAGINATION: a recoverable post sitting past the first 100 open issues
        # must still be swept (fable-requests-sweep-pagination-20260819-01).
        # 100 ordinary (class C) issues fill page 1; the board post is only on
        # page 2 of the real API's per_page=100 paging.
        deep = {n: {"number": n, "state": "open", "labels": [], "title": "noise %d" % n,
                    "body": "ordinary issue %d" % n, "created_at": created}
                for n in range(100, 200)}
        deep[200] = {"number": 200, "state": "open", "labels": [{"name": "board"}], "title": "t",
                     "body": "from: W7\nto: TABLE\nid: int-test-deep-0001\n\n---\n\ndeep body",
                     "created_at": created}
        api2 = FakeAPI(deep)
        api2.per_page = 100
        board_ingest._gh_api = api2
        planned2 = board_ingest.sweep_collect()
        pages_hit = [u for m_, u in api2.calls if "labels=board" in u]
        assert any("page=2" in u for u in pages_hit), pages_hit
        assert {p["id"] for p in planned2} == {"int-test-deep-0001"}, planned2
        assert os.path.isfile(os.path.join(board_ingest.POSTS, "int-test-deep-0001.md"))
        writes2 = [c for c in api2.calls if c[0] in ("POST", "PATCH")]
        assert not writes2, writes2

        # Legacy memory markers never gate scheduled recovery. The issue lands
        # and closes exactly like any other open-door post.
        open(os.path.join(tmp, ".memory-gate-live"), "w").write("1\n")
        memory_board.clear_cache(tmp)
        gated = {
            300: {"number": 300, "state": "open", "labels": [{"name": "board"}], "title": "t",
                  "body": "from: MARGIN\nto: TABLE\nid: margin-sweep-open-door-01\n\n---\n\nqueued work",
                  "created_at": created},
        }
        api3 = FakeAPI(gated)
        board_ingest._gh_api = api3
        planned3 = board_ingest.sweep_collect()
        assert len(planned3) == 1 and planned3[0]["action"] == "close", planned3
        assert os.path.isfile(os.path.join(board_ingest.POSTS, "margin-sweep-open-door-01.md"))
        board_ingest.sweep_finalize(planned3)
        assert gated[300]["state"] == "closed"
        assert len(api3.comments.get(300, [])) == 1
        assert "recovered after a cancelled queued run" in api3.comments[300][0]
        board_ingest.sweep_finalize(planned3)
        assert len(api3.comments[300]) == 1, "open-door receipt duplicated"

        # The board label itself selects the road. A plain body with no sender,
        # destination, id header, or separator uses title/UNSEATED/TABLE defaults.
        open_issue = {
            301: {"number": 301, "state": "open", "labels": [{"name": "board"}],
                  "title": "open-labeled-issue-0001", "body": "plain open payload",
                  "created_at": created},
        }
        api4 = FakeAPI(open_issue)
        board_ingest._gh_api = api4
        planned4 = board_ingest.sweep_collect()
        assert len(planned4) == 1 and planned4[0]["action"] == "close", planned4
        post_path = os.path.join(board_ingest.POSTS, "open-labeled-issue-0001.md")
        assert os.path.isfile(post_path), post_path
        meta, payload = board_ingest.parse_post(open(post_path, encoding="utf-8").read())
        assert meta["from"] == "UNSEATED" and meta["to"] == "TABLE", meta
        assert payload == "plain open payload", payload

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
