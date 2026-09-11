#!/usr/bin/env python3
"""Prove owned-path preimages are unchanged before a non-force moving-main refresh."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import PurePosixPath
from typing import Iterable


HOLD_EXIT = 2


class CheckError(RuntimeError):
    pass


def run_git(repo: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    proc = subprocess.run(
        ["git", "-C", repo, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", "replace").strip()
        raise CheckError(f"git {' '.join(args)} failed: {stderr or f'exit {proc.returncode}'}")
    return proc


def resolve_commit(repo: str, ref: str) -> str:
    out = run_git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").stdout
    value = out.decode().strip()
    if len(value) != 40:
        raise CheckError(f"unexpected commit id for {ref!r}: {value!r}")
    return value


def is_ancestor(repo: str, older: str, newer: str) -> bool:
    proc = run_git(repo, "merge-base", "--is-ancestor", older, newer, check=False)
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    stderr = proc.stderr.decode("utf-8", "replace").strip()
    raise CheckError(f"git merge-base --is-ancestor failed: {stderr or proc.returncode}")


def changed_paths(repo: str, base: str, head: str) -> list[str]:
    raw = run_git(repo, "diff", "--name-only", "-z", base, head, "--").stdout
    return sorted(p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p)


def validate_owned_paths(paths: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    clean: list[str] = []
    for raw in paths:
        if not raw or "\x00" in raw:
            raise CheckError("owned paths must be nonempty and contain no NUL")
        path = PurePosixPath(raw)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise CheckError(f"unsafe owned path: {raw!r}")
        normalized = str(path)
        if normalized != raw:
            raise CheckError(f"owned path must be normalized POSIX text: {raw!r}")
        if raw in seen:
            raise CheckError(f"duplicate owned path: {raw!r}")
        seen.add(raw)
        clean.append(raw)
    if not clean:
        raise CheckError("at least one --path is required")
    return sorted(clean)


@dataclass(frozen=True)
class TreeIdentity:
    state: str
    mode: str | None = None
    object_type: str | None = None
    object_id: str | None = None


def tree_identity(repo: str, commit: str, path: str) -> TreeIdentity:
    raw = run_git(repo, "ls-tree", "-z", commit, "--", path).stdout
    entries = [entry for entry in raw.split(b"\0") if entry]
    if not entries:
        return TreeIdentity(state="ABSENT")
    if len(entries) != 1:
        raise CheckError(f"expected one tree entry for {path!r}, got {len(entries)}")
    try:
        meta, encoded_path = entries[0].split(b"\t", 1)
        mode, object_type, object_id = meta.decode("ascii").split(" ", 2)
    except (ValueError, UnicodeDecodeError) as exc:
        raise CheckError(f"malformed ls-tree entry for {path!r}") from exc
    actual_path = encoded_path.decode("utf-8", "surrogateescape")
    if actual_path != path:
        raise CheckError(f"ls-tree path mismatch: expected {path!r}, got {actual_path!r}")
    return TreeIdentity(
        state="PRESENT",
        mode=mode,
        object_type=object_type,
        object_id=object_id,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Git working tree or bare repository")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--current-main", required=True)
    parser.add_argument("--path", action="append", dest="paths", default=[])
    args = parser.parse_args(argv)

    try:
        owned = validate_owned_paths(args.paths)
        base = resolve_commit(args.repo, args.base)
        head = resolve_commit(args.repo, args.head)
        current = resolve_commit(args.repo, args.current_main)

        reasons: list[str] = []
        topology = {
            "base_is_ancestor_of_head": is_ancestor(args.repo, base, head),
            "base_is_ancestor_of_current_main": is_ancestor(args.repo, base, current),
        }
        if not topology["base_is_ancestor_of_head"]:
            reasons.append("BASE_NOT_ANCESTOR_OF_HEAD")
        if not topology["base_is_ancestor_of_current_main"]:
            reasons.append("BASE_NOT_ANCESTOR_OF_CURRENT_MAIN")

        candidate_paths = changed_paths(args.repo, base, head)
        if candidate_paths != owned:
            reasons.append("CANDIDATE_SCOPE_MISMATCH")

        path_rows = []
        for path in owned:
            base_id = tree_identity(args.repo, base, path)
            current_id = tree_identity(args.repo, current, path)
            head_id = tree_identity(args.repo, head, path)
            unchanged = base_id == current_id
            if not unchanged:
                reasons.append(f"OWNED_PREIMAGE_CHANGED:{path}")
            path_rows.append(
                {
                    "path": path,
                    "base": asdict(base_id),
                    "current_main": asdict(current_id),
                    "head": asdict(head_id),
                    "preimage_unchanged": unchanged,
                }
            )

        reasons = sorted(set(reasons))
        result = {
            "schema": "commons-moving-main-preimage-v1",
            "status": "PASS" if not reasons else "HOLD",
            "repo": args.repo,
            "base": base,
            "head": head,
            "current_main": current,
            "topology": topology,
            "owned_paths": owned,
            "candidate_changed_paths": candidate_paths,
            "paths": path_rows,
            "reasons": reasons,
            "mutation_performed": False,
        }
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if not reasons else HOLD_EXIT
    except CheckError as exc:
        print(json.dumps({"schema": "commons-moving-main-preimage-v1", "status": "ERROR", "error": str(exc), "mutation_performed": False}, sort_keys=True, indent=2))
        return 64


if __name__ == "__main__":
    sys.exit(main())
