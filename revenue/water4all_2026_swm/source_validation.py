"""Official-source validation for the Water4All readiness compiler."""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Optional, Set, Tuple

from .common import (
    FUTURE_SKEW_SECONDS,
    REQUIRED_SOURCE_CLASSES,
    SOURCE_CLASSES,
    SOURCE_MAX_AGE_SECONDS,
    ReadinessError,
    _expect_bool,
    _expect_dict,
    _expect_hex,
    _expect_id,
    _expect_int,
    _expect_list,
    _expect_str,
    _https_url,
    _reason,
    format_time,
    parse_time,
    sha256_hex,
    source_fact_commitment,
    _HEX64,
)

def _validate_sources(
    raw_sources: Any,
    evaluated_at: _dt.datetime,
    current_mode: bool,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str], Optional[str], str]:
    sources = _expect_list(raw_sources, "$.official_sources")
    if not sources:
        raise ReadinessError("$.official_sources must not be empty")
    normalized: List[Dict[str, Any]] = []
    reasons: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    classes: Dict[str, int] = {}

    for index, raw in enumerate(sources):
        path = "$.official_sources[%d]" % index
        source = _expect_dict(raw, path)
        source_id = _expect_id(source.get("source_id"), path + ".source_id")
        if source_id in seen_ids:
            raise ReadinessError("duplicate source_id: %s" % source_id)
        seen_ids.add(source_id)
        authority_class = _expect_str(source.get("authority_class"), path + ".authority_class")
        if authority_class not in SOURCE_CLASSES:
            raise ReadinessError("unsupported source class: %s" % authority_class)
        classes[authority_class] = classes.get(authority_class, 0) + 1
        if classes[authority_class] > 1:
            reasons.append(_reason("DUPLICATE_SOURCE_CLASS", "more than one current source claims class %s" % authority_class, [source_id]))
        source_url = _https_url(source.get("source_url"), path + ".source_url")
        version = _expect_str(source.get("version"), path + ".version")
        observed_at_dt = parse_time(source.get("observed_at"), path + ".observed_at")
        observed_at = format_time(observed_at_dt)
        published_raw = source.get("published_at")
        published_at = None if published_raw is None else format_time(parse_time(published_raw, path + ".published_at"))
        call_title = _expect_str(source.get("call_title"), path + ".call_title")
        preproposal = format_time(parse_time(source.get("preproposal_deadline_at"), path + ".preproposal_deadline_at"))
        full_proposal = format_time(parse_time(source.get("full_proposal_deadline_at"), path + ".full_proposal_deadline_at"))
        budget = _expect_int(source.get("budget_eur_cents"), path + ".budget_eur_cents", 0)
        complete = _expect_bool(source.get("complete"), path + ".complete")
        declared_current = _expect_bool(source.get("declared_current"), path + ".declared_current")
        commitment = _expect_hex(source.get("fact_commitment"), path + ".fact_commitment", _HEX64)

        candidate = {
            "source_id": source_id,
            "authority_class": authority_class,
            "source_url": source_url,
            "version": version,
            "observed_at": observed_at,
            "published_at": published_at,
            "call_title": call_title,
            "preproposal_deadline_at": preproposal,
            "full_proposal_deadline_at": full_proposal,
            "budget_eur_cents": budget,
            "complete": complete,
            "declared_current": declared_current,
            "fact_commitment": commitment,
        }
        expected_commitment = source_fact_commitment(candidate)
        if commitment != expected_commitment:
            reasons.append(_reason("SOURCE_FACT_COMMITMENT_MISMATCH", "source fact commitment does not bind the supplied generation", [source_id]))
        if observed_at_dt > evaluated_at + _dt.timedelta(seconds=FUTURE_SKEW_SECONDS):
            reasons.append(_reason("SOURCE_OBSERVED_IN_FUTURE", "source observation is beyond the allowed future skew", [source_id]))
        if current_mode and evaluated_at - observed_at_dt > _dt.timedelta(seconds=SOURCE_MAX_AGE_SECONDS):
            reasons.append(_reason("SOURCE_OBSERVATION_STALE", "source observation exceeds the currentness window", [source_id]))
        if not complete:
            reasons.append(_reason("SOURCE_INCOMPLETE", "official source generation is not complete", [source_id]))
        if not declared_current:
            reasons.append(_reason("SOURCE_NOT_DECLARED_CURRENT", "official source generation is not declared current", [source_id]))
        normalized.append(candidate)

    for required in sorted(REQUIRED_SOURCE_CLASSES):
        if classes.get(required, 0) == 0:
            reasons.append(_reason("REQUIRED_SOURCE_MISSING", "required official source class is absent: %s" % required))

    trustworthy = [
        source
        for source in normalized
        if source["authority_class"] in REQUIRED_SOURCE_CLASSES
        and source["complete"]
        and source["declared_current"]
        and source["fact_commitment"] == source_fact_commitment(source)
        and parse_time(source["observed_at"], "source.observed_at") <= evaluated_at + _dt.timedelta(seconds=FUTURE_SKEW_SECONDS)
        and (not current_mode or evaluated_at - parse_time(source["observed_at"], "source.observed_at") <= _dt.timedelta(seconds=SOURCE_MAX_AGE_SECONDS))
    ]
    deadlines = sorted(set(source["preproposal_deadline_at"] for source in trustworthy))
    planning_deadline = min(deadlines) if deadlines else None
    controlling_deadline = deadlines[0] if len(deadlines) == 1 and REQUIRED_SOURCE_CLASSES.issubset(set(source["authority_class"] for source in trustworthy)) else None
    if len(deadlines) > 1:
        refs = [source["source_id"] for source in trustworthy]
        reasons.append(
            _reason(
                "DEADLINE_SOURCE_CONFLICT",
                "current complete official sources disagree on the pre-proposal deadline; no controlling deadline is selected",
                refs,
            )
        )

    full_deadlines = sorted(set(source["full_proposal_deadline_at"] for source in trustworthy))
    if len(full_deadlines) > 1:
        reasons.append(
            _reason(
                "FULL_PROPOSAL_DEADLINE_CONFLICT",
                "current complete official sources disagree on the full-proposal deadline",
                [source["source_id"] for source in trustworthy],
            )
        )

    budgets = sorted(set(source["budget_eur_cents"] for source in trustworthy))
    if len(budgets) > 1:
        reasons.append(
            _reason(
                "CALL_BUDGET_SOURCE_CONFLICT",
                "current complete official sources disagree on the call budget",
                [source["source_id"] for source in trustworthy],
            )
        )

    normalized.sort(key=lambda item: (item["authority_class"], item["source_id"]))
    generation_digest = sha256_hex(normalized)
    return normalized, reasons, controlling_deadline, planning_deadline, generation_digest
