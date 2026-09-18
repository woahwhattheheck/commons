#!/usr/bin/env python3
"""Fail-closed pull-request root-tree retention guard.

This module is executed only from the repository default branch by the existing
``pull_request_target`` listener.  It reads commit and non-recursive root-tree
metadata for the exact event base/head SHAs and never checks out or executes PR
head content.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_MIN_BASE_ROOTS = 100
_MAX_ABSOLUTE_REMOVALS = 25
_MAX_REMOVAL_FRACTION = 0.10
_SAMPLE_LIMIT = 20


class GuardError(RuntimeError):
    """Stable fail-closed error for malformed or unavailable metadata."""


@dataclass(frozen=True)
class RootEntry:
    path: str
    mode: str
    kind: str
    sha: str


JsonGet = Callable[[str], Any]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise GuardError(f"{name} must be object")
    return value


def _require_text(value: Any, name: str, *, maximum: int = 512) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise GuardError(f"{name} must be non-empty text <= {maximum} chars")
    return value


def _require_sha(value: Any, name: str) -> str:
    value = _require_text(value, name, maximum=40)
    if not _SHA_RE.fullmatch(value):
        raise GuardError(f"{name} must be lowercase 40-hex git SHA")
    return value


def _repo_name(value: Any, name: str) -> str:
    repo = _require_dict(value, name)
    full_name = _require_text(repo.get("full_name"), f"{name}.full_name", maximum=240)
    if full_name.count("/") != 1 or any(part in {"", ".", ".."} for part in full_name.split("/")):
        raise GuardError(f"{name}.full_name must be owner/repo")
    return full_name


def _parse_event(event: Any) -> tuple[str, str, str, str]:
    event = _require_dict(event, "event")
    event_repo = _repo_name(event.get("repository"), "event.repository")
    pr = _require_dict(event.get("pull_request"), "event.pull_request")
    base = _require_dict(pr.get("base"), "event.pull_request.base")
    head = _require_dict(pr.get("head"), "event.pull_request.head")
    base_repo = _repo_name(base.get("repo"), "event.pull_request.base.repo")
    head_repo = _repo_name(head.get("repo"), "event.pull_request.head.repo")
    if base_repo != event_repo:
        raise GuardError("event base repository does not match event repository")
    return (
        base_repo,
        head_repo,
        _require_sha(base.get("sha"), "event.base.sha"),
        _require_sha(head.get("sha"), "event.head.sha"),
    )


def _commit_tree_sha(payload: Any, requested_sha: str, name: str) -> str:
    payload = _require_dict(payload, name)
    observed = _require_sha(payload.get("sha"), f"{name}.sha")
    if observed != requested_sha:
        raise GuardError(f"{name}.sha mismatch")
    tree = _require_dict(payload.get("tree"), f"{name}.tree")
    return _require_sha(tree.get("sha"), f"{name}.tree.sha")


def _parse_root_tree(payload: Any, expected_sha: str, name: str) -> dict[str, RootEntry]:
    payload = _require_dict(payload, name)
    observed = _require_sha(payload.get("sha"), f"{name}.sha")
    if observed != expected_sha:
        raise GuardError(f"{name}.sha mismatch")
    if payload.get("truncated") is not False:
        raise GuardError(f"{name}.truncated must be false")
    raw = payload.get("tree")
    if type(raw) is not list:
        raise GuardError(f"{name}.tree must be array")

    entries: dict[str, RootEntry] = {}
    for index, item in enumerate(raw):
        item = _require_dict(item, f"{name}.tree[{index}]")
        path = _require_text(item.get("path"), f"{name}.tree[{index}].path", maximum=4096)
        if "/" in path or path in {".", ".."}:
            raise GuardError(f"{name}.tree[{index}].path must be one root component")
        if path in entries:
            raise GuardError(f"{name}.tree contains duplicate path {path!r}")
        mode = _require_text(item.get("mode"), f"{name}.tree[{index}].mode", maximum=16)
        kind = _require_text(item.get("type"), f"{name}.tree[{index}].type", maximum=16)
        sha = _require_sha(item.get("sha"), f"{name}.tree[{index}].sha")
        if kind not in {"blob", "tree", "commit"}:
            raise GuardError(f"{name}.tree[{index}].type unsupported")
        entries[path] = RootEntry(path=path, mode=mode, kind=kind, sha=sha)
    return entries


def evaluate(base: Mapping[str, RootEntry], head: Mapping[str, RootEntry]) -> dict[str, Any]:
    base_paths = set(base)
    head_paths = set(head)
    removed = sorted(base_paths - head_paths)
    added = sorted(head_paths - base_paths)
    shared = sorted(base_paths & head_paths)
    tree_to_non_tree = sorted(
        path for path in shared if base[path].kind == "tree" and head[path].kind != "tree"
    )

    removed_count = len(removed)
    base_count = len(base)
    removal_fraction = (removed_count / base_count) if base_count else 0.0
    reasons: list[str] = []
    if (
        base_count >= _MIN_BASE_ROOTS
        and removed_count > _MAX_ABSOLUTE_REMOVALS
        and removal_fraction > _MAX_REMOVAL_FRACTION
    ):
        reasons.append("mass_root_deletion")
    if tree_to_non_tree:
        reasons.append("root_tree_retyped_non_tree")

    return {
        "schema": "commons.pr-root-tree-preservation/v1",
        "status": "FAIL" if reasons else "PASS",
        "base_root_count": base_count,
        "head_root_count": len(head),
        "removed_root_count": removed_count,
        "added_root_count": len(added),
        "removal_fraction_ppm": (
            (removed_count * 1_000_000) // base_count if base_count else 0
        ),
        "reasons": reasons,
        "removed_sample": removed[:_SAMPLE_LIMIT],
        "added_sample": added[:_SAMPLE_LIMIT],
        "tree_to_non_tree_sample": tree_to_non_tree[:_SAMPLE_LIMIT],
    }


def inspect(
    base_repo: str,
    head_repo: str,
    base_sha: str,
    head_sha: str,
    get_json: JsonGet,
) -> dict[str, Any]:
    base_commit = get_json(f"/repos/{base_repo}/git/commits/{base_sha}")
    head_commit = get_json(f"/repos/{head_repo}/git/commits/{head_sha}")
    base_tree_sha = _commit_tree_sha(base_commit, base_sha, "base_commit")
    head_tree_sha = _commit_tree_sha(head_commit, head_sha, "head_commit")

    base_tree_payload = get_json(f"/repos/{base_repo}/git/trees/{base_tree_sha}")
    head_tree_payload = get_json(f"/repos/{head_repo}/git/trees/{head_tree_sha}")
    base = _parse_root_tree(base_tree_payload, base_tree_sha, "base_tree")
    head = _parse_root_tree(head_tree_payload, head_tree_sha, "head_tree")
    result = evaluate(base, head)
    result.update(
        {
            "repository": base_repo,
            "head_repository": head_repo,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "base_tree_sha": base_tree_sha,
            "head_tree_sha": head_tree_sha,
        }
    )
    return result


def _http_getter(api_url: str, token: str) -> JsonGet:
    api_url = api_url.rstrip("/")
    if not token:
        raise GuardError("GITHUB_TOKEN is required")

    calls = 0

    def get_json(path: str) -> Any:
        nonlocal calls
        calls += 1
        if calls > 4:
            raise GuardError("metadata request budget exceeded")
        if not path.startswith("/repos/"):
            raise GuardError("unexpected API path")
        request = urllib.request.Request(
            api_url + path,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "commons-pr-root-tree-preservation",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                if getattr(response, "status", 200) != 200:
                    raise GuardError(f"GitHub metadata HTTP {response.status}")
                raw = response.read(8 * 1024 * 1024 + 1)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            raise GuardError(f"GitHub metadata request failed: {exc}") from exc
        if len(raw) > 8 * 1024 * 1024:
            raise GuardError("GitHub metadata response exceeds limit")
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise GuardError("GitHub metadata response is not valid JSON") from exc

    return get_json


def _load_event(path: str) -> Any:
    try:
        with open(path, "rb") as handle:
            raw = handle.read(2 * 1024 * 1024 + 1)
    except OSError as exc:
        raise GuardError(f"cannot read event payload: {exc}") from exc
    if len(raw) > 2 * 1024 * 1024:
        raise GuardError("event payload exceeds limit")
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GuardError("event payload is not valid JSON") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_PATH"))
    args = parser.parse_args(argv)
    if not args.event:
        print(_canonical_json({"schema": "commons.pr-root-tree-preservation/v1", "status": "ERROR", "reason": "GITHUB_EVENT_PATH missing"}))
        return 2
    try:
        base_repo, head_repo, base_sha, head_sha = _parse_event(_load_event(args.event))
        getter = _http_getter(
            os.environ.get("GITHUB_API_URL", "https://api.github.com"),
            os.environ.get("GITHUB_TOKEN", ""),
        )
        result = inspect(base_repo, head_repo, base_sha, head_sha, getter)
        print(_canonical_json(result))
        return 0 if result["status"] == "PASS" else 1
    except GuardError as exc:
        print(
            _canonical_json(
                {
                    "schema": "commons.pr-root-tree-preservation/v1",
                    "status": "ERROR",
                    "reason": str(exc),
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
