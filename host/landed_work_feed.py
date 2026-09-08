#!/usr/bin/env python3
"""Per-merge landed-work feed. One line. Not per day. Not a digest.

Ride named leftover commons-ship-enforcer (Claude is taking headless on
the owner PC). This helper formats the merge line the enforcer already
knows. --send/--go REFUSED: no new Slack secret in this repo.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "ground/LANDED_WORK_FEED.json"
REPO = "woahwhattheheck/commons"
CHANNEL = "C0BTVA3C0G3"
BAKE_SUBJECT = "llms.txt+fresh.md"
BAKE_PATHS = {
    "llms.txt",
    "fresh.md",
    "pulse.json",
    "head.json",
    "peers.md",
    "change.md",
    "challenge.json",
}
PR_RE = re.compile(r"#(\d+)")
REFUSE = ("--send", "--apply", "--go", "--autopilot")


def git(args: list[str], cwd: Path | None = None) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=str(cwd or ROOT), text=True
    ).strip()


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or CATALOG).read_text(encoding="utf-8"))


def harness_of(author: str) -> str:
    name = author.strip()
    if name == "Cursor Agent":
        return "cursor"
    if name == "commons-llms":
        return "bake"
    if name in {"GitHub", "woahwhattheheck"}:
        return "github"
    return name.replace(" ", "-").lower() or "UNSEATED"


def paths_of(sha: str, cwd: Path | None = None) -> list[str]:
    # NUL-delimited bytes preserve Git filenames, including whitespace/Unicode.
    out = subprocess.check_output(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r",
         "--diff-merges=first-parent", "--root", "-z", sha],
        cwd=str(cwd or ROOT),
    )
    return [os.fsdecode(path) for path in out.split(b"\0") if path]


def parse_commit(sha: str, author: str, subject: str, cwd: Path | None = None) -> dict[str, Any] | None:
    if subject.startswith(BAKE_SUBJECT):
        return None
    paths = paths_of(sha, cwd)
    if paths and set(paths) <= BAKE_PATHS:
        return None
    pr_match = PR_RE.search(subject)
    return {
        "repo": REPO,
        "pr": int(pr_match.group(1)) if pr_match else None,
        "sha": sha,
        "title": subject,
        "harness": harness_of(author),
        "paths": paths,
        "author": author,
    }


def _line_label(text: str, delimiters: str = "") -> str:
    if any(ord(c) < 32 or c in "\x85\u2028\u2029" + delimiters for c in text):
        return json.dumps(text, ensure_ascii=True)
    return text


def format_line(row: dict[str, Any]) -> str:
    pr = f"#{row['pr']}" if row.get("pr") else "PR=FINDER-FAILED"
    path_labels = [_line_label(path, '\\",') for path in row.get("paths") or []]
    paths = ",".join(path_labels) or "paths=FINDER-FAILED"
    return (
        f"{row['repo']} {pr} {row['sha'][:9]} {_line_label(row['title'])} "
        f"harness={_line_label(row['harness'])} paths={paths}"
    )


def recent_merges(limit: int = 8, cwd: Path | None = None) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    # Pin one history before paging; new commits must not shift page offsets.
    head = git(["rev-parse", "HEAD"], cwd=cwd)
    page_size = max(24, limit * 3)
    offset = 0
    rows: list[dict[str, Any]] = []
    while len(rows) < limit:
        raw = git(
            ["log", "--first-parent", f"--max-count={page_size}",
             f"--skip={offset}", "-z", "--format=%H%x00%an%x00%s", head, "--"],
            cwd=cwd,
        )
        # Fixed-width NUL fields preserve empty subjects and embedded tabs.
        fields = raw.split("\0")[:-1]
        records = [fields[i:i + 3] for i in range(0, len(fields), 3)]
        for sha, author, subject in records:
            parsed = parse_commit(sha, author, subject, cwd)
            if parsed is None:
                continue
            rows.append(parsed)
            if len(rows) >= limit:
                return rows
        if len(records) < page_size:
            break
        offset += len(records)
    return rows


def refuse_payload(flag: str) -> dict[str, Any]:
    return {
        "kind": "LANDED_WORK_FEED",
        "id": "cursor-landed-work-feed-20260902-01",
        "gate": False,
        "refused": flag,
        "verdict": "FINDER-FAILED",
        "sent": 0,
        "cash": 0,
        "note": f"{flag} REFUSED. No new Slack secret. Use the harness that already has Slack.",
    }


def measure(limit: int = 8, cwd: Path | None = None) -> dict[str, Any]:
    catalog = load_catalog()
    rows = recent_merges(limit, cwd)
    return {
        "kind": "LANDED_WORK_FEED",
        "id": catalog["id"],
        "gate": False,
        "commons_admission": False,
        "cadence": "per-merge",
        "not_per_day": True,
        "channel": CHANNEL,
        "thread_per": "repo",
        "ride": catalog["ride"],
        "headless_enforcer": catalog["headless_enforcer"],
        "invented_stripe_urls": False,
        "sends": 0,
        "cash_usd": 0,
        "repos_named_here": catalog["repos_named_here"],
        "twelve_named_here": False,
        "unnamed_remainder": "FINDER-FAILED",
        "count": len(rows),
        "lines": [format_line(row) for row in rows],
        "merges": rows,
        "verdict": "RENDER",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--limit", type=int, default=8)
    args, unknown = parser.parse_known_args(argv)
    for flag in unknown:
        if flag in REFUSE:
            print(json.dumps(refuse_payload(flag), sort_keys=True))
            return 2
        if flag.startswith("-"):
            print(
                json.dumps(
                    {
                        "kind": "LANDED_WORK_FEED",
                        "verdict": "FINDER-FAILED",
                        "sent": 0,
                        "unknown": flag,
                    },
                    sort_keys=True,
                )
            )
            return 1
    packet = measure(args.limit)
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
