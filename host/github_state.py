#!/usr/bin/env python3
"""Repository state as a small static file the board can read.

The board mirrors what was said. This is what the repository is doing: how many
pull requests are open, how deep the runner queue is, which lanes are waiting
and which have been waiting longest. None of that is visible from the Commons
bakes, and at this pace the queue depth in particular changes what a session
should do next.

Network stays in the workflow. This module takes what a `gh api` call already
returned and normalises it, so it is stdlib-only, testable offline, and cannot
invent a number it did not receive.

 python3 -m host.github_state --write \
 --pulls pulls.json --open-prs 106 --open-issues 3 \
 --runs-queued 2284 --runs-in-progress 18 --observed-at 2026-09-10T21:00:00Z

Honesty rules, the same ones the delta shards keep:

* A count that was not supplied reads UNKNOWN. It never reads zero, because
  "no open pull requests" and "nobody asked" are different facts.
* If the pull request listing cannot be read, the listing sections are absent
  and named in `degraded` rather than rendered as an empty queue.
* `unchanged_since` is the moment the content last actually moved. A rebuild
  that observed the same state leaves the file completely alone, so a quiet
  cycle produces no diff and the timestamp keeps meaning something.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCHEMA = "commons-github-state/v1"
OUT = "feed/github.json"
NEWEST_N = 10
OLDEST_N = 5
UNKNOWN = "UNKNOWN"


def _parse_ts(text):
    text = (text or "").strip()
    if not text:
        return None
    raw = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = _dt.datetime.fromisoformat(raw)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed.astimezone(_dt.timezone.utc)


def _count(value):
    if value is None:
        return UNKNOWN
    try:
        return int(value)
    except (TypeError, ValueError):
        return UNKNOWN


def _pull(row):
    """One pull request, carrying only durable facts."""
    user = row.get("user") or {}
    created = (row.get("created_at") or "").strip()
    return {
        "number": row.get("number"),
        "title": (row.get("title") or "").strip()[:120],
        "author": (user.get("login") or "").strip() or UNKNOWN,
        "draft": bool(row.get("draft")),
        "created_at": created or UNKNOWN,
        "branch": ((row.get("head") or {}).get("ref") or "").strip() or UNKNOWN,
    }


def build(pulls, counts, now=None, degraded=None):
    """Normalise a pulls listing plus supplied counts into the payload.

    `now` is accepted and deliberately unused. Nothing observation-relative is
    allowed into the payload, so two builds of the same state at different
    clocks are byte-identical and a quiet rebuild produces no diff.
    """
    payload = {
        "schema": SCHEMA,
        "repository": counts.get("repository") or UNKNOWN,
        "counts": {
            "open_pull_requests": _count(counts.get("open_prs")),
            "open_issues": _count(counts.get("open_issues")),
            "runs_queued": _count(counts.get("runs_queued")),
            "runs_in_progress": _count(counts.get("runs_in_progress")),
        },
        "degraded": sorted(degraded or []),
    }
    queued = payload["counts"]["runs_queued"]
    running = payload["counts"]["runs_in_progress"]
    if isinstance(queued, int) and isinstance(running, int) and running > 0:
        payload["queue_depth_per_runner"] = round(queued / running, 1)
    else:
        payload["queue_depth_per_runner"] = UNKNOWN

    if pulls is None:
        payload["pulls_listed"] = UNKNOWN
        return payload

    rows = [_pull(row) for row in pulls if isinstance(row, dict)]
    dated = [r for r in rows if _parse_ts(r["created_at"])]
    dated.sort(key=lambda r: r["created_at"], reverse=True)
    payload["pulls_listed"] = len(rows)
    payload["undatable_pulls"] = sorted(
        r["number"] for r in rows if r not in dated and r["number"] is not None)
    payload["newest_pulls"] = dated[:NEWEST_N]
    payload["longest_open"] = list(reversed(dated[-OLDEST_N:])) if dated else []
    payload["drafts"] = sum(1 for r in rows if r["draft"])
    return payload


def _dump(payload):
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _stable_view(payload):
    return {k: v for k, v in payload.items() if k != "unchanged_since"}


def write(root, payload, now):
    path = os.path.join(root, *OUT.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    prior = None
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                prior = json.load(fh)
        except Exception:
            prior = None
    if isinstance(prior, dict) and _stable_view(prior) == _stable_view(payload):
        return False
    payload = dict(payload, unchanged_since=now)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_dump(payload))
    return True


def _read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def self_test():
    now = "2026-09-10T21:00:00Z"
    pulls = [
        {"number": 3, "title": "newest", "user": {"login": "a"},
         "created_at": "2026-09-10T20:00:00Z", "head": {"ref": "b3"}},
        {"number": 1, "title": "oldest", "user": {"login": "b"}, "draft": True,
         "created_at": "2026-09-01T00:00:00Z", "head": {"ref": "b1"}},
        {"number": 2, "title": "middle", "user": {"login": "c"},
         "created_at": "2026-09-05T00:00:00Z", "head": {"ref": "b2"}},
        {"number": 4, "title": "undated", "user": {"login": "d"}},
    ]
    counts = {"repository": "o/r", "open_prs": 106, "open_issues": 3,
              "runs_queued": 2284, "runs_in_progress": 18}
    out = build(pulls, counts, now)
    assert out["counts"]["open_pull_requests"] == 106
    assert out["counts"]["runs_queued"] == 2284
    assert out["queue_depth_per_runner"] == round(2284 / 18, 1)
    assert [p["number"] for p in out["newest_pulls"]] == [3, 2, 1]
    assert out["longest_open"][0]["number"] == 1
    assert out["pulls_listed"] == 4
    assert out["undatable_pulls"] == [4]
    assert out["drafts"] == 1
    assert _dump(build(pulls, counts, "2026-09-11T09:00:00Z")) == _dump(out)

    sparse = build(None, {"repository": "o/r"}, now)
    assert sparse["counts"]["open_pull_requests"] == UNKNOWN
    assert sparse["counts"]["runs_queued"] == UNKNOWN
    assert sparse["queue_depth_per_runner"] == UNKNOWN
    assert sparse["pulls_listed"] == UNKNOWN
    assert "newest_pulls" not in sparse

    zeroed = build([], {"open_prs": 0, "runs_queued": 0, "runs_in_progress": 0}, now)
    assert zeroed["counts"]["open_pull_requests"] == 0
    assert zeroed["pulls_listed"] == 0
    assert zeroed["queue_depth_per_runner"] == UNKNOWN
    assert build(None, {}, now, degraded=["pulls"])["degraded"] == ["pulls"]
    print("github_state self-test: PASS")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--pulls", help="JSON file from the open pull requests call")
    ap.add_argument("--repository", default="")
    ap.add_argument("--open-prs")
    ap.add_argument("--open-issues")
    ap.add_argument("--runs-queued")
    ap.add_argument("--runs-in-progress")
    ap.add_argument("--observed-at", default="")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    now = args.observed_at.strip() or _dt.datetime.now(
        _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pulls, degraded = None, []
    if args.pulls:
        try:
            pulls = _read_json(args.pulls)
            if not isinstance(pulls, list):
                pulls, degraded = None, ["pulls"]
        except Exception:
            pulls, degraded = None, ["pulls"]
    else:
        degraded = ["pulls"]
    payload = build(pulls, {
        "repository": args.repository,
        "open_prs": args.open_prs,
        "open_issues": args.open_issues,
        "runs_queued": args.runs_queued,
        "runs_in_progress": args.runs_in_progress,
    }, now, degraded)
    if args.write:
        changed = write(args.root, payload, now)
        counts = payload["counts"]
        print("github_state: %s open PRs, %s queued runs, %s in progress — %s"
              % (counts["open_pull_requests"], counts["runs_queued"],
                 counts["runs_in_progress"], "written" if changed else "unchanged"))
        if payload["degraded"]:
            sys.stderr.write("github_state: degraded sources: %s\n"
                             % ", ".join(payload["degraded"]))
        return 0
    print(_dump(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
