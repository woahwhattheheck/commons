#!/usr/bin/env python3
"""Plan or apply a bounded, preimage-safe viewport backfill to tracked derived pages.

Dry-run is the default. A dry-run scans the already-landed viewport_check.py
inventory, selects at most --limit missing p/*.html pages after --cursor, and
emits a JSON manifest with exact before/after SHA-256 digests. Applying changes
requires that manifest and refuses to write unless HEAD and every selected
preimage still match.

The only page-byte mutation is insertion of VIEWPORT_TAG immediately after the
opening <head...> tag. No regeneration or other HTML normalization occurs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import viewport_check


SCHEMA = "commons-viewport-backfill/v1"
VIEWPORT_TAG = '<meta name="viewport" content="width=device-width, initial-scale=1">'
_VIEWPORT_BYTES = VIEWPORT_TAG.encode("ascii")
_HEAD_RE = re.compile(br"<head(?:\s[^>]*)?>", re.IGNORECASE)
DEFAULT_PREFIX = "p/"
MAX_LIMIT = 100


class BackfillError(RuntimeError):
    """A deterministic safety boundary was not satisfied."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd or Path.cwd()),
        capture_output=True,
        check=False,
    )


def _head_sha() -> str:
    done = _git(["rev-parse", "--verify", "HEAD"])
    sha = (done.stdout or b"").decode("ascii", "replace").strip()
    if done.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise BackfillError("HEAD is not an addressable git commit")
    return sha


def _safe_relpath(value: str) -> str:
    path = value.replace("\\", "/")
    if (
        not path
        or path.startswith("/")
        or path.startswith("../")
        or "/../" in path
        or path.endswith("/..")
    ):
        raise BackfillError("unsafe manifest path")
    return path


def _text(raw: bytes) -> str:
    return raw.decode("utf-8-sig", errors="replace")


def _is_document(raw: bytes) -> bool:
    return _text(raw).lstrip()[:1] == "<"


def _has_viewport(raw: bytes) -> bool:
    return viewport_check._has_viewport(_text(raw))


def insert_viewport(raw: bytes) -> bytes:
    """Return raw bytes with exactly one canonical viewport tag inserted."""
    if _has_viewport(raw):
        return raw
    match = _HEAD_RE.search(raw)
    if match is None:
        raise BackfillError("missing <head> insertion point")
    return raw[: match.end()] + _VIEWPORT_BYTES + raw[match.end() :]


def _assert_clean_selected(paths: list[str]) -> None:
    if not paths:
        return
    done = _git(["diff", "--quiet", "HEAD", "--", *paths])
    if done.returncode == 1:
        raise BackfillError("selected batch has a moved working-tree preimage")
    if done.returncode != 0:
        raise BackfillError("git preimage check failed")


def build_plan(limit: int, cursor: str = "", prefix: str = DEFAULT_PREFIX) -> dict[str, Any]:
    if limit < 1 or limit > MAX_LIMIT:
        raise BackfillError("limit must be between 1 and %d" % MAX_LIMIT)
    cursor = cursor.replace("\\", "/")
    prefix = _safe_relpath(prefix)
    if not prefix.endswith("/"):
        prefix += "/"

    base = _head_sha()
    try:
        tracked = viewport_check.tracked_pages()
    except viewport_check.GitInventoryError as exc:
        raise BackfillError(str(exc)) from exc

    derived = [p for p in tracked if p.startswith(prefix)]
    missing = 0
    skipped_non_document = 0
    unsupported_no_head = 0
    candidates: list[dict[str, Any]] = []

    for path in derived:
        try:
            raw = Path(path).read_bytes()
        except OSError as exc:
            raise BackfillError("tracked page unreadable: %s" % path) from exc
        if not _is_document(raw):
            skipped_non_document += 1
            continue
        if _has_viewport(raw):
            continue
        missing += 1
        try:
            after = insert_viewport(raw)
        except BackfillError:
            unsupported_no_head += 1
            continue
        candidates.append(
            {
                "path": path,
                "before_sha256": _sha256(raw),
                "after_sha256": _sha256(after),
                "inserted_bytes": len(after) - len(raw),
            }
        )

    candidates.sort(key=lambda row: row["path"])
    eligible_after_cursor = [row for row in candidates if row["path"] > cursor]
    changes = eligible_after_cursor[:limit]
    selected_paths = [row["path"] for row in changes]
    _assert_clean_selected(selected_paths)

    next_cursor = None
    if len(eligible_after_cursor) > len(changes) and changes:
        next_cursor = changes[-1]["path"]

    return {
        "schema": SCHEMA,
        "mode": "dry-run",
        "base_head_sha": base,
        "prefix": prefix,
        "limit": limit,
        "cursor": cursor,
        "viewport_tag": VIEWPORT_TAG,
        "tracked_html_count": len(tracked),
        "derived_tracked_count": len(derived),
        "missing_viewport_count": missing,
        "selectable_count": len(candidates),
        "skipped_non_document_count": skipped_non_document,
        "unsupported_missing_head_count": unsupported_no_head,
        "selected_count": len(changes),
        "next_cursor": next_cursor,
        "changes": changes,
    }


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackfillError("manifest unreadable") from exc
    if not isinstance(value, dict):
        raise BackfillError("manifest must be a JSON object")
    return value


