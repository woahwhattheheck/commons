"""Classify bounty issue snapshots so concurrent builders can avoid duplicate work."""

from __future__ import annotations

import re
from dataclasses import dataclass

READY = "READY"
OVERLAP_OPEN_PR = "OVERLAP_OPEN_PR"
SATISFIED_DEFAULT_BRANCH = "SATISFIED_DEFAULT_BRANCH"
ISSUE_CLOSED = "ISSUE_CLOSED"
NEEDS_REFRESH = "NEEDS_REFRESH"

_CLOSING_REF = re.compile(
    r"(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s*#(?P<number>\d+)\b"
)
_ISSUE_URL = re.compile(r"/issues/(?P<number>\d+)(?:\b|/|$)")


@dataclass(frozen=True)
class PullRequestEvidence:
    number: int
    state: str
    title: str = ""
    body: str = ""
    url: str = ""
    draft: bool = False
    merged: bool = False


@dataclass(frozen=True)
class CandidateEvidence:
    repository: str
    issue_number: int
    issue_state: str
    default_branch_sha: str | None = None
    default_branch_satisfied: bool | None = None
    pull_requests: tuple[PullRequestEvidence, ...] = ()


def _explicit_reference(pr: PullRequestEvidence, issue_number: int) -> bool:
    text = f"{pr.title}\n{pr.body}\n{pr.url}"
    return any(int(m.group("number")) == issue_number for m in _CLOSING_REF.finditer(text)) or any(
        int(m.group("number")) == issue_number for m in _ISSUE_URL.finditer(text)
    )


def classify(candidate: CandidateEvidence) -> dict:
    if candidate.issue_state.strip().lower() != "open":
        return _result(candidate, ISSUE_CLOSED)
    if candidate.default_branch_satisfied is True:
        return _result(candidate, SATISFIED_DEFAULT_BRANCH)

    overlaps = sorted(
        pr.number
        for pr in candidate.pull_requests
        if not pr.merged
        and pr.state.strip().lower() == "open"
        and _explicit_reference(pr, candidate.issue_number)
    )
    if overlaps:
        return _result(candidate, OVERLAP_OPEN_PR, overlaps)
    if candidate.default_branch_satisfied is None:
        return _result(candidate, NEEDS_REFRESH)
    return _result(candidate, READY)


def _result(candidate: CandidateEvidence, verdict: str, overlaps=()) -> dict:
    return {
        "repository": candidate.repository,
        "issue_number": candidate.issue_number,
        "default_branch_sha": candidate.default_branch_sha,
        "verdict": verdict,
        "overlapping_prs": list(overlaps),
    }
