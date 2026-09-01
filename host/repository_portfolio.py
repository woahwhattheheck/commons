#!/usr/bin/env python3
"""Validate the public-safe Commons repository portfolio projection.

The projection is a read-only routing aid.  It keeps public repository heads
exact while reducing private repositories to aggregate capacity.  A mirror is
CURRENT only when its recorded source is the canonical head; any positive or
unknown gap fails closed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA = "commons-repository-portfolio/v1"
HEX = set("0123456789abcdef")


class PortfolioError(ValueError):
    """The portfolio projection is incomplete or internally inconsistent."""


def is_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and set(value) <= HEX


def classify(repo: dict[str, Any], canonical_sha: str) -> str:
    role = repo.get("role")
    if role == "CANONICAL":
        if repo.get("head_sha") != canonical_sha:
            raise PortfolioError("canonical repository head differs from source_main_sha")
        return "CANONICAL"
    if role == "MIRROR":
        source_sha = repo.get("recorded_source_sha")
        gap = repo.get("commits_behind")
        if not is_sha(source_sha):
            return "MIRROR_UNVERIFIED"
        if not isinstance(gap, int) or isinstance(gap, bool) or gap < 0:
            return "MIRROR_UNVERIFIED"
        if source_sha == canonical_sha and gap == 0:
            return "CURRENT_MIRROR"
        if gap > 0:
            return "STALE_MIRROR"
        return "MIRROR_INCONSISTENT"
    if role in {"HELP_REFERENCE", "SPRINT_REFERENCE"}:
        return "REFERENCE"
    raise PortfolioError(f"unsupported public repository role: {role!r}")


def validate(snapshot: dict[str, Any]) -> dict[str, Any]:
    if snapshot.get("schema") != SCHEMA:
        raise PortfolioError(f"snapshot is not {SCHEMA}")
    canonical_sha = snapshot.get("source_main_sha")
    if not is_sha(canonical_sha):
        raise PortfolioError("source_main_sha is not a full Git SHA")

    repos = snapshot.get("public_repositories")
    if not isinstance(repos, list) or not repos:
        raise PortfolioError("public_repositories must be a non-empty list")
    names: set[str] = set()
    canonical = 0
    statuses: dict[str, int] = {}
    for repo in repos:
        if not isinstance(repo, dict):
            raise PortfolioError("public repository row must be an object")
        name = repo.get("full_name")
        if not isinstance(name, str) or "/" not in name or name in names:
            raise PortfolioError(f"invalid or duplicate public repository: {name!r}")
        names.add(name)
        if repo.get("visibility") != "public":
            raise PortfolioError(f"public row is not public: {name}")
        if not is_sha(repo.get("head_sha")):
            raise PortfolioError(f"public row lacks an exact head SHA: {name}")
        if repo.get("role") == "CANONICAL":
            canonical += 1
        want = classify(repo, canonical_sha)
        if repo.get("condition") != want:
            raise PortfolioError(f"condition drift for {name}: want {want}")
        statuses[want] = statuses.get(want, 0) + 1

    if canonical != 1:
        raise PortfolioError("portfolio must contain exactly one canonical repository")

    private = snapshot.get("private_aggregate")
    if not isinstance(private, dict):
        raise PortfolioError("private_aggregate must be an object")
    private_count = private.get("accessible_repository_count")
    if not isinstance(private_count, int) or isinstance(private_count, bool) or private_count < 0:
        raise PortfolioError("private accessible_repository_count must be a non-negative integer")
    forbidden = {"full_name", "head_sha", "default_branch", "commit_title", "url"}
    leaked = sorted(forbidden.intersection(private))
    if leaked:
        raise PortfolioError("private aggregate leaks repository detail: " + ", ".join(leaked))
    if private.get("details_persisted") is not False:
        raise PortfolioError("private details_persisted must be false")

    summary = snapshot.get("summary")
    expected = {
        "accessible_repositories": len(repos) + private_count,
        "public_repositories": len(repos),
        "private_repositories": private_count,
        "canonical_repositories": statuses.get("CANONICAL", 0),
        "current_mirrors": statuses.get("CURRENT_MIRROR", 0),
        "stale_mirrors": statuses.get("STALE_MIRROR", 0),
        "unverified_mirrors": statuses.get("MIRROR_UNVERIFIED", 0)
        + statuses.get("MIRROR_INCONSISTENT", 0),
        "reference_repositories": statuses.get("REFERENCE", 0),
    }
    if summary != expected:
        raise PortfolioError(f"summary drift: want {expected!r}")
    return expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args(argv)
    try:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        summary = validate(snapshot)
    except (OSError, json.JSONDecodeError, PortfolioError) as exc:
        print(f"repository-portfolio: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
