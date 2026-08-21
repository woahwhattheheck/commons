#!/usr/bin/env python3
"""Land exact action outputs on a moving Commons main, on any runner OS."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, check=check,
                          capture_output=True)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(value: object) -> str:
    raw = str(value or "").strip().replace("\\", "/").lstrip("/")
    if not raw or ".." in raw.split("/") or raw == ".git" or raw.startswith(".git/"):
        raise ValueError("unsafe action output path: %r" % value)
    path = (ROOT / raw).resolve()
    if ROOT.resolve() != path and ROOT.resolve() not in path.parents:
        raise ValueError("action output escapes repository: %s" % raw)
    return raw


def validate_manifest(data: dict) -> list[str]:
    paths = [safe_path(p) for p in data.get("changed", []) if str(p).strip()]
    if len(paths) != len(set(paths)):
        raise ValueError("action manifest contains duplicate paths")
    canonical = {safe_path(k): str(v) for k, v in (data.get("canonical_records") or {}).items()}
    results = {safe_path(k): str(v) for k, v in (data.get("result_records") or {}).items()}
    for name in paths:
        path = ROOT / name
        if not path.is_file():
            raise ValueError("action output is missing or not a regular file: %s" % name)
        actual = file_sha256(path)
        if results.get(name) == actual:
            continue
        if canonical.get(name) != actual:
            raise ValueError(
                "UNAUTHORIZED_WRITE: action output lacks an exact canonical-writer/result hash: %s" % name
            )
        if name.startswith("p/") and git("ls-files", "--error-unmatch", name, check=False).returncode == 0:
            raise ValueError("UNAUTHORIZED_WRITE: Action Pad may not modify an existing post path: %s" % name)
    return paths


def main() -> int:
    data = json.loads((ROOT / ".action_changed.json").read_text(encoding="utf-8"))
    paths = validate_manifest(data)
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
