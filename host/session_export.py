#!/usr/bin/env python3
"""host/session_export.py — measure hoarded session bytes.

Owner Slack 1787627026.727319: commit and push every build. Do not
hoard work in the session and make Bryce track it down.

This instrument reads one clone. It does not write. It does not add a
gate. Uncommitted or unpushed bytes are NOT_LANDED. A pushed branch
that is still ahead of main is CANDIDATE. Talk without these numbers
is CLAIMED.

  python3 host/session_export.py
  python3 host/session_export.py --root /path/to/clone
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys


def classify(row):
    """Turn a measured clone row into a land-desk state."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": "session dirty/unpushed state not measured. Absence was not stillness.",
        }
    dirty = int(row.get("dirty") or 0)
    unpushed = int(row.get("unpushed") or 0)
    ahead = int(row.get("ahead_of_main") or 0)
    if dirty > 0 or unpushed > 0:
        return {
            "state": "NOT_LANDED",
            "note": (
                "session has %s dirty path(s) and %s unpushed commit(s). "
                "Commit, push, and merge to current main."
            )
            % (dirty, unpushed),
        }
    if ahead > 0:
        return {
            "state": "CANDIDATE",
            "note": (
                "this clone is %s commit(s) ahead of origin/main and still "
                "not merged. A push is not current main."
            )
            % ahead,
        }
    return {
        "state": "INTEGRATED",
        "note": "this clone has no hoarded bytes. Still measure the intended path on official main.",
    }


def measure_from_git_text(status_text, rev_list_text, ahead_text="0"):
    """Pure parser so tests do not need a live git remote."""
    dirty = 0
    for line in str(status_text or "").splitlines():
        if line.strip():
            dirty += 1
    unpushed = 0
    for line in str(rev_list_text or "").splitlines():
        if line.strip():
            unpushed += 1
    try:
        ahead = int(str(ahead_text or "0").strip() or "0")
    except ValueError:
        ahead = unpushed
    return {
        "measured": True,
        "dirty": dirty,
        "unpushed": unpushed,
        "ahead_of_main": ahead,
        "titan": "NOT_WRITTEN",
    }


def _run(root, args):
    proc = subprocess.run(
        args,
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def measure_clone(root):
    root = os.path.abspath(root)
    if not os.path.isdir(os.path.join(root, ".git")) and not os.path.isfile(
        os.path.join(root, ".git")
    ):
        return {
            "measured": False,
            "root": root,
            "error": "not a git clone",
            "titan": "NOT_WRITTEN",
        }
    code, status_out, status_err = _run(root, ["git", "status", "--porcelain"])
    if code != 0:
        return {
            "measured": False,
            "root": root,
            "error": status_err.strip() or "git status failed",
            "titan": "NOT_WRITTEN",
        }
    _run(root, ["git", "rev-parse", "--verify", "origin/main"])
    code, rev_out, _rev_err = _run(
        root, ["git", "rev-list", "--max-count=200", "origin/main..HEAD"]
    )
    if code != 0:
        rev_out = ""
    code, count_out, _count_err = _run(
        root, ["git", "rev-list", "--count", "origin/main..HEAD"]
    )
    ahead_text = count_out.strip() if code == 0 else "0"
    row = measure_from_git_text(status_out, rev_out, ahead_text)
    row["root"] = root
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure session hoard vs origin/main")
    parser.add_argument("--root", default=".", help="clone to measure")
    args = parser.parse_args(argv)
    row = measure_clone(args.root)
    verdict = classify(row)
    payload = dict(row)
    payload.update(verdict)
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if row.get("measured") else 2


if __name__ == "__main__":
    sys.exit(main())
