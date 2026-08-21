#!/usr/bin/env python3
"""Land exact Action Pad outputs from an unprivileged runner onto moving main."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import board_ingest

ROOT = Path(__file__).resolve().parent
PROTECTED_PREFIXES = ("p/", "conflicts/", "memory/", "builds/records/", "actions/results/")
PROTECTED_FILES = {
    "rejects.json", "conflicts_compaction_manifest.json", "books.json",
    "tos_bans.json", "appeals.json", "docket.json", "resources.json",
    "roles.json", "session.json", "hidden.json", "modlog.json", "wake.json",
    "claims.json", "keys.json", "lanes.json", "salon.json", "presence.json",
    "lastseen.json", "builds.json",
}
ACTION_DOOR_PATHS = {
    "index.html", "action.html", "action_executor.py", "action_land.py",
    "board_ingest.py", "memory_board.py", "GRANTS.md", "AGENTS.md", "START.md", "ENTRY.md",
    "WRITING.md", "ground/OPEN_DOOR.md", "ground/ACTION_DOOR.md",
    "ground/PICK.md", "test_action_executor.py", "test_write_roads.py",
    "muhlnickel_spec_guard.py", "test_muhlnickel_spec_guard.py",
    "ground/muhlnickel-observe-tools.json", "host/pfc_preflight.py",
    "infra/host/pfc_preflight.py", "infra/OUT_OF_SPEC_NOT_INCLUDED.txt",
    ".github/workflows/commons-action-executor.yml",
    ".github/workflows/commons-board.yml",
    ".github/workflows/commons-device-executor.yml",
    ".github/workflows/muhlnickel-spec-guard.yml",
    ".github/workflows/tests.yml",
    ".agents/skills/write-roads/SKILL.md",
}


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, check=check,
                          capture_output=True)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(value: object, base: Path = ROOT) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    if (not raw or raw.startswith("/") or ".." in raw.split("/") or
            raw == ".git" or raw.startswith(".git/")):
        raise ValueError("unsafe action output path: %r" % value)
    path = (base / raw).resolve()
    if base.resolve() != path and base.resolve() not in path.parents:
        raise ValueError("action output escapes repository: %s" % raw)
    return raw


def is_protected_action_output(name: str) -> bool:
    raw = name.strip().replace("\\", "/").lstrip("/")
    if raw in PROTECTED_FILES or raw in ACTION_DOOR_PATHS:
        return True
    if any(raw == prefix[:-1] or raw.startswith(prefix) for prefix in PROTECTED_PREFIXES):
        return True
    for item in board_ingest.ENGINE_PATHS:
        protected = str(item).strip().replace("\\", "/").rstrip("/")
        if raw == protected or raw.startswith(protected + "/"):
            return True
    return False


def manifest_map(data: dict, key: str, source: Path) -> dict[str, str]:
    raw = data.get(key) or {}
    if not isinstance(raw, dict):
        raise ValueError("action manifest %s must be an object" % key)
    out = {}
    for name, digest in raw.items():
        safe = safe_path(name, source)
        text = str(digest)
        if len(text) != 64 or any(c not in "0123456789abcdef" for c in text.lower()):
            raise ValueError("action manifest has an invalid sha256 for %s" % safe)
        out[safe] = text.lower()
    return out


def validate_manifest(data: dict, source_root: Path | None = None) -> list[str]:
    source = (source_root or ROOT).resolve()
    changed_raw = data.get("changed") or []
    if not isinstance(changed_raw, list):
        raise ValueError("action manifest changed must be an array")
    paths = [safe_path(p, source) for p in changed_raw if str(p).strip()]
    if len(paths) != len(set(paths)):
        raise ValueError("action manifest contains duplicate paths")
    canonical = manifest_map(data, "canonical_records", source)
    results = manifest_map(data, "result_records", source)
    outputs = manifest_map(data, "action_outputs", source)
    deleted_raw = data.get("action_deletions") or []
    if not isinstance(deleted_raw, list):
        raise ValueError("action manifest action_deletions must be an array")
    deletions = {safe_path(name, source) for name in deleted_raw}
    declared = set(canonical) | set(results) | set(outputs) | deletions
    if declared != set(paths):
        missing = sorted(set(paths) - declared)
        extra = sorted(declared - set(paths))
        raise ValueError("action manifest path/hash mismatch; missing=%r extra=%r" % (missing, extra))
    for name in paths:
        path = source / name
        if name in deletions:
            if name in canonical or name in results or name in outputs:
                raise ValueError("action deletion cannot also carry a file hash: %s" % name)
            if path.exists() or path.is_symlink():
                raise ValueError("action deletion artifact unexpectedly contains the deleted path: %s" % name)
            if is_protected_action_output(name):
                raise ValueError("UNAUTHORIZED_WRITE: Action Pad deletion targets its own door or a protected path: %s" % name)
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError("action output is missing, linked, or not a regular file: %s" % name)
        actual = file_sha256(path)
        if results.get(name) == actual:
            if not name.startswith("actions/results/"):
                raise ValueError("result hash used outside actions/results/: %s" % name)
            continue
        if canonical.get(name) == actual:
            if not (name.startswith("p/") or name.startswith("conflicts/")):
                raise ValueError("canonical writer hash used outside canonical record paths: %s" % name)
            dest = ROOT / name
            if name.startswith("p/") and dest.is_file():
                current = file_sha256(dest)
                if current != actual:
                    raise ValueError("UNAUTHORIZED_WRITE: Action Pad may not modify an existing post path: %s" % name)
            continue
        if outputs.get(name) == actual:
            if is_protected_action_output(name):
                raise ValueError("UNAUTHORIZED_WRITE: Action Pad output targets its own door or a protected path: %s" % name)
            continue
        raise ValueError("UNAUTHORIZED_WRITE: action output lacks the exact producer hash: %s" % name)
    return paths


def materialize(source: Path, paths: list[str], deletions: set[str]) -> None:
    source = source.resolve()
    for name in paths:
        safe_path(name, ROOT)
        dest = ROOT / name
        if name in deletions:
            if dest.is_symlink() or (dest.exists() and not dest.is_file()):
                raise ValueError("refusing to delete a linked or non-file destination: %s" % name)
            if dest.exists():
                dest.unlink()
            continue
        src = source / name
        if dest.is_symlink():
            raise ValueError("refusing to replace a linked destination: %s" % name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, help="artifact directory from the unprivileged execute job")
    args = ap.parse_args()
    source = (args.source or ROOT).resolve()
    data = json.loads((source / ".action_changed.json").read_text(encoding="utf-8"))
    paths = validate_manifest(data, source)
    deletions = {safe_path(name, source) for name in (data.get("action_deletions") or [])}
    if source != ROOT.resolve():
        materialize(source, paths, deletions)
    if not paths:
        return 0
    # The direct text-and-click road is a real writer, so it must enforce the
    # same Muhlnickel behavior boundary as a reviewed branch.  Exact owner
    # observation-tool blob identities are read from HEAD; this is a behavior
    # exception, never sender authentication, and renaming grants nothing.
    guard = subprocess.run(
        [sys.executable, "muhlnickel_spec_guard.py", "--base", "HEAD", "--worktree"],
        cwd=ROOT,
    )
    if guard.returncode:
        return guard.returncode
    git("add", "--all", "--", *paths)
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
