"""Trust, activity, occupancy, and funding evidence checks."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Any, Mapping, Sequence

from constants import (
    ACCEPTANCE_RE,
    FUNDING_RESTORATION_RE,
    FUNDING_WITHDRAWAL_RE,
    GITHUB_ITEM_RE,
    SPONSOR_RE,
    STRICT_CLAIM_RE,
    TRUSTED_ASSOCIATIONS,
    TRUSTED_SPONSOR_BOTS,
)
from models import validate_github_item_url


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        return None
    return stamp.astimezone(timezone.utc)


def iso(stamp: datetime) -> str:
    return stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def funding_authority(user: Mapping[str, Any], association: Any) -> bool:
    """Return whether one actor may authorize sponsor/amount/acceptance evidence."""

    login = str(user.get("login") or "").lower()
    normalized_association = str(association or "").upper()
    return (
        normalized_association in TRUSTED_ASSOCIATIONS
        or login in TRUSTED_SPONSOR_BOTS
    )


def trusted_comment(
    comment: Mapping[str, Any], issue_author: str | None = None
) -> bool:
    """Return whether a comment is authoritative for funded-work qualification.

    ``issue_author`` is retained only for call/API compatibility; being the issue
    author does not grant funding authority.
    """

    del issue_author
    user = comment.get("user") if isinstance(comment.get("user"), Mapping) else {}
    return funding_authority(user, comment.get("author_association"))


def canonical_text(issue: Mapping[str, Any], comments: Sequence[Mapping[str, Any]]) -> str:
    """Return only sponsor/maintainer-authoritative funding/acceptance prose."""

    issue_user = issue.get("user") if isinstance(issue.get("user"), Mapping) else {}
    chunks: list[str] = []
    if funding_authority(issue_user, issue.get("author_association")):
        chunks.extend((str(issue.get("title") or ""), str(issue.get("body") or "")))
    chunks.extend(
        str(comment.get("body") or "")
        for comment in comments
        if trusted_comment(comment)
    )
    return "\n".join(chunks)


def descriptive_issue_text(issue: Mapping[str, Any]) -> str:
    """Return issue-authored descriptive text independent of funding authority."""

    return "\n".join((str(issue.get("title") or ""), str(issue.get("body") or "")))


def amount_supported(text: str, amount: str, currency: str) -> bool:
    """Require an exact numeric currency token, not a prefix of a larger amount."""

    target = Decimal(amount)
    number = r"(?<![\d.,])(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)(?![\d.,])"
    symbols = {"USD": r"\$", "EUR": "€", "GBP": "£"}
    markers = [rf"\b{re.escape(currency)}\b"]
    if currency in symbols:
        markers.append(symbols[currency])
    for marker in markers:
        for pattern in (rf"{marker}\s*{number}", rf"{number}\s*{marker}"):
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                found = Decimal(match.group("value").replace(",", ""))
                if found == target:
                    return True
    return False


def _funding_directive(text: str) -> str | None:
    """Return the last explicit commercial-state directive in one authority event."""

    directives = [
        *((match.start(), "withdrawn") for match in FUNDING_WITHDRAWAL_RE.finditer(text)),
        *((match.start(), "restored") for match in FUNDING_RESTORATION_RE.finditer(text)),
    ]
    return max(directives, default=(0, None), key=lambda row: row[0])[1]


def authoritative_funding_state(
    issue: Mapping[str, Any],
    comments: Sequence[Mapping[str, Any]],
    amount: str,
    currency: str,
) -> str:
    """Resolve explicit funding withdrawal/restoration in authority-event order.

    Positive evidence remains cumulative for normal qualification, but an explicit
    trusted withdrawal blocks it. A later restoration can clear that block only
    when the same restoration event restates sponsor, exact amount, and acceptance
    evidence, preventing stale pre-withdrawal terms from silently reactivating.
    """

    state = "not_withdrawn"

    issue_user = issue.get("user") if isinstance(issue.get("user"), Mapping) else {}
    if funding_authority(issue_user, issue.get("author_association")):
        issue_text = "\n".join(
            (str(issue.get("title") or ""), str(issue.get("body") or ""))
        )
        directive = _funding_directive(issue_text)
        if directive == "withdrawn":
            state = "withdrawn"
        elif directive == "restored" and state == "withdrawn":
            if (
                SPONSOR_RE.search(issue_text)
                and amount_supported(issue_text, amount, currency)
                and ACCEPTANCE_RE.search(issue_text)
            ):
                state = "not_withdrawn"

    far_future = datetime.max.replace(tzinfo=timezone.utc)
    events: list[tuple[datetime, int, str]] = []
    for index, comment in enumerate(comments):
        if not trusted_comment(comment):
            continue
        stamp = (
            parse_timestamp(comment.get("updated_at"))
            or parse_timestamp(comment.get("created_at"))
            or far_future
        )
        events.append((stamp, index, str(comment.get("body") or "")))

    for _, _, text in sorted(events, key=lambda row: (row[0], row[1])):
        directive = _funding_directive(text)
        if directive == "withdrawn":
            state = "withdrawn"
        elif directive == "restored" and state == "withdrawn":
            if (
                SPONSOR_RE.search(text)
                and amount_supported(text, amount, currency)
                and ACCEPTANCE_RE.search(text)
            ):
                state = "not_withdrawn"

    return state


def visible_claimants(comments: Sequence[Mapping[str, Any]]) -> list[str]:
    claimants: set[str] = set()
    for comment in comments:
        if not STRICT_CLAIM_RE.search(str(comment.get("body") or "")):
            continue
        user = comment.get("user") if isinstance(comment.get("user"), Mapping) else {}
        claimants.add(str(user.get("login") or "unknown"))
    return sorted(claimants)


def active_competing_prs(timeline: Sequence[Mapping[str, Any]]) -> list[str]:
    urls: set[str] = set()
    for event in timeline:
        if event.get("event") != "cross-referenced":
            continue
        source = event.get("source") if isinstance(event.get("source"), Mapping) else {}
        issue = source.get("issue") if isinstance(source.get("issue"), Mapping) else {}
        if not isinstance(issue.get("pull_request"), Mapping):
            continue
        if str(issue.get("state") or "").lower() != "open":
            continue
        url = issue.get("html_url")
        if isinstance(url, str) and GITHUB_ITEM_RE.fullmatch(url):
            urls.add(validate_github_item_url(url))
    return sorted(urls)


def last_activity(
    issue: Mapping[str, Any], comments: Sequence[Mapping[str, Any]]
) -> datetime | None:
    """Return the newest timestamp allowed to refresh funded-work freshness.

    GitHub issue ``updated_at`` is intentionally excluded: arbitrary comments can
    advance it even when the sponsor or maintainer has done nothing. The immutable
    issue creation time is the baseline. After creation, only comments from actors
    already trusted for funding evidence may refresh the clock. Untrusted comments
    remain available to claim/occupancy and security checks elsewhere in the gate.
    """

    stamps = [parse_timestamp(issue.get("created_at"))]
    for comment in comments:
        if not trusted_comment(comment):
            continue
        stamps.extend(
            (parse_timestamp(comment.get("updated_at")), parse_timestamp(comment.get("created_at")))
        )
    real = [stamp for stamp in stamps if stamp is not None]
    return max(real) if real else None
