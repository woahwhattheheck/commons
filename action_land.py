#!/usr/bin/env python3
"""Land exact action outputs on a moving Commons main, on any runner OS."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, check=check,
                          capture_output=True)


def main() -> int:
    data = json.loads((ROOT / ".action_changed.json").read_text(encoding="utf-8"))
    paths = [str(p) for p in data.get("changed", []) if str(p).strip()]
    if not paths:
        return 0
    git("add", "--", *paths)
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        return 0
    git("config", "user.name", "commons-action")
    git("config", "user.email", "commons-action@users.noreply.github.com")
    git("commit", "-m", "fire addressed Commons actions")
    for attempt in range(1, 6):
        if git("push", "origin", "HEAD:main", check=False).returncode == 0:
            return 0
        git("fetch", "origin", "main")
        if git("rebase", "origin/main", check=False).returncode != 0:
            git("rebase", "--abort", check=False)
            return 1
        time.sleep(attempt * 3)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
