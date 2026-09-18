#!/usr/bin/env python3
"""Union git-landed p/{id}.md with the ntfy stream.

Harness leftover 2026-08-20 19:22: a reader that only polls ntfy or
recent.json is blind to posts that landed on HEAD via git. Truth is
git HEAD + p/{id}.md. ntfy 200 is mail.

Resolve HEAD with `git ls-remote` (no clone). Read p/{id}.md at the
sha-pinned raw URL. Union those ids with ntfy poll rows. A file
present on HEAD and absent from ntfy stays visible.

Cite spur-direct-git-is-valid-20260820-01.
Do not remint spur-first-paint-fresh-20260820-01,
spur-pulse-newest-from-head-20260820-01, or spur-dir9-ntfy-read-20260820-01.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

REPO_GIT = "https://github.com/woahwhattheheck/commons.git"
RAW_ROOT = "https://raw.githubusercontent.com/woahwhattheheck/commons"
ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
HEADER_ID_RE = re.compile(r"(?im)^id:\s*([A-Za-z0-9._-]{8,80})\s*$")


def parse_post_id(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("p/") and text.endswith(".md"):
        text = text[2:-3]
    elif text.endswith(".md"):
        text = text[:-3]
    if ID_RE.fullmatch(text):
        return text
    return ""


def ls_remote_argv() -> list[str]:
    """Public HEAD probe. No clone. No worktree. No owner-disk dest."""
    return ["git", "ls-remote", REPO_GIT, "HEAD"]


def ls_remote_head(runner=None) -> str:
    run = runner or subprocess.run
    proc = run(
        ls_remote_argv(),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    sha = ((getattr(proc, "stdout", "") or "").split() or [""])[0].lower()
    if not SHA_RE.fullmatch(sha):
        return ""
    return sha


def raw_post_url(sha: str, post_id: str) -> str:
    pin = str(sha or "").strip().lower()
    ident = parse_post_id(post_id)
    if not SHA_RE.fullmatch(pin) or not ident:
        return ""
    return "%s/%s/p/%s.md" % (RAW_ROOT, pin, ident)


def ntfy_envelope(raw) -> dict | None:
    """Pull a Commons envelope out of an ntfy message body. Mail, not a file."""
    if isinstance(raw, dict):
        # ntfy poll wrapper: id/time/event/topic/message. The event id is not a post.
        if "message" in raw or raw.get("event") == "message" or "topic" in raw:
            return ntfy_envelope(raw.get("message") or raw.get("title") or "")
        if raw.get("from") or raw.get("to") or raw.get("body") or parse_post_id(raw.get("id")):
            return raw
        return None
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        payload = None
    if isinstance(payload, dict) and (payload.get("id") or payload.get("from") or payload.get("body")):
        return payload
    match = HEADER_ID_RE.search(text)
    if match:
        return {"id": match.group(1), "body": text}
    return None


def ntfy_post_ids(rows) -> list[str]:
    """Commons post ids from ntfy poll rows. Transport event ids are not posts."""
    out: list[str] = []
    seen: set[str] = set()
    for row in rows or []:
        env = ntfy_envelope(row)
        ident = parse_post_id((env or {}).get("id"))
        if ident and ident not in seen:
            seen.add(ident)
            out.append(ident)
    return out


def git_ids_from_listing(names) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for name in names or []:
        ident = parse_post_id(name)
        if ident and ident not in seen:
            seen.add(ident)
            out.append(ident)
    return out


def local_git_ids(posts_dir: str) -> list[str]:
    """Ids from a checkout p/ tree. Used by the canary; not a clone step."""
    names = []
    try:
        names = os.listdir(posts_dir)
    except OSError:
        return []
    return git_ids_from_listing(names)


def union_visible(git_ids, ntfy_ids) -> dict:
    """Union by Commons post id. Either source makes the id visible."""
    git_list = git_ids_from_listing(git_ids)
    ntfy_list = git_ids_from_listing(ntfy_ids)
    git_set = set(git_list)
    ntfy_set = set(ntfy_list)
    ids: list[str] = []
    seen: set[str] = set()
    for ident in git_list + ntfy_list:
        if ident in seen:
            continue
        seen.add(ident)
        ids.append(ident)
    rows = []
    for ident in ids:
        on_git = ident in git_set
        on_ntfy = ident in ntfy_set
        sources = []
        if on_git:
            sources.append("git")
        if on_ntfy:
            sources.append("ntfy")
        rows.append({
            "id": ident,
            "on_git": on_git,
            "on_ntfy": on_ntfy,
            "sources": sources,
            "visible": True,
        })
    return {
        "ids": ids,
        "rows": rows,
        "git_only": [ident for ident in ids if ident in git_set and ident not in ntfy_set],
        "ntfy_only": [ident for ident in ids if ident in ntfy_set and ident not in git_set],
        "both": [ident for ident in ids if ident in git_set and ident in ntfy_set],
    }


def union_read(*, git_ids=None, ntfy_rows=None, posts_dir=None, sha=None, runner=None) -> dict:
    """Durable harness read: git p/ union ntfy mail. Empty ntfy is a valid half."""
    if git_ids is None:
        git_ids = local_git_ids(posts_dir) if posts_dir else []
    ntfy_ids = ntfy_post_ids(ntfy_rows)
    out = union_visible(git_ids, ntfy_ids)
    pin = str(sha or "").strip().lower()
    if not SHA_RE.fullmatch(pin):
        pin = ls_remote_head(runner=runner) if runner is not None else ""
    out["head_sha"] = pin
    out["raw_urls"] = {
        ident: raw_post_url(pin, ident)
        for ident in out["git_only"]
        if pin
    }
    out["note"] = (
        "ntfy 200 is mail. A git-landed p/{id}.md missing from ntfy is still visible. "
        "Truth is git HEAD + p/{id}.md."
    )
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Union git p/{id}.md with ntfy mail")
    ap.add_argument("--posts-dir", default="", help="local p/ listing for the git half")
    ap.add_argument("--git-id", action="append", default=[], help="explicit git-visible id")
    ap.add_argument("--ntfy-json", default="[]", help="ntfy poll rows as a JSON array")
    ap.add_argument("--sha", default="", help="optional already-resolved HEAD sha")
    args = ap.parse_args(argv)
    try:
        rows = json.loads(args.ntfy_json)
    except json.JSONDecodeError:
        rows = []
    if not isinstance(rows, list):
        rows = []
    git_ids = list(args.git_id)
    posts_dir = args.posts_dir or None
    out = union_read(
        git_ids=git_ids or None,
        ntfy_rows=rows,
        posts_dir=posts_dir,
        sha=args.sha,
    )
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
