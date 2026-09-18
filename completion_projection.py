"""Stable completion markers for actionable UNSEATED board cards.

Durable p/{id}.md pages are history and are never rewritten when work finishes.
This module owns a separate, fail-closed projection input: a marker is valid only
when it binds an exact durable operation id, a canonical completed issue, and a
same-repository pull request merged to main that explicitly closes that issue.

The renderer may suppress only the actionable UNSEATED -> TABLE projection. A
missing, malformed, stale, or source-mismatched marker means "not proven done".
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

SCHEMA = "commons-completed-operation-v1"
STATE = "COMPLETED"
MARKER_DIR = "completion/operations"
ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
CLOSING_RE_TEMPLATE = (
    r"(?im)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+"
    r"(?:https://github\.com/woahwhattheheck/commons/issues/|"
    r"woahwhattheheck/commons)?#?%s\b"
)


class CompletionEvidenceError(ValueError):
    """Completion evidence is absent, ambiguous, or not strong enough."""


def _clean_id(operation_id: str) -> str:
    value = str(operation_id or "").strip()
    if not ID_RE.fullmatch(value):
        raise CompletionEvidenceError("invalid operation id")
    return value


def _git_blob_sha1(data: bytes) -> str:
    header = ("blob %d\0" % len(data)).encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def source_rel(operation_id: str) -> str:
    return "p/%s.md" % _clean_id(operation_id)


def marker_rel(operation_id: str) -> str:
    return "%s/%s.json" % (MARKER_DIR, _clean_id(operation_id))


def _source_blob(root: str | os.PathLike[str], operation_id: str) -> tuple[str, str]:
    rel = source_rel(operation_id)
    path = Path(root) / rel
    if not path.is_file():
        raise CompletionEvidenceError("durable source is absent")
    return rel, _git_blob_sha1(path.read_bytes())


def source_paths(root: str | os.PathLike[str]) -> list[str]:
    base = Path(root) / MARKER_DIR
    if not base.is_dir():
        return []
    return [
        str(path.relative_to(root)).replace(os.sep, "/")
        for path in sorted(base.glob("*.json"))
        if path.is_file()
    ]


def closing_keyword_mentions_issue(body: str, issue_number: int) -> bool:
    if not isinstance(issue_number, int) or isinstance(issue_number, bool) or issue_number < 1:
        return False
    return re.search(CLOSING_RE_TEMPLATE % issue_number, str(body or "")) is not None


def build_marker(
    root: str | os.PathLike[str],
    operation_id: str,
    issue: dict[str, Any],
    pull_request: dict[str, Any],
) -> dict[str, Any]:
    operation_id = _clean_id(operation_id)
    issue_number = issue.get("number")
    if not isinstance(issue_number, int) or isinstance(issue_number, bool) or issue_number < 1:
        raise CompletionEvidenceError("invalid issue number")
    if issue.get("state") != "closed" or issue.get("state_reason") != "completed":
        raise CompletionEvidenceError("issue is not canonically completed")
    closed_at = str(issue.get("closed_at") or "")
    if not closed_at:
        raise CompletionEvidenceError("completed issue lacks closed_at")

    pr_number = pull_request.get("number")
    if not isinstance(pr_number, int) or isinstance(pr_number, bool) or pr_number < 1:
        raise CompletionEvidenceError("invalid pull request number")
    if pull_request.get("merged") is not True:
        raise CompletionEvidenceError("pull request is not merged")
    base = pull_request.get("base") or {}
    if str(base.get("ref") or "") != "main":
        raise CompletionEvidenceError("pull request did not merge to main")
    merged_at = str(pull_request.get("merged_at") or "")
    merge_commit_sha = str(pull_request.get("merge_commit_sha") or "").lower()
    if not merged_at or not HEX40_RE.fullmatch(merge_commit_sha):
        raise CompletionEvidenceError("merged pull request lacks immutable merge evidence")
    if merged_at > closed_at:
        raise CompletionEvidenceError("merge happened after canonical completion")
    if not closing_keyword_mentions_issue(str(pull_request.get("body") or ""), issue_number):
        raise CompletionEvidenceError("pull request does not explicitly close canonical issue")

    rel, blob_sha1 = _source_blob(root, operation_id)
    issue_url = str(issue.get("html_url") or issue.get("url") or "")
    pr_url = str(pull_request.get("html_url") or pull_request.get("url") or "")
    return {
        "schema": SCHEMA,
        "state": STATE,
        "operation_id": operation_id,
        "issue": {
            "number": issue_number,
            "url": issue_url,
            "closed_at": closed_at,
            "state_reason": "completed",
        },
        "merge": {
            "pr_number": pr_number,
            "url": pr_url,
            "base": "main",
            "merged_at": merged_at,
            "merge_commit_sha": merge_commit_sha,
        },
        "source": {
            "path": rel,
            "blob_sha1": blob_sha1,
        },
    }


def write_marker(root: str | os.PathLike[str], marker: dict[str, Any]) -> str:
    operation_id = _clean_id(marker.get("operation_id"))
    if not marker_is_valid(root, marker):
        raise CompletionEvidenceError("refusing to write invalid completion marker")
    path = Path(root) / marker_rel(operation_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(marker, indent=2, sort_keys=True) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return "unchanged"
    path.write_text(text, encoding="utf-8")
    return "wrote"


def remove_marker(
    root: str | os.PathLike[str],
    operation_id: str,
    issue_number: int,
) -> bool:
    operation_id = _clean_id(operation_id)
    path = Path(root) / marker_rel(operation_id)
    if not path.is_file():
        return False
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    issue = row.get("issue") if isinstance(row, dict) else None
    if not isinstance(issue, dict) or issue.get("number") != issue_number:
        return False
    path.unlink()
    return True


def marker_is_valid(root: str | os.PathLike[str], row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    try:
        operation_id = _clean_id(row.get("operation_id"))
        issue = row.get("issue")
        merge = row.get("merge")
        source = row.get("source")
        if row.get("schema") != SCHEMA or row.get("state") != STATE:
            return False
        if not isinstance(issue, dict) or not isinstance(merge, dict) or not isinstance(source, dict):
            return False
        if issue.get("state_reason") != "completed":
            return False
        number = issue.get("number")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            return False
        if not str(issue.get("closed_at") or ""):
            return False
        if merge.get("base") != "main" or not str(merge.get("merged_at") or ""):
            return False
        if not HEX40_RE.fullmatch(str(merge.get("merge_commit_sha") or "").lower()):
            return False
        pr_number = merge.get("pr_number")
        if not isinstance(pr_number, int) or isinstance(pr_number, bool) or pr_number < 1:
            return False
        rel, blob_sha1 = _source_blob(root, operation_id)
        return source.get("path") == rel and source.get("blob_sha1") == blob_sha1
    except (CompletionEvidenceError, OSError, UnicodeError):
        return False


def completed_operation_ids(root: str | os.PathLike[str]) -> frozenset[str]:
    completed: set[str] = set()
    for rel in source_paths(root):
        path = Path(root) / rel
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if marker_is_valid(root, row):
            completed.add(str(row["operation_id"]))
    return frozenset(completed)


def is_completed_actionable(meta: dict[str, Any], completed_ids: set[str] | frozenset[str]) -> bool:
    return (
        str(meta.get("id") or "") in completed_ids
        and str(meta.get("from") or "").upper() == "UNSEATED"
        and str(meta.get("to") or "").upper() == "TABLE"
    )
