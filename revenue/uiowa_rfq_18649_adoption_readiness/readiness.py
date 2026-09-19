#!/usr/bin/env python3
"""UIOWA-077 - Organizational AI adoption readiness.

Team-level capability assessment plus capability-development options mapped to
0-90 / 90-180 / 180+ day horizons.

Six design rules, enforced in code rather than promised in prose:

  1. ORGANIZATION, NOT INDIVIDUALS. Records are team-scoped. A record carrying
     an individual identity key is REJECTED, not quietly anonymised, so this
     instrument cannot be repurposed as a performance-review tool.
  2. THIN SIGNAL IS NOT A LOW RATING. A team below the contributor floor, or a
     dimension below the indicator floor, resolves to UNKNOWN - never to
     ABSENT, never to zero, never to a maturity level.
  3. UNKNOWN IS EXCLUDED FROM EVERY DENOMINATOR. Coverage is reported as plain
     counts. There is no composite score, no maturity rating, no peer
     percentile and no certification claim anywhere in the output.
  4. RECOLLECTION IS NOT A RECORD. An indicator whose only evidence is an
     interview statement cannot support ESTABLISHED; it is downgraded to
     EMERGING and the reason is recorded next to it.
  5. EVERY EFFORT FIGURE CARRIES ITS OWN BASIS. A staff-effort range is invalid
     without both `assumption_basis` (what the number assumes) and
     `validating_evidence` (the real data that would confirm or replace it).
     Nothing here is a measured University figure.
  6. YOU CANNOT PLAN TO FIX WHAT YOU HAVE NOT ESTABLISHED IS BROKEN. An UNKNOWN
     dimension produces an EVIDENCE REQUEST, never a development option.

Python 3 standard library only. No network access. Deterministic: no clock, no
RNG, sorted traversal, stable content digest.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys

# --------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------

STATES = ("ABSENT", "EMERGING", "ESTABLISHED")
UNKNOWN = "UNKNOWN"
HORIZONS = ("0-90", "90-180", "180+")
HORIZON_INDEX = {h: i for i, h in enumerate(HORIZONS)}
EVIDENCE_KINDS = ("artifact", "system_record", "interview_statement")
EFFORT_KINDS = ("one_time", "recurring")

DEFAULT_MIN_CONTRIBUTORS = 3
DEFAULT_MIN_INDICATORS = 2

# Keys that would make a record about a person. Presence of any one of these
# anywhere in a team record rejects the whole record. `team_id`, `team_label`
# and `contributor_count` are deliberately not in this set.
FORBIDDEN_IDENTITY_KEYS = frozenset({
    "email", "emails", "employee", "employee_id", "employee_name",
    "first_name", "full_name", "hawkid", "individual", "individual_id",
    "last_name", "netid", "person", "person_id", "person_name",
    "respondent", "respondents", "reviewer_name", "staff_name",
    "user_id", "username",
})

REQUIRED_EFFORT_FIELDS = (
    "value_low", "value_high", "unit", "effort_kind",
    "assumption_basis", "validating_evidence",
)

REQUIRED_OPTION_FIELDS = (
    "option_id", "addresses", "applies_when", "horizon", "capability_gained",
    "staff_effort", "dependencies", "observable_indicator",
)

# Words that would turn this into a rating product. Asserted against in tests.
BANNED_OUTPUT_KEYS = frozenset({
    "score", "scores", "rating", "ratings", "maturity", "maturity_level",
    "percentile", "peer_percentile", "grade", "rank", "certification",
    "compliant", "compliance_level",
})


def diag(severity, code, where, message, detail=None):
    """One diagnostic record. Diagnostics are output, not exceptions."""
    out = {"severity": severity, "code": code, "where": where, "message": message}
    if detail is not None:
        out["detail"] = detail
    return out


def _nonempty_str(value):
    return isinstance(value, str) and value.strip() != ""


def _is_int(value):
    # bool is a subclass of int; a boolean contributor count is a data error.
    return isinstance(value, int) and not isinstance(value, bool)


# --------------------------------------------------------------------------
# Rule 1 - individual identity scan
# --------------------------------------------------------------------------

def scan_identity_keys(node, path="record"):
    """Return every path in `node` whose key names an individual.

    Walks the whole tree. Returns sorted paths so output is stable.
    """
    found = []
    if isinstance(node, dict):
        for key in sorted(node, key=str):
            if str(key).strip().lower() in FORBIDDEN_IDENTITY_KEYS:
                found.append("%s.%s" % (path, key))
            found.extend(scan_identity_keys(node[key], "%s.%s" % (path, key)))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(scan_identity_keys(item, "%s[%d]" % (path, index)))
    return sorted(found)


# --------------------------------------------------------------------------
# Model loading
# --------------------------------------------------------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_indicator_model(obj):
    """Build the dimension/indicator index used by everything downstream."""
    diagnostics = []
    dimensions = {}
    order = []
    indicators = {}
    for entry in obj.get("dimensions", []):
        dim_id = entry.get("dimension_id")
        if not _nonempty_str(dim_id):
            diagnostics.append(diag("error", "dimension_missing_id", "indicators",
                                    "A dimension has no dimension_id and was skipped."))
            continue
        if dim_id in dimensions:
            diagnostics.append(diag("error", "dimension_duplicate", dim_id,
                                    "Duplicate dimension_id; the later definition was skipped."))
            continue
        own = []
        for ind in entry.get("indicators", []):
            ind_id = ind.get("indicator_id")
            if not _nonempty_str(ind_id):
                diagnostics.append(diag("error", "indicator_missing_id", dim_id,
                                        "An indicator has no indicator_id and was skipped."))
                continue
            if ind_id in indicators:
                diagnostics.append(diag("error", "indicator_duplicate", ind_id,
                                        "Duplicate indicator_id; the later definition was skipped."))
                continue
            record = dict(ind)
            record["dimension_id"] = dim_id
            indicators[ind_id] = record
            own.append(ind_id)
        dimensions[dim_id] = {
            "dimension_id": dim_id,
            "label": entry.get("label", dim_id),
            "intent": entry.get("intent", ""),
            "indicator_ids": own,
        }
        order.append(dim_id)
    if not order:
        diagnostics.append(diag("error", "model_empty", "indicators",
                                "The indicator model defines no usable dimensions."))
    return {"dimensions": dimensions, "order": order, "indicators": indicators,
            "recording_rule": obj.get("recording_rule", "")}, diagnostics


# --------------------------------------------------------------------------
# Rule 5 - effort figures must carry their basis
# --------------------------------------------------------------------------

def validate_effort(effort, where):
    """An effort range without both basis fields is not a usable number."""
    diagnostics = []
    if not isinstance(effort, dict):
        return [diag("error", "effort_not_object", where,
                     "staff_effort must be an object carrying its own assumptions.")]
    for field in REQUIRED_EFFORT_FIELDS:
        value = effort.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            diagnostics.append(diag(
                "error", "effort_field_missing", where,
                "staff_effort is missing required field '%s'. An effort figure "
                "without its basis cannot be published." % field))
    low, high = effort.get("value_low"), effort.get("value_high")
    if low is not None and not isinstance(low, (int, float)):
        diagnostics.append(diag("error", "effort_not_numeric", where,
                                "value_low must be a number."))
    if high is not None and not isinstance(high, (int, float)):
        diagnostics.append(diag("error", "effort_not_numeric", where,
                                "value_high must be a number."))
    if isinstance(low, (int, float)) and isinstance(high, (int, float)) and low > high:
        diagnostics.append(diag("error", "effort_range_inverted", where,
                                "value_low (%s) exceeds value_high (%s)." % (low, high)))
    kind = effort.get("effort_kind")
    if kind is not None and kind not in EFFORT_KINDS:
        diagnostics.append(diag(
            "error", "effort_kind_unknown", where,
            "effort_kind '%s' is not one of %s; one-time and recurring effort "
            "must stay distinguishable." % (kind, list(EFFORT_KINDS))))
    return diagnostics


def validate_option(option, model):
    """Structural completeness of one development option.

    The order's completion bar - capability gained, staff effort, dependencies,
    observable indicator - is enforced here, so an option missing any of the
    four cannot reach the plan.
    """
    diagnostics = []
    where = option.get("option_id") if _nonempty_str(option.get("option_id")) else "<unnamed option>"
    for field in REQUIRED_OPTION_FIELDS:
        if field not in option:
            diagnostics.append(diag("error", "option_field_missing", where,
                                    "Option is missing required field '%s'." % field))
    for field in ("capability_gained", "observable_indicator"):
        if field in option and not _nonempty_str(option.get(field)):
            diagnostics.append(diag("error", "option_field_empty", where,
                                    "Option field '%s' is present but empty." % field))
    horizon = option.get("horizon")
    if horizon is not None and horizon not in HORIZON_INDEX:
        diagnostics.append(diag("error", "option_horizon_unknown", where,
                                "horizon '%s' is not one of %s." % (horizon, list(HORIZONS))))
    addresses = option.get("addresses")
    if addresses is not None and addresses not in model["dimensions"]:
        diagnostics.append(diag("error", "option_dimension_unknown", where,
                                "addresses '%s' is not a defined dimension." % addresses))
    applies = option.get("applies_when")
    if applies is not None:
        if not isinstance(applies, list) or not applies:
            diagnostics.append(diag("error", "option_applies_when_invalid", where,
                                    "applies_when must be a non-empty list of capability states."))
        else:
            for state in applies:
                if state not in STATES:
                    diagnostics.append(diag(
                        "error", "option_applies_when_invalid", where,
                        "applies_when contains '%s'; only %s are selectable states. "
                        "UNKNOWN is never a trigger for a development option." % (state, list(STATES))))
    deps = option.get("dependencies")
    if deps is not None and not isinstance(deps, list):
        diagnostics.append(diag("error", "option_dependencies_invalid", where,
                                "dependencies must be a list (possibly empty)."))
    if "staff_effort" in option:
        diagnostics.extend(validate_effort(option.get("staff_effort"), where))
    return diagnostics


def load_catalog(obj, model):
    """Accept only structurally complete options; report the rest."""
    diagnostics = []
    accepted = {}
    rejected = []
    for option in obj.get("options", []):
        problems = validate_option(option, model)
        option_id = option.get("option_id")
        if problems:
            diagnostics.extend(problems)
            rejected.append({
                "option_id": option_id if _nonempty_str(option_id) else "<unnamed option>",
                "reasons": sorted({p["code"] for p in problems}),
            })
            continue
        if option_id in accepted:
            diagnostics.append(diag("error", "option_duplicate", option_id,
                                    "Duplicate option_id; the later definition was skipped."))
            rejected.append({"option_id": option_id, "reasons": ["option_duplicate"]})
            continue
        accepted[option_id] = option
    for option_id in sorted(accepted):
        for dep in accepted[option_id].get("dependencies", []):
            if dep not in accepted:
                diagnostics.append(diag(
                    "error", "missing_prerequisite", option_id,
                    "Depends on '%s', which is not an accepted option in this catalog." % dep,
                    detail=dep))
    for cycle in find_cycles(accepted):
        diagnostics.append(diag(
            "error", "dependency_cycle", " -> ".join(cycle),
            "These options depend on each other in a loop, so no order can satisfy them.",
            detail=list(cycle)))
    return accepted, rejected, diagnostics


def find_cycles(options):
    """Return dependency cycles as rotation-normalised tuples, sorted."""
    cycles = set()
    color = {}

    def visit(node, stack):
        color[node] = 1
        stack.append(node)
        for dep in sorted(options[node].get("dependencies", [])):
            if dep not in options:
                continue
            state = color.get(dep, 0)
            if state == 0:
                visit(dep, stack)
            elif state == 1:
                cut = stack.index(dep)
                cycle = tuple(stack[cut:])
                pivot = cycle.index(min(cycle))
                cycles.add(cycle[pivot:] + cycle[:pivot])
        stack.pop()
        color[node] = 2

    for node in sorted(options):
        if color.get(node, 0) == 0:
            visit(node, [])
    return sorted(cycles)


# --------------------------------------------------------------------------
# Team records
# --------------------------------------------------------------------------

def load_teams(obj, model):
    """Load team records. Hostile records are rejected with a reason, not dropped."""
    diagnostics = []
    accepted = []
    rejected = []
    for record in obj.get("teams", []):
        team_id = record.get("team_id")
        where = team_id if _nonempty_str(team_id) else "<unnamed team>"

        identity_hits = scan_identity_keys(record, where)
        if identity_hits:
            reason = diag(
                "error", "individual_identity_present", where,
                "Record carries individual identity fields. This instrument "
                "assesses organizational capability and must never rate a "
                "person, so the record is rejected rather than anonymised.",
                detail=identity_hits)
            diagnostics.append(reason)
            rejected.append({"team_id": where, "reasons": ["individual_identity_present"],
                             "detail": identity_hits})
            continue

        if not _nonempty_str(team_id):
            diagnostics.append(diag("error", "team_missing_id", where,
                                    "Record has no team_id."))
            rejected.append({"team_id": where, "reasons": ["team_missing_id"]})
            continue

        count = record.get("contributor_count")
        if not _is_int(count) or count < 0:
            diagnostics.append(diag(
                "error", "contributor_count_invalid", where,
                "contributor_count must be a non-negative integer; got %r. "
                "It is not inferred and it is not defaulted to zero." % (count,)))
            rejected.append({"team_id": where, "reasons": ["contributor_count_invalid"]})
            continue

        observations = []
        bad_observations = []
        raw = record.get("observations")
        if raw is None:
            raw = []
        if not isinstance(raw, list):
            diagnostics.append(diag("error", "observations_invalid", where,
                                    "observations must be a list."))
            rejected.append({"team_id": where, "reasons": ["observations_invalid"]})
            continue
        for index, obs in enumerate(raw):
            spot = "%s.observations[%d]" % (where, index)
            problems = []
            if not isinstance(obs, dict):
                problems.append("observation_not_object")
            else:
                ind_id = obs.get("indicator_id")
                if ind_id not in model["indicators"]:
                    problems.append("indicator_unknown")
                if obs.get("state") not in STATES:
                    problems.append("state_invalid")
                if obs.get("evidence_kind") not in EVIDENCE_KINDS:
                    problems.append("evidence_kind_invalid")
                if not _nonempty_str(obs.get("evidence_source")):
                    problems.append("evidence_source_missing")
            if problems:
                for code in problems:
                    diagnostics.append(diag(
                        "error", code, spot,
                        "Observation rejected (%s). A rejected observation is "
                        "absent evidence, which resolves to UNKNOWN - it never "
                        "becomes an ABSENT finding." % code))
                bad_observations.append({
                    "position": index,
                    "indicator_id": obs.get("indicator_id") if isinstance(obs, dict) else None,
                    "reasons": sorted(set(problems)),
                })
                continue
            observations.append({
                "indicator_id": obs["indicator_id"],
                "state": obs["state"],
                "evidence_kind": obs["evidence_kind"],
                "evidence_source": obs["evidence_source"].strip(),
            })

        seen = {}
        deduped = []
        for obs in observations:
            if obs["indicator_id"] in seen:
                diagnostics.append(diag(
                    "error", "observation_duplicate", where,
                    "Indicator '%s' observed more than once; the later "
                    "observation was rejected rather than merged." % obs["indicator_id"]))
                bad_observations.append({"position": None, "indicator_id": obs["indicator_id"],
                                         "reasons": ["observation_duplicate"]})
                continue
            seen[obs["indicator_id"]] = True
            deduped.append(obs)

        accepted.append({
            "team_id": team_id,
            "team_label": record.get("team_label", team_id),
            "contributor_count": count,
            "observations": sorted(deduped, key=lambda o: o["indicator_id"]),
            "rejected_observations": bad_observations,
        })
    accepted.sort(key=lambda t: t["team_id"])
    return accepted, rejected, diagnostics


# --------------------------------------------------------------------------
# Rules 2, 3, 4 - resolving a dimension
# --------------------------------------------------------------------------

def resolve_dimension(dimension, observations, contributor_count,
                      min_contributors, min_indicators):
    notes = []
    base = {
        "dimension_id": dimension["dimension_id"],
        "label": dimension["label"],
        "indicators_observed": sorted(o["indicator_id"] for o in observations),
        "indicators_defined": list(dimension["indicator_ids"]),
        "evidence_sources": sorted({o["evidence_source"] for o in observations}),
    }

    if contributor_count < min_contributors:
        base.update({
            "state": UNKNOWN,
            "reason": "insufficient_contributors",
            "reason_text": (
                "Signal comes from %d contributor(s); the floor for an "
                "organizational reading is %d. This is thin evidence, not a "
                "low capability." % (contributor_count, min_contributors)),
            "notes": notes,
        })
        return base

    if not observations:
        base.update({
            "state": UNKNOWN,
            "reason": "no_indicator_evidence",
            "reason_text": "No indicator for this dimension has supplied evidence.",
            "notes": notes,
        })
        return base

    if len(observations) < min_indicators:
        base.update({
            "state": UNKNOWN,
            "reason": "insufficient_indicator_coverage",
            "reason_text": (
                "%d of %d indicators observed; the floor for stating a capability "
                "state is %d." % (len(observations), len(dimension["indicator_ids"]),
                                  min_indicators)),
            "notes": notes,
        })
        return base

    effective = []
    for obs in sorted(observations, key=lambda o: o["indicator_id"]):
        state = obs["state"]
        if state == "ESTABLISHED" and obs["evidence_kind"] == "interview_statement":
            state = "EMERGING"
            notes.append(
                "%s: ESTABLISHED downgraded to EMERGING (recollection_only) - the "
                "only evidence is an interview statement, not a record."
                % obs["indicator_id"])
        effective.append(state)

    if all(s == "ESTABLISHED" for s in effective):
        state = "ESTABLISHED"
    elif all(s == "ABSENT" for s in effective):
        state = "ABSENT"
    else:
        state = "EMERGING"

    base.update({
        "state": state,
        "reason": "resolved_from_indicators",
        "reason_text": "Resolved from %d observed indicator(s)." % len(effective),
        "notes": notes,
    })
    return base


# --------------------------------------------------------------------------
# Rule 6 - options for established gaps, evidence requests for UNKNOWN
# --------------------------------------------------------------------------

def evidence_request(team, dimension_result, model, min_contributors):
    dimension = model["dimensions"][dimension_result["dimension_id"]]
    observed = set(dimension_result["indicators_observed"])
    outstanding = []
    for ind_id in dimension["indicator_ids"]:
        if ind_id in observed:
            continue
        ind = model["indicators"][ind_id]
        outstanding.append({
            "indicator_id": ind_id,
            "prompt": ind.get("prompt", ""),
            "artifact_request": ind.get("artifact_request", ""),
        })
    if dimension_result["reason"] == "insufficient_contributors":
        validating = (
            "Responses from at least %d contributors on this team, or an explicit "
            "record that the team is smaller than the floor so its reading stays "
            "UNKNOWN by design." % min_contributors)
    else:
        validating = ("The artifacts listed below, or a written statement that the "
                      "practice does not exist here.")
    return {
        "team_id": team["team_id"],
        "dimension_id": dimension_result["dimension_id"],
        "dimension_label": dimension_result["label"],
        "reason": dimension_result["reason"],
        "reason_text": dimension_result["reason_text"],
        "validating_evidence": validating,
        "outstanding_indicators": outstanding,
    }


def select_options(dimension_result, catalog):
    """Options for a dimension whose gap is established. Never for UNKNOWN."""
    state = dimension_result["state"]
    if state == UNKNOWN or state == "ESTABLISHED":
        return []
    chosen = []
    for option_id in sorted(catalog):
        option = catalog[option_id]
        if option["addresses"] != dimension_result["dimension_id"]:
            continue
        if state not in option["applies_when"]:
            continue
        chosen.append(option)
    return chosen


def check_dependencies(selected_ids, catalog):
    """Phase inversions and prerequisites left outside the plan."""
    findings = []
    selected = set(selected_ids)
    for option_id in sorted(selected):
        option = catalog[option_id]
        own = HORIZON_INDEX[option["horizon"]]
        for dep in sorted(option.get("dependencies", [])):
            if dep not in catalog:
                findings.append(diag(
                    "error", "missing_prerequisite", option_id,
                    "Prerequisite '%s' does not exist in the catalog." % dep, detail=dep))
                continue
            if dep not in selected:
                findings.append(diag(
                    "open_question", "prerequisite_not_in_plan", option_id,
                    "Prerequisite '%s' is not in this team's plan, because the "
                    "capability it builds is not a gap here. Confirm it is "
                    "genuinely already satisfied before scheduling '%s'."
                    % (dep, option_id), detail=dep))
                continue
            if HORIZON_INDEX[catalog[dep]["horizon"]] > own:
                findings.append(diag(
                    "error", "phase_inversion", option_id,
                    "Scheduled in %s but depends on '%s', which lands in %s. "
                    "No execution order satisfies this."
                    % (option["horizon"], dep, catalog[dep]["horizon"]), detail=dep))
    return findings


# --------------------------------------------------------------------------
# Assessment
# --------------------------------------------------------------------------

def assess(teams_obj, model_obj, catalog_obj,
           min_contributors=DEFAULT_MIN_CONTRIBUTORS,
           min_indicators=DEFAULT_MIN_INDICATORS):
    diagnostics = []
    model, model_diags = load_indicator_model(model_obj)
    diagnostics.extend(model_diags)
    catalog, rejected_options, catalog_diags = load_catalog(catalog_obj, model)
    diagnostics.extend(catalog_diags)
    teams, rejected_teams, team_diags = load_teams(teams_obj, model)
    diagnostics.extend(team_diags)

    results = []
    for team in teams:
        by_dimension = {dim_id: [] for dim_id in model["order"]}
        for obs in team["observations"]:
            by_dimension[model["indicators"][obs["indicator_id"]]["dimension_id"]].append(obs)

        dimension_results = []
        requests = []
        plan = []
        for dim_id in model["order"]:
            resolved = resolve_dimension(
                model["dimensions"][dim_id], by_dimension[dim_id],
                team["contributor_count"], min_contributors, min_indicators)
            dimension_results.append(resolved)
            if resolved["state"] == UNKNOWN:
                requests.append(evidence_request(team, resolved, model, min_contributors))
                continue
            for option in select_options(resolved, catalog):
                plan.append({
                    "option_id": option["option_id"],
                    "dimension_id": resolved["dimension_id"],
                    "dimension_state": resolved["state"],
                    "horizon": option["horizon"],
                    "capability_gained": option["capability_gained"],
                    "staff_effort": option["staff_effort"],
                    "dependencies": sorted(option.get("dependencies", [])),
                    "observable_indicator": option["observable_indicator"],
                })

        plan.sort(key=lambda p: (HORIZON_INDEX[p["horizon"]], p["option_id"]))
        conflicts = check_dependencies([p["option_id"] for p in plan], catalog)

        states = [d["state"] for d in dimension_results]
        # Counts only. UNKNOWN stays out of every denominator; there is no
        # composite score anywhere in this structure.
        coverage = {
            "dimensions_defined": len(model["order"]),
            "dimensions_with_a_state": sum(1 for s in states if s != UNKNOWN),
            "dimensions_unknown": sum(1 for s in states if s == UNKNOWN),
            "established_of_assessed": sum(1 for s in states if s == "ESTABLISHED"),
            "emerging_of_assessed": sum(1 for s in states if s == "EMERGING"),
            "absent_of_assessed": sum(1 for s in states if s == "ABSENT"),
            "denominator_note": (
                "'of_assessed' counts share the denominator "
                "dimensions_with_a_state. UNKNOWN dimensions are excluded from "
                "every denominator and are not counted as a shortfall."),
        }

        results.append({
            "team_id": team["team_id"],
            "team_label": team["team_label"],
            "contributor_count": team["contributor_count"],
            "dimensions": dimension_results,
            "coverage": coverage,
            "strengths": sorted(d["dimension_id"] for d in dimension_results
                                if d["state"] == "ESTABLISHED"),
            "gaps": sorted(d["dimension_id"] for d in dimension_results
                           if d["state"] in ("ABSENT", "EMERGING")),
            "unknown": sorted(d["dimension_id"] for d in dimension_results
                              if d["state"] == UNKNOWN),
            "plan": plan,
            "evidence_requests": requests,
            "dependency_findings": conflicts,
            "rejected_observations": team["rejected_observations"],
        })

    result = {
        "artifact": "UIOWA-077 organizational AI adoption readiness",
        "fiction_notice": (
            "All team records in this run are SYNTHETIC and labelled fiction. "
            "No figure here is a measured University value, and no statement "
            "here is a University finding."),
        "scoring_notice": (
            "This artifact produces capability STATES and COUNTS. It does not "
            "produce a composite score, a maturity level, a peer percentile, a "
            "certification or compliance claim, or any assessment of an "
            "individual employee."),
        "parameters": {
            "min_contributors": min_contributors,
            "min_indicators_per_dimension": min_indicators,
            "states": list(STATES) + [UNKNOWN],
            "horizons": list(HORIZONS),
        },
        "instrument_id": model_obj.get("instrument_id", UNKNOWN),
        "catalog_id": catalog_obj.get("catalog_id", UNKNOWN),
        "teams": results,
        "rejected_teams": rejected_teams,
        "rejected_options": rejected_options,
        "diagnostics": sorted(diagnostics, key=lambda d: (d["severity"], d["code"], d["where"])),
    }
    result["content_digest"] = content_digest(result)
    return result, model, catalog


def content_digest(result):
    """Stable digest so a second operator gets byte-identical output or a loud diff."""
    payload = {k: v for k, v in result.items() if k != "content_digest"}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Writers
# --------------------------------------------------------------------------

def _csv_cell(value):
    """Export hygiene: keep a cell a spreadsheet would read as a formula as text."""
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@"):
        return "'" + text
    return text


def _write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            writer.writerow([_csv_cell(cell) for cell in row])


def write_worksheet_csv(path, result):
    header = ["team_id", "team_label", "contributor_count", "dimension_id",
              "capability_state", "reason", "reason_text", "indicators_observed",
              "evidence_sources", "notes"]
    rows = []
    for team in result["teams"]:
        for dim in team["dimensions"]:
            rows.append([
                team["team_id"], team["team_label"], team["contributor_count"],
                dim["dimension_id"], dim["state"], dim["reason"], dim["reason_text"],
                "; ".join(dim["indicators_observed"]),
                " | ".join(dim["evidence_sources"]),
                " | ".join(dim["notes"]),
            ])
    _write_csv(path, header, rows)


def write_options_csv(path, result):
    header = ["team_id", "dimension_id", "dimension_state", "option_id", "horizon",
              "capability_gained", "effort_low", "effort_high", "effort_unit",
              "effort_kind", "assumption_basis", "validating_evidence",
              "dependencies", "observable_indicator"]
    rows = []
    for team in result["teams"]:
        for item in team["plan"]:
            effort = item["staff_effort"]
            rows.append([
                team["team_id"], item["dimension_id"], item["dimension_state"],
                item["option_id"], item["horizon"], item["capability_gained"],
                effort.get("value_low"), effort.get("value_high"),
                effort.get("unit"), effort.get("effort_kind"),
                effort.get("assumption_basis"), effort.get("validating_evidence"),
                "; ".join(item["dependencies"]), item["observable_indicator"],
            ])
    _write_csv(path, header, rows)


def write_requests_csv(path, result):
    header = ["team_id", "dimension_id", "reason", "reason_text",
              "validating_evidence", "outstanding_indicator_id",
              "prompt", "artifact_request"]
    rows = []
    for team in result["teams"]:
        for request in team["evidence_requests"]:
            if not request["outstanding_indicators"]:
                rows.append([request["team_id"], request["dimension_id"],
                             request["reason"], request["reason_text"],
                             request["validating_evidence"], "", "", ""])
                continue
            for outstanding in request["outstanding_indicators"]:
                rows.append([
                    request["team_id"], request["dimension_id"], request["reason"],
                    request["reason_text"], request["validating_evidence"],
                    outstanding["indicator_id"], outstanding["prompt"],
                    outstanding["artifact_request"],
                ])
    _write_csv(path, header, rows)


def render_instrument(model_obj):
    lines = [
        "# %s" % model_obj.get("title", "Interview instrument"),
        "",
        "**Instrument id:** `%s`" % model_obj.get("instrument_id", UNKNOWN),
        "",
        "> %s" % model_obj.get("content_notice", ""),
        "",
        "> **Recording rule.** %s" % model_obj.get("recording_rule", ""),
        "",
        "Record each indicator as `ABSENT`, `EMERGING` or `ESTABLISHED` **with the "
        "evidence you actually looked at**, or leave it unobserved. An unobserved "
        "indicator is not an `ABSENT` finding - it resolves to `UNKNOWN` and becomes "
        "an evidence request.",
        "",
        "Evidence kinds: `artifact`, `system_record`, `interview_statement`. An "
        "indicator supported only by an interview statement cannot reach "
        "`ESTABLISHED`; recollection is not a record.",
        "",
    ]
    for dimension in model_obj.get("dimensions", []):
        lines.append("## %s" % dimension.get("label", dimension.get("dimension_id")))
        lines.append("")
        lines.append("*%s*" % dimension.get("intent", ""))
        lines.append("")
        for ind in dimension.get("indicators", []):
            lines.append("### %s" % ind.get("indicator_id"))
            lines.append("")
            lines.append("**Ask:** %s" % ind.get("prompt", ""))
            lines.append("")
            lines.append("**Ask to see:** %s" % ind.get("artifact_request", ""))
            lines.append("")
            lines.append("**Why it matters:** %s" % ind.get("why_it_matters", ""))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_report(result, model):
    lines = [
        "# Organizational AI adoption readiness - worked assessment",
        "",
        "**Work order:** UIOWA-077  ",
        "**Instrument:** `%s`  " % result["instrument_id"],
        "**Option catalog:** `%s`  " % result["catalog_id"],
        "**Content digest:** `%s`" % result["content_digest"],
        "",
        "> %s" % result["fiction_notice"],
        "",
        "> %s" % result["scoring_notice"],
        "",
        "**Reading `UNKNOWN`.** `UNKNOWN` means the evidence to state a capability "
        "was not available - too few contributors, or too few observed indicators. "
        "It is not a low result, it is excluded from every denominator, and it "
        "produces an evidence request rather than a development option.",
        "",
        "**Floors in this run:** at least %d contributors per team and at least %d "
        "observed indicators per dimension."
        % (result["parameters"]["min_contributors"],
           result["parameters"]["min_indicators_per_dimension"]),
        "",
    ]

    if result["rejected_teams"]:
        lines += ["## Rejected records", "",
                  "| record | reason |", "|---|---|"]
        for rec in result["rejected_teams"]:
            lines.append("| `%s` | %s |" % (rec["team_id"], ", ".join(rec["reasons"])))
        lines.append("")
    if result["rejected_options"]:
        lines += ["## Rejected options", "",
                  "| option | reason |", "|---|---|"]
        for rec in result["rejected_options"]:
            lines.append("| `%s` | %s |" % (rec["option_id"], ", ".join(rec["reasons"])))
        lines.append("")

    for team in result["teams"]:
        lines += ["## %s - %s" % (team["team_id"], team["team_label"]), "",
                  "Contributors represented: **%d**" % team["contributor_count"], ""]
        cov = team["coverage"]
        lines.append(
            "Dimensions with a state: **%d of %d**. UNKNOWN: **%d** (excluded from "
            "every denominator). Of those assessed - established %d, emerging %d, "
            "absent %d."
            % (cov["dimensions_with_a_state"], cov["dimensions_defined"],
               cov["dimensions_unknown"], cov["established_of_assessed"],
               cov["emerging_of_assessed"], cov["absent_of_assessed"]))
        lines += ["", "| dimension | state | why | evidence looked at |", "|---|---|---|---|"]
        for dim in team["dimensions"]:
            evidence = " · ".join(dim["evidence_sources"]) if dim["evidence_sources"] else "-"
            lines.append("| %s | **%s** | %s | %s |"
                         % (dim["label"], dim["state"], dim["reason_text"], evidence))
        lines.append("")
        notes = [n for dim in team["dimensions"] for n in dim["notes"]]
        if notes:
            lines += ["**Evidence-strength notes**", ""]
            lines += ["- %s" % note for note in notes]
            lines.append("")

        if team["evidence_requests"]:
            lines += ["### Evidence needed before any plan can be made here", ""]
            for request in team["evidence_requests"]:
                lines.append("**%s** - %s" % (request["dimension_label"], request["reason_text"]))
                lines.append("")
                lines.append("*Validating evidence:* %s" % request["validating_evidence"])
                lines.append("")
                for outstanding in request["outstanding_indicators"]:
                    lines.append("- `%s` - %s  \n  *Ask to see:* %s"
                                 % (outstanding["indicator_id"], outstanding["prompt"],
                                    outstanding["artifact_request"]))
                lines.append("")

        if team["plan"]:
            lines += ["### Capability-development options", ""]
            for horizon in HORIZONS:
                items = [p for p in team["plan"] if p["horizon"] == horizon]
                if not items:
                    continue
                lines += ["#### %s days" % horizon, ""]
                for item in items:
                    effort = item["staff_effort"]
                    deps = ", ".join("`%s`" % d for d in item["dependencies"]) or "none"
                    lines += [
                        "**`%s`** (%s, currently %s)" % (item["option_id"],
                                                          item["dimension_id"],
                                                          item["dimension_state"]),
                        "",
                        "- *Capability gained:* %s" % item["capability_gained"],
                        "- *Staff effort:* %s-%s %s (%s)"
                        % (effort.get("value_low"), effort.get("value_high"),
                           effort.get("unit"), effort.get("effort_kind")),
                        "- *Assumption basis:* %s" % effort.get("assumption_basis"),
                        "- *Validating evidence:* %s" % effort.get("validating_evidence"),
                        "- *Dependencies:* %s" % deps,
                        "- *Observable indicator:* %s" % item["observable_indicator"],
                        "",
                    ]
        if team["dependency_findings"]:
            lines += ["### Sequencing findings", ""]
            for finding in team["dependency_findings"]:
                lines.append("- **%s** (`%s`, %s): %s"
                             % (finding["code"], finding["where"],
                                finding["severity"], finding["message"]))
            lines.append("")
        if team["rejected_observations"]:
            lines += ["### Rejected observations", ""]
            for bad in team["rejected_observations"]:
                lines.append("- `%s`: %s" % (bad["indicator_id"], ", ".join(bad["reasons"])))
            lines.append("")

    errors = [d for d in result["diagnostics"] if d["severity"] == "error"]
    if errors:
        lines += ["## Diagnostics", "",
                  "| code | where | message |", "|---|---|---|"]
        for entry in errors:
            lines.append("| `%s` | `%s` | %s |"
                         % (entry["code"], entry["where"], entry["message"].replace("|", "\\|")))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _here(*parts):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--teams", default=_here("fixtures", "synthetic_teams.json"))
    parser.add_argument("--indicators", default=_here("model", "indicators.json"))
    parser.add_argument("--catalog", default=_here("model", "option_catalog.json"))
    parser.add_argument("--outdir", default=_here("out"))
    parser.add_argument("--min-contributors", type=int, default=DEFAULT_MIN_CONTRIBUTORS)
    parser.add_argument("--min-indicators", type=int, default=DEFAULT_MIN_INDICATORS)
    parser.add_argument("--instrument-only", action="store_true",
                        help="Render only the interview instrument and exit.")
    args = parser.parse_args(argv)

    model_obj = load_json(args.indicators)
    os.makedirs(args.outdir, exist_ok=True)

    instrument_path = os.path.join(args.outdir, "interview_instrument.md")
    with open(instrument_path, "w", encoding="utf-8") as handle:
        handle.write(render_instrument(model_obj))
    if args.instrument_only:
        print("wrote %s" % instrument_path)
        return 0

    teams_obj = load_json(args.teams)
    catalog_obj = load_json(args.catalog)
    result, model, _catalog = assess(
        teams_obj, model_obj, catalog_obj,
        min_contributors=args.min_contributors,
        min_indicators=args.min_indicators)

    with open(os.path.join(args.outdir, "readiness_assessment.json"), "w",
              encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    write_worksheet_csv(os.path.join(args.outdir, "readiness_worksheet.csv"), result)
    write_options_csv(os.path.join(args.outdir, "capability_options.csv"), result)
    write_requests_csv(os.path.join(args.outdir, "evidence_requests.csv"), result)
    with open(os.path.join(args.outdir, "readiness_report.md"), "w",
              encoding="utf-8") as handle:
        handle.write(render_report(result, model))

    print("teams assessed: %d   rejected records: %d   rejected options: %d"
          % (len(result["teams"]), len(result["rejected_teams"]),
             len(result["rejected_options"])))
    for team in result["teams"]:
        cov = team["coverage"]
        print("  %-8s contributors=%-3d state=%d/%d unknown=%d  "
              "established=%d emerging=%d absent=%d  options=%d  evidence_requests=%d"
              % (team["team_id"], team["contributor_count"],
                 cov["dimensions_with_a_state"], cov["dimensions_defined"],
                 cov["dimensions_unknown"], cov["established_of_assessed"],
                 cov["emerging_of_assessed"], cov["absent_of_assessed"],
                 len(team["plan"]), len(team["evidence_requests"])))
    errors = sum(1 for d in result["diagnostics"] if d["severity"] == "error")
    questions = sum(1 for t in result["teams"] for d in t["dependency_findings"]
                    if d["severity"] == "open_question")
    print("diagnostics: %d error(s); sequencing open questions: %d" % (errors, questions))
    print("content digest: %s" % result["content_digest"])
    print("outputs in %s" % args.outdir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
