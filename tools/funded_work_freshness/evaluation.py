"""Trust, activity, occupancy, and funding evidence checks."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Any, Mapping, Sequence

from constants import GITHUB_ITEM_RE, STRICT_CLAIM_RE, TRUSTED_ASSOCIATIONS, TRUSTED_SPONSOR_BOTS
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


def trusted_comment(comment: Mapping[str, Any], issue_author: str | None) -> bool:
    association = str(comment.get("author_association") or "").upper()
    user = comment.get("user") if isinstance(comment.get("user"), Mapping) else {}
    login = str(user.get("login") or "").lower()
    return (
        association in TRUSTED_ASSOCIATIONS
        or (issue_author is not None and login == issue_author.lower())
        or login in TRUSTED_SPONSOR_BOTS
    )


def canonical_text(issue: Mapping[str, Any], comments: Sequence[Mapping[str, Any]]) -> str:
    """Return only canonical/trusted prose for sponsor and criteria decisions."""

    issue_user = issue.get("user") if isinstance(issue.get("user"), Mapping) else {}
    issue_author = str(issue_user.get("login")) if issue_user.get("login") else None
    chunks = [str(issue.get("title") or ""), str(issue.get("body") or "")]
    chunks.extend(
        str(comment.get("body") or "")
        for comment in comments
        if trusted_comment(comment, issue_author)
    )
    return "\n".join(chunks)


def amount_supported(text: str, amount: str, currency: str) -> bool:
    normalized_text = re.sub(r"(?<=\d),(?=\d)", "", text).lower()
    amount_decimal = Decimal(amount)
    forms = {amount, format(amount_decimal, "f")}
    if amount_decimal == amount_decimal.to_integral_value():
        forms.add(str(int(amount_decimal)))
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    currency_forms = {currency.lower()}
    if currency in symbols:
        currency_forms.add(symbols[currency])
    for form in forms:
        escaped = re.escape(form)
        for marker in currency_forms:
            marker_escaped = re.escape(marker)
            if re.search(
                rf"(?:{marker_escaped}\s*{escaped}|{escaped}\s*{marker_escaped})",
                normalized_text,
            ):
                return True
    return False


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
    stamps = [parse_timestamp(issue.get("updated_at")), parse_timestamp(issue.get("created_at"))]
    for comment in comments:
        stamps.extend(
            (parse_timestamp(comment.get("updated_at")), parse_timestamp(comment.get("created_at")))
        )
    real = [stamp for stamp in stamps if stamp is not None]
    return max(real) if real else None
