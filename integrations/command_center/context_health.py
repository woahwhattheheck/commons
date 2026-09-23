"""Optional context/source-health composition over one existing cached snapshot.

Reuse the native selector and summary source projection. No collector, second
store, per-query cache, provider call, dispatch or new access rule is introduced.
The ordinary context path is delegated unchanged when the option is absent.
"""
from __future__ import annotations

from datetime import datetime
import json
import time

from .context_view import build_index, select, _hash, _json
from .schema import CoreError
from .summary import MAX_ROWS, build_summary

SOURCE_HEALTH_PROPERTY = {
    "type": "boolean", "default": False,
    "description": "Include bounded all-cached-source freshness/coverage even on empty or no-match pages. Never refreshes a provider or proves that no work exists.",
}


def _health(work, index, result):
    # Match the existing context index's evaluation clock, not a second clock
    # or a separately fetched summary generation after a concurrent ingestion.
    now = datetime.fromisoformat(index["evaluated_at"].replace("Z", "+00:00"))
    sources = build_summary(work, now=now)["sources"]
    indexed = {row["source_id"]: row for row in index["sources"]}
    missing = [row["source_id"] for row in index["sources"] if row["missing"]]
    for row in sources["coverage_debt"]:
        source = indexed.get(row["id"], {})
        row["has_error"] = source.get("has_error", False)
        # Native summary.complete is a display boolean; keep its meaning and
        # expose the existing context projection's true/false/unknown beside it.
        row["complete_declared"] = source.get("coverage", {}).get("complete")
    if not sources["total"] or missing:
        coverage_state = "unknown_source_coverage"
    elif sources["coverage_debt_count"]:
        coverage_state = "degraded_or_incomplete_source_coverage"
    else:
        coverage_state = "fresh_declared_complete_sources"
    counts = result["counts"]
    if counts["matching_records"]:
        selection_state = "cached_matches_on_page" if counts["page_records"] else "past_end_of_cached_matches"
    else:
        selection_state = "no_cached_records" if not counts["inventory_records"] else "no_matching_cached_records"
    selected_source = result["filters"]["source"]
    return {
        "scope": "all_cached_sources", "filtered_by_item_selection": False,
        "basis": "existing_summary_sources_same_cached_snapshot",
        "coverage_state": coverage_state, "selection_state": selection_state,
        "sources": sources,
        "has_error_sources": sum(row["has_error"] for row in index["sources"]),
        "missing_source_metadata": {
            "count": len(missing), "source_ids": missing[:MAX_ROWS],
            "omitted": max(0, len(missing) - MAX_ROWS),
        },
        "selected_source_metadata_known": (
            selected_source in indexed and not indexed[selected_source]["missing"]
            if selected_source else None
        ),
        "summary_endpoint": "/api/summary",
        "note": "Empty and no-match results describe cached observations, not absence of provider work. Fresh/complete is a source declaration, not independent proof. Health covers all cached sources regardless of item filters; an unknown selected source remains unknown.",
    }


def read_context(center, *, source_health=False, **selection):
    """Equipment/HTTP adapter; False preserves the existing core call exactly.

    The opt-in path uses the core's existing lock, shared snapshot and index
    cache. Both projections are made while holding that lock; there is no
    additional store read or refresh and no separate health-cache lifecycle.
    """
    if type(source_health) is not bool:
        raise CoreError(400, "Context source_health must be a boolean.")
    if not source_health:
        return center.work_context(**selection)
    if_revision = selection.pop("if_revision", None)
    if if_revision is not None and (not isinstance(if_revision, str) or len(if_revision) > 64):
        raise CoreError(400, "Invalid context revision.")
    started = time.monotonic()
    with center._summary_lock:
        work, cache = center._shared_work_snapshot_locked()
        cached = center._context_index_cache
        rebuilt = cached is None or cached["work"] is not work
        if rebuilt:
            cached = {"work": work, "index": build_index(work)}
            center._context_index_cache = cached
        try:
            # Always obtain the full selected page first. A legacy revision may
            # not suppress items before the health-aware revision is compared.
            result = select(cached["index"], **selection)
        except ValueError as exc:
            raise CoreError(400, str(exc)) from None
        health = _health(work, cached["index"], result)
        revision = _hash({"context_revision": result["revision"],
                          "extension": "context-source-health/v1", "source_health": health})
        unchanged = if_revision == revision
        result["revision"] = revision
        result["unchanged"] = unchanged
        result["source_health"] = health
        if unchanged:
            result["items"] = []
            result["counts"]["returned_records"] = 0
            result["omissions"]["unchanged_records"] = result["counts"]["page_records"]
        result["cache"] = cache
        result["telemetry"] = {
            "projection_ms": round((time.monotonic() - started) * 1000, 2),
            "records_examined": len(work.get("items", [])) * (2 if rebuilt else 1),
            "source_health_projection": "existing_summary",
        }
        # Do not let callers mutate either shared index or source observations.
        return json.loads(_json(result))
