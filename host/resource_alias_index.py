#!/usr/bin/env python3
"""Build a deterministic content-addressed alias index for tracked Git blobs.

Git already stores identical content once. This tool makes the logical aliases
explicit for consumers without deleting files, rewriting history, or copying
blob contents. It reads only the named Git tree.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "commons-resource-alias-index/v1"


class AliasIndexError(ValueError):
    """The Git inventory or checked snapshot is not internally consistent."""


def canonical_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def parse_ls_tree(raw: bytes) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, oid, raw_size = metadata.decode("ascii").split()
        except (ValueError, UnicodeDecodeError) as exc:
            raise AliasIndexError("malformed git ls-tree record") from exc
        if object_type != "blob":
            continue
        try:
            size = int(raw_size)
        except ValueError as exc:
            raise AliasIndexError(f"blob {oid} has non-integer size") from exc
        path = raw_path.decode("utf-8", "surrogateescape")
        entries.append({"mode": mode, "path": path, "sha": oid, "size": size})
    return entries


def build_alias_index(
    entries: Iterable[dict[str, Any]],
    *,
    source_commit: str,
    source_tree: str,
) -> dict[str, Any]:
    by_oid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_paths: set[str] = set()
    blob_count = 0

    for raw in entries:
        path = str(raw["path"])
        oid = str(raw["sha"]).lower()
        size = int(raw["size"])
        mode = str(raw.get("mode") or "100644")
        if path in seen_paths:
            raise AliasIndexError(f"duplicate tracked path: {path}")
        if size < 0:
            raise AliasIndexError(f"negative blob size: {path}")
        if len(oid) not in {40, 64} or any(ch not in "0123456789abcdef" for ch in oid):
            raise AliasIndexError(f"invalid Git object id: {oid}")
        seen_paths.add(path)
        blob_count += 1
        by_oid[oid].append({"mode": mode, "path": path, "size": size})

    groups: list[dict[str, Any]] = []
    for oid, members in sorted(by_oid.items()):
        if len(members) < 2:
            continue
        sizes = {member["size"] for member in members}
        if len(sizes) != 1:
            raise AliasIndexError(f"content address {oid} has inconsistent sizes")
        size = sizes.pop()
        members.sort(key=lambda item: item["path"])
        canonical = members[0]
        groups.append(
            {
                "content_address": f"git_blob:{oid}",
                "size": size,
                "path_count": len(members),
                "canonical_path": canonical["path"],
                "canonical_mode": canonical["mode"],
                "aliases": [
                    {"path": member["path"], "mode": member["mode"]}
                    for member in members[1:]
                ],
                "logical_bytes": size * len(members),
                "alias_bytes": size * (len(members) - 1),
            }
        )

    logical_files = sum(group["path_count"] for group in groups)
    alias_paths = sum(group["path_count"] - 1 for group in groups)
    return {
        "schema": SCHEMA,
        "source_commit": source_commit,
        "source_tree": source_tree,
        "scope": "all tracked Git blobs",
        "truth": {
            "git_blob_object_ids_are_content_addresses": True,
            "logical_aliases_are_not_new_physical_git_capacity": True,
            "deletions_performed": 0,
            "history_rewrites_performed": 0,
            "blob_contents_copied": 0,
        },
        "summary": {
            "tracked_blobs": blob_count,
            "unique_content_addresses": len(by_oid),
            "duplicate_groups": len(groups),
            "logical_files_in_duplicate_groups": logical_files,
            "extra_alias_paths": alias_paths,
            "logical_duplicate_bytes": sum(group["logical_bytes"] for group in groups),
            "alias_bytes": sum(group["alias_bytes"] for group in groups),
        },
        "groups": groups,
    }


def git_output(*args: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", *args],
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"").decode("utf-8", "replace").strip()
        raise AliasIndexError(f"git {' '.join(args)} failed: {detail}") from exc


def scan_git(ref: str) -> dict[str, Any]:
    commit = git_output("rev-parse", f"{ref}^{{commit}}").decode("ascii").strip()
    tree = git_output("rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    raw = git_output("ls-tree", "-r", "-l", "-z", "--full-tree", commit)
    return build_alias_index(
        parse_ls_tree(raw),
        source_commit=commit,
        source_tree=tree,
    )


def check_snapshot(path: Path) -> dict[str, Any]:
    expected = json.loads(path.read_text(encoding="utf-8"))
    if expected.get("schema") != SCHEMA:
        raise AliasIndexError(f"{path} is not {SCHEMA}")
    source_commit = expected.get("source_commit")
    if not isinstance(source_commit, str) or not source_commit:
        raise AliasIndexError(f"{path} has no source_commit")
    actual = scan_git(source_commit)
    if actual != expected:
        raise AliasIndexError(f"{path} differs from source commit {source_commit}")
    return actual


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD", help="Git commit or ref to scan")
    parser.add_argument("--check", type=Path, help="verify a pinned snapshot")
    parser.add_argument("--output", type=Path, help="write instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = check_snapshot(args.check) if args.check else scan_git(args.ref)
        if args.check:
            summary = result["summary"]
            print(
                "MATCH "
                f"{summary['tracked_blobs']} blobs "
                f"{summary['duplicate_groups']} groups "
                f"{summary['extra_alias_paths']} aliases "
                f"{summary['alias_bytes']} alias-bytes"
            )
            return 0
        rendered = canonical_text(result)
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except (AliasIndexError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"resource-alias-index: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