def apply_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("schema") != SCHEMA:
        raise BackfillError("manifest schema mismatch")
    if manifest.get("viewport_tag") != VIEWPORT_TAG:
        raise BackfillError("manifest viewport tag mismatch")
    base = str(manifest.get("base_head_sha") or "")
    if base != _head_sha():
        raise BackfillError("HEAD moved since dry-run")
    prefix = _safe_relpath(str(manifest.get("prefix") or DEFAULT_PREFIX))
    if not prefix.endswith("/"):
        prefix += "/"
    changes = manifest.get("changes")
    if not isinstance(changes, list) or len(changes) > MAX_LIMIT:
        raise BackfillError("manifest changes are invalid")

    verified: list[tuple[Path, bytes, bytes, dict[str, Any]]] = []
    paths: list[str] = []
    for row in changes:
        if not isinstance(row, dict):
            raise BackfillError("manifest change must be an object")
        rel = _safe_relpath(str(row.get("path") or ""))
        if not rel.startswith(prefix):
            raise BackfillError("manifest path is outside derived prefix")
        path = Path(rel)
        try:
            before = path.read_bytes()
        except OSError as exc:
            raise BackfillError("manifest preimage missing: %s" % rel) from exc
        if _sha256(before) != str(row.get("before_sha256") or ""):
            raise BackfillError("preimage digest moved: %s" % rel)
        after = insert_viewport(before)
        if _sha256(after) != str(row.get("after_sha256") or ""):
            raise BackfillError("after digest mismatch: %s" % rel)
        if after == before:
            raise BackfillError("manifest page is already idempotently complete: %s" % rel)
        paths.append(rel)
        verified.append((path, before, after, row))

    # Verify the complete selected batch before the first page write.
    _assert_clean_selected(paths)

    applied: list[dict[str, Any]] = []
    for path, before, after, row in verified:
        mode = path.stat().st_mode
        fd, tmp_name = tempfile.mkstemp(prefix=".viewport-backfill-", dir=str(path.parent))
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(after)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp, mode)
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                tmp.unlink()
        landed = path.read_bytes()
        if _sha256(landed) != row["after_sha256"]:
            raise BackfillError("post-write digest mismatch: %s" % row["path"])
        applied.append(
            {
                "path": row["path"],
                "before_sha256": row["before_sha256"],
                "after_sha256": row["after_sha256"],
            }
        )

    return {
        "schema": SCHEMA,
        "mode": "apply",
        "base_head_sha": base,
        "viewport_tag": VIEWPORT_TAG,
        "applied_count": len(applied),
        "changes": applied,
    }


def _write_manifest(path: Path, plan: dict[str, Any]) -> None:
    path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="max missing pages selected by a dry-run (1..100)")
    parser.add_argument("--cursor", default="", help="exclusive lexicographic path cursor")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX, help="derived-page prefix; default p/")
    parser.add_argument("--manifest-out", type=Path, help="optional dry-run JSON manifest path")
    parser.add_argument("--apply", action="store_true", help="apply a previously reviewed manifest")
    parser.add_argument("--manifest", type=Path, help="reviewed dry-run manifest required by --apply")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.apply:
            if args.manifest is None:
                parser.error("--apply requires --manifest")
            result = apply_manifest(_load_manifest(args.manifest))
        else:
            if args.limit is None:
                parser.error("dry-run requires explicit --limit")
            result = build_plan(args.limit, args.cursor, args.prefix)
            if args.manifest_out is not None:
                _write_manifest(args.manifest_out, result)
    except BackfillError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
