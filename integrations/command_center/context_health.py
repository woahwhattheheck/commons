"""Opt-in all-source health for an existing context page.

The default context response and its revision stay byte-for-byte the caller's
page. This envelope is a separate object with its own revision.
"""
from __future__ import annotations

import hashlib
import json


def page_condition(page):
    """Name why this page is empty or reused. Item filters are not coverage."""
    counts = page.get("counts") or {}
    pagination = page.get("pagination") or {}
    offset = pagination.get("offset") or 0
    if page.get("unchanged") is True:
        return "unchanged_page"
    if counts.get("inventory_records") == 0 and counts.get("inventory_sources") == 0:
        return "no_cached_records"
    if counts.get("matching_records") == 0:
        return "no_matches"
    if counts.get("page_records") == 0 and offset > 0:
        return "past_end"
    return "page"


def _revision(payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def envelope(page, summary_sources):
    """Bounded source portion from build_summary, including zero-item sources."""
    sources = summary_sources if isinstance(summary_sources, dict) else {}
    body = {
        "schema": "commons-context-source-health/v1",
        "scope": "all_cached_sources",
        "independent_of_item_filters": True,
        "page_condition": page_condition(page),
        "page_revision": page.get("revision"),
        "sources": {
            "total": sources.get("total"),
            "health_state": sources.get("health_state"),
            "freshness": {
                key: (sources.get(key) if key in sources else (sources.get("freshness") or {}).get(key))
                for key in ("fresh", "retained", "stale", "unknown")
            },
            "coverage_debt_count": sources.get("coverage_debt_count"),
            "coverage_debt": sources.get("coverage_debt") or [],
            "coverage_debt_omitted": sources.get("coverage_debt_omitted"),
        },
    }
    # build_summary flattens freshness onto sources as fresh/retained/stale/unknown.
    flat = {key: sources.get(key, 0) for key in ("fresh", "retained", "stale", "unknown")}
    body["sources"]["freshness"] = flat
    body["revision"] = _revision({key: value for key, value in body.items() if key != "revision"})
    return body


def with_source_health(center, page):
    """Attach summary source facts from the shared cached snapshot.

    Does not replace page['revision'] and does not read a provider.
    """
    summary = center.work_summary()
    attached = dict(page)
    attached["source_health_opt_in"] = envelope(page, summary.get("sources") or {})
    return attached
