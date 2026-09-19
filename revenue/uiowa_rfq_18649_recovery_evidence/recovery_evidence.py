#!/usr/bin/env python3
"""UIOWA-068 - Backup and service-recovery evidence.

Turns a set of service, backup-job and restoration-exercise records into a
recovery evidence matrix, a worked restoration scenario, and a ranked list of
next exercises.

The single idea this tool exists to enforce:

    A completed backup job, a demonstrated restoration, and a recovered
    service that can actually perform its business function are THREE
    DIFFERENT CLAIMS, supported by three different kinds of evidence.

Almost every backup dashboard reports the first one and lets the reader infer
the other two. This tool refuses that inference. Each service is placed on an
explicit evidence ladder and only the evidence actually present can lift it:

    R0 NO_EVIDENCE        nothing on record
    R1 CONFIGURED         a backup exists but is not currently completing
    R2 BACKUP_COMPLETING  the job succeeds on schedule
    R3 RESTORE_DEMONSTRATED  a restoration actually completed
    R4 FUNCTION_VERIFIED  the restored service performed its business function

Rules that make the ladder mean something:

  * A tabletop exercise never lifts a service above R2. A discussion of a
    restore is planning, not restoration.
  * R4 requires a business-function check that was PERFORMED, RESULTED IN
    PASS, and carries an evidence reference. "not_attempted" is never a pass,
    and a check that ran and failed is recorded as its own distinct state.
  * A past restoration does not prove you can restore TODAY's data, so the
    rung is capped at R2 while the current backup is failing, stale or
    unrecorded. The cap is always reported with the rung it capped.

The second idea: a stated RTO is fiction if a dependency cannot be brought
back inside it. Recovery time is computed over the transitive dependency
closure, and:

  * UNKNOWN propagates. One dependency with no measured restoration makes the
    whole chain's effective recovery UNKNOWN. It never becomes the best case
    of the links that were measured.
  * A lower bound is still reported, explicitly labelled as a lower bound.
    That asymmetry is deliberate: partial evidence can prove an objective is
    ALREADY exceeded, but partial evidence can never prove one is met.
  * A circular recovery dependency forces UNKNOWN even when every link was
    measured, because the measurements were each taken with the other side
    assumed present.

Missing evidence stays UNKNOWN throughout. It is never turned into a zero, a
pass, or a maturity score. No individual is scored; owners are roles.

Python 3 standard library only. No network. Deterministic: every age and
staleness calculation runs against the `as_of` date declared in the input
file, never against the wall clock.

Usage:
    python3 recovery_evidence.py --estate fixtures/synthetic_estate.json \
        --outdir out --scenario-service SVC-REG
"""

import argparse
import csv
import datetime
import json
import os
import sys

# --------------------------------------------------------------------------
# The evidence ladder
# --------------------------------------------------------------------------

RUNGS = [
    ("R0", "NO_EVIDENCE", "Nothing on record for this service."),
    ("R1", "CONFIGURED", "A backup exists but is not currently completing."),
    ("R2", "BACKUP_COMPLETING", "The backup job succeeds on its schedule."),
    ("R3", "RESTORE_DEMONSTRATED", "A restoration actually completed."),
    ("R4", "FUNCTION_VERIFIED", "The restored service performed its business function."),
]
RUNG_INDEX = {code: i for i, (code, _label, _desc) in enumerate(RUNGS)}
RUNG_LABEL = {code: label for code, label, _desc in RUNGS}
MAX_RUNG_INDEX = len(RUNGS) - 1

# Exercise kinds that can demonstrate a restoration. A tabletop is not one of
# them -- that exclusion is the whole point, so it is spelled out here rather
# than buried in a conditional.
RESTORATION_KINDS = ("partial_restore", "full_restore", "failover")
NON_RESTORATION_KINDS = ("tabletop", "walkthrough", "review")

# Grace applied to a schedule before a "successful" job is called stale:
# one missed run plus a day of slack. Unknown schedules yield UNKNOWN, never
# a default.
SCHEDULE_DAYS = {
    "hourly": 1,
    "daily": 1,
    "weekly": 7,
    "monthly": 31,
    "quarterly": 92,
}
SCHEDULE_MINUTES = {
    "hourly": 60,
    "daily": 1440,
    "weekly": 10080,
    "monthly": 44640,
    "quarterly": 132480,
}

# Scopes that could plausibly bound data loss. A config-only backup says
# nothing about an RPO for service data.
DATA_SCOPES = ("full", "data_only")

TIER_WEIGHT = {1: 3, 2: 2, 3: 1}

UNKNOWN = "UNKNOWN"


# --------------------------------------------------------------------------
# Loading and validation
# --------------------------------------------------------------------------

class EstateError(Exception):
    """The input file cannot be used at all."""


def _parse_date(value, where, issues):
    """Return a date, or None plus a recorded issue. Never guesses."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        issues.append("%s: date is not a string (%r); left UNKNOWN" % (where, value))
        return None
    try:
        return datetime.date(*(int(p) for p in value.split("-")))
    except (ValueError, TypeError):
        issues.append("%s: unparseable date %r; left UNKNOWN" % (where, value))
        return None


def load_estate(path):
    """Read the estate file. Structural problems raise; record-level problems
    are collected as issues so one bad row cannot blank the whole report."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (IOError, OSError) as exc:
        raise EstateError("cannot read estate file %s: %s" % (path, exc))
    except ValueError as exc:
        raise EstateError("estate file %s is not valid JSON: %s" % (path, exc))

    if not isinstance(raw, dict):
        raise EstateError("estate file must contain a JSON object at the top level")

    issues = []
    as_of = _parse_date(raw.get("as_of"), "top level as_of", issues)
    if as_of is None:
        raise EstateError(
            "estate file must declare a usable 'as_of' date. Ages are never "
            "computed against the wall clock, so there is no fallback."
        )

    services = {}
    for row in raw.get("services") or []:
        sid = row.get("service_id")
        if not sid:
            issues.append("a service record has no service_id; skipped")
            continue
        if sid in services:
            issues.append("duplicate service_id %s; later record skipped" % sid)
            continue
        deps = row.get("depends_on")
        if deps is None:
            deps = []
        if not isinstance(deps, list):
            issues.append("%s: depends_on is not a list; treated as empty and flagged" % sid)
            deps = []
        services[sid] = {
            "service_id": sid,
            "name": row.get("name") or sid,
            "tier": row.get("tier") if isinstance(row.get("tier"), int) else None,
            "business_function": row.get("business_function") or UNKNOWN,
            "owner_role": row.get("owner_role") or UNKNOWN,
            "stated_rto_minutes": _int_or_none(row.get("stated_rto_minutes")),
            "stated_rpo_minutes": _int_or_none(row.get("stated_rpo_minutes")),
            "depends_on": [d for d in deps if isinstance(d, str)],
        }

    backups = {}
    for row in raw.get("backups") or []:
        sid = row.get("service_id")
        bid = row.get("backup_id") or "(unidentified backup)"
        if not sid:
            issues.append("backup %s has no service_id; skipped" % bid)
            continue
        if sid not in services:
            issues.append("backup %s references unknown service %s; skipped" % (bid, sid))
            continue
        backups.setdefault(sid, []).append({
            "backup_id": bid,
            "service_id": sid,
            "scope": row.get("scope") or UNKNOWN,
            "schedule": row.get("schedule") or UNKNOWN,
            "last_job_status": row.get("last_job_status") or UNKNOWN,
            "last_job_at": _parse_date(row.get("last_job_at"), "backup %s" % bid, issues),
            "last_job_at_raw": row.get("last_job_at"),
            "retention_days": _int_or_none(row.get("retention_days")),
            "offsite_copy": _tri_state(row.get("offsite_copy")),
            "notes": row.get("notes") or "",
        })

    exercises = {}
    for row in raw.get("exercises") or []:
        sid = row.get("service_id")
        xid = row.get("exercise_id") or "(unidentified exercise)"
        if not sid:
            issues.append("exercise %s has no service_id; skipped" % xid)
            continue
        if sid not in services:
            issues.append("exercise %s references unknown service %s; skipped" % (xid, sid))
            continue
        check = row.get("business_function_check")
        if not isinstance(check, dict):
            check = {"performed": False, "result": UNKNOWN, "evidence_ref": None,
                     "description": ""}
            issues.append("exercise %s has no business_function_check; "
                          "treated as not verified" % xid)
        exercises.setdefault(sid, []).append({
            "exercise_id": xid,
            "service_id": sid,
            "date": _parse_date(row.get("date"), "exercise %s" % xid, issues),
            "date_raw": row.get("date"),
            "kind": row.get("kind") or UNKNOWN,
            "outcome": row.get("outcome") or UNKNOWN,
            "measured_restore_complete_minutes": _int_or_none(
                row.get("measured_restore_complete_minutes")),
            "check_performed": bool(check.get("performed")),
            "check_result": check.get("result") or UNKNOWN,
            "check_evidence_ref": check.get("evidence_ref"),
            "check_description": check.get("description") or "",
            "dependencies_unavailable": [
                d for d in (row.get("dependencies_unavailable") or [])
                if isinstance(d, str)],
            "notes": row.get("notes") or "",
        })

    return {
        "as_of": as_of,
        "fiction_notice": raw.get("fiction_notice") or "",
        "schema_version": raw.get("schema_version") or UNKNOWN,
        "services": services,
        "backups": backups,
        "exercises": exercises,
        "load_issues": issues,
    }


def _int_or_none(value):
    """Integers survive; everything else becomes None. A missing number is
    never silently turned into 0."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value == int(value):
        return int(value)
    return None


def _tri_state(value):
    """True / False / UNKNOWN. An absent field is UNKNOWN, not False."""
    if value is True:
        return True
    if value is False:
        return False
    return UNKNOWN


# --------------------------------------------------------------------------
# Backup health
# --------------------------------------------------------------------------

def assess_backup_health(records, as_of):
    """Classify the current backup position for one service.

    Returns (health, age_days, detail, best_record). Health is one of
    COMPLETING / STALE / FAILING / NO_RECORD / UNKNOWN. A green-but-ancient
    job is STALE, not COMPLETING -- that distinction is the whole reason this
    function exists.
    """
    if not records:
        return "NO_RECORD", None, "No backup record for this service.", None

    # Prefer the most recent successful job; fall back to the most recent job
    # of any status so a failing service still reports its age.
    def sort_key(rec):
        return (rec["last_job_at"] or datetime.date.min, rec["backup_id"])

    successes = [r for r in records if r["last_job_status"] == "success"]
    chosen = max(successes, key=sort_key) if successes else max(records, key=sort_key)

    if chosen["last_job_status"] != "success":
        return ("FAILING", None,
                "Most recent recorded job for %s is '%s'." % (
                    chosen["backup_id"], chosen["last_job_status"]),
                chosen)

    if chosen["last_job_at"] is None:
        return ("UNKNOWN", None,
                "Job %s reports success with no usable timestamp, so its "
                "currency cannot be established." % chosen["backup_id"],
                chosen)

    age_days = (as_of - chosen["last_job_at"]).days
    cadence = SCHEDULE_DAYS.get(str(chosen["schedule"]).lower())
    if cadence is None:
        return ("UNKNOWN", age_days,
                "Job %s succeeded %d day(s) ago, but its schedule (%s) is not "
                "recognised, so staleness cannot be judged." % (
                    chosen["backup_id"], age_days, chosen["schedule"]),
                chosen)

    tolerance = cadence * 2 + 1  # one missed run plus a day of slack
    if age_days > tolerance:
        return ("STALE", age_days,
                "Job %s reports success but ran %d day(s) ago against a %s "
                "schedule (tolerance %d day(s))." % (
                    chosen["backup_id"], age_days, chosen["schedule"], tolerance),
                chosen)
    return ("COMPLETING", age_days,
            "Job %s succeeded %d day(s) ago on a %s schedule." % (
                chosen["backup_id"], age_days, chosen["schedule"]),
            chosen)


# --------------------------------------------------------------------------
# The rung
# --------------------------------------------------------------------------

def assess_rung(service, backup_health, exercise_records):
    """Place one service on the evidence ladder.

    Returns a dict with the rung, any cap that was applied, and the
    diagnostics that justify it. Every lift is traceable to a specific record.
    """
    diagnostics = []
    rung = "R0"
    basis = "No backup record and no exercise record."

    if backup_health in ("FAILING", "STALE", "UNKNOWN"):
        rung = "R1"
        basis = "A backup record exists but is not currently completing."
    elif backup_health == "COMPLETING":
        rung = "R2"
        basis = "The backup job is completing on schedule."

    best_restore = None
    best_verified = None
    for ex in sorted(exercise_records, key=lambda e: (e["date"] or datetime.date.min,
                                                      e["exercise_id"])):
        kind = str(ex["kind"]).lower()
        if kind in NON_RESTORATION_KINDS:
            diagnostics.append(
                "%s (%s) is a %s: it does not demonstrate restoration and cannot "
                "lift this service above R2." % (ex["exercise_id"], ex["date_raw"], kind))
            continue
        if kind not in RESTORATION_KINDS:
            diagnostics.append(
                "%s has an unrecognised exercise kind %r; not counted as "
                "restoration evidence." % (ex["exercise_id"], ex["kind"]))
            continue
        if str(ex["outcome"]).lower() != "completed":
            diagnostics.append(
                "%s (%s) was attempted and did not complete (outcome=%s). An "
                "attempt is not a demonstrated capability." % (
                    ex["exercise_id"], ex["date_raw"], ex["outcome"]))
            continue

        best_restore = ex
        if not ex["check_performed"]:
            diagnostics.append(
                "%s restored the service but no business-function check was "
                "performed (%s). Restoration is demonstrated; usefulness is not."
                % (ex["exercise_id"], ex["check_result"]))
        elif str(ex["check_result"]).lower() == "pass":
            if ex["check_evidence_ref"]:
                best_verified = ex
            else:
                diagnostics.append(
                    "%s reports a passing business-function check with no "
                    "evidence reference; not counted toward R4." % ex["exercise_id"])
        elif str(ex["check_result"]).lower() == "fail":
            diagnostics.append(
                "%s restored the service and the business-function check RAN "
                "AND FAILED: %s" % (ex["exercise_id"], ex["check_description"]))
        else:
            diagnostics.append(
                "%s reports business-function check result %r, which is not a "
                "pass; not counted toward R4." % (ex["exercise_id"], ex["check_result"]))

    uncapped = rung
    if best_restore is not None and RUNG_INDEX["R3"] > RUNG_INDEX[uncapped]:
        uncapped = "R3"
        basis = "Restoration demonstrated by %s." % best_restore["exercise_id"]
    if best_verified is not None:
        uncapped = "R4"
        basis = "Business function verified by %s (%s)." % (
            best_verified["exercise_id"], best_verified["check_evidence_ref"])

    # A past restoration does not prove today's data can be restored.
    capped_from = None
    cap_reason = None
    final = uncapped
    if backup_health != "COMPLETING" and RUNG_INDEX[uncapped] > RUNG_INDEX["R2"]:
        capped_from = uncapped
        final = "R2"
        cap_reason = (
            "Restoration evidence exists, but the current backup is %s, so a "
            "restoration of today's data is not evidenced." % backup_health)
        diagnostics.append(cap_reason)
    if backup_health == "NO_RECORD" and RUNG_INDEX[final] > RUNG_INDEX["R1"]:
        # Restored from something, but nothing is on record producing it.
        capped_from = capped_from or uncapped
        final = "R1"
        cap_reason = ("Restoration evidence exists with no backup record on file "
                      "to produce the source data.")
        diagnostics.append(cap_reason)

    return {
        "rung": final,
        "rung_label": RUNG_LABEL[final],
        "rung_uncapped": uncapped,
        "rung_capped_from": capped_from,
        "cap_reason": cap_reason,
        "basis": basis,
        "latest_restore_exercise": best_restore["exercise_id"] if best_restore else None,
        "verifying_exercise": best_verified["exercise_id"] if best_verified else None,
        "diagnostics": diagnostics,
    }


def own_measured_minutes(exercise_records):
    """The service's own measured restoration time.

    Uses the most recent completed restoration that carries a measurement --
    capability changes over time, so the latest measurement is the honest one.
    Ties on date resolve to the larger figure rather than the flattering one.
    """
    candidates = [
        ex for ex in exercise_records
        if str(ex["kind"]).lower() in RESTORATION_KINDS
        and str(ex["outcome"]).lower() == "completed"
        and ex["measured_restore_complete_minutes"] is not None
    ]
    if not candidates:
        return None, None
    candidates.sort(key=lambda e: (e["date"] or datetime.date.min,
                                   e["measured_restore_complete_minutes"],
                                   e["exercise_id"]))
    chosen = candidates[-1]
    return chosen["measured_restore_complete_minutes"], chosen["exercise_id"]


# --------------------------------------------------------------------------
# The dependency graph
# --------------------------------------------------------------------------

def closure(service_id, services):
    """Transitive dependency closure of a service, including itself.

    Returns (members, cycle_members, missing_refs). Cycle-safe by
    construction: a visited set bounds the walk, and anything re-entered is
    reported rather than silently dropped.
    """
    members = set()
    missing = set()
    cycle = set()
    stack = [(service_id, (service_id,))]
    while stack:
        current, path = stack.pop()
        members.add(current)
        node = services.get(current)
        if node is None:
            missing.add(current)
            continue
        for dep in node["depends_on"]:
            if dep in path:
                # Re-entering a node already on this path is a genuine cycle.
                idx = path.index(dep)
                cycle.update(path[idx:])
                cycle.add(dep)
                continue
            if dep not in services:
                missing.add(dep)
                members.add(dep)
                continue
            stack.append((dep, path + (dep,)))
    return members, cycle, missing


def blast_radius(service_id, services):
    """How many other services transitively depend on this one."""
    dependents = set()
    for other in services:
        if other == service_id:
            continue
        members, _cycle, _missing = closure(other, services)
        if service_id in members:
            dependents.add(other)
    return len(dependents)


def effective_recovery(service_id, services, own_measured):
    """Recovery time over the whole restoration chain.

    UNKNOWN propagates; a lower bound is still reported and labelled as one.
    A cycle forces UNKNOWN even when every link was measured, because each
    measurement was taken with the other side assumed present.
    """
    members, cycle, missing = closure(service_id, services)
    known = []
    unmeasured = []
    for member in sorted(members):
        if member in missing:
            unmeasured.append(member)
            continue
        value = own_measured.get(member)
        if value is None:
            unmeasured.append(member)
        else:
            known.append(value)

    lower_bound = max(known) if known else None
    if cycle:
        status = UNKNOWN
        effective = None
        reason = ("Circular recovery dependency across %s: restoration order is "
                  "undefined, so a chain time cannot be computed even where "
                  "individual links were measured." % ", ".join(sorted(cycle)))
    elif missing:
        status = UNKNOWN
        effective = None
        reason = ("Dependency record(s) missing from the estate: %s."
                  % ", ".join(sorted(missing)))
    elif unmeasured:
        status = UNKNOWN
        effective = None
        reason = ("No measured restoration for %s. The chain time is unknown; "
                  "the figure below is a lower bound, not an estimate."
                  % ", ".join(sorted(unmeasured)))
    else:
        status = "MEASURED"
        effective = lower_bound
        reason = "Every link in the chain has a measured restoration."

    return {
        "chain_members": sorted(members),
        "chain_cycle": sorted(cycle),
        "chain_missing_records": sorted(missing),
        "unmeasured_links": sorted(unmeasured),
        "effective_recovery_minutes": effective,
        "effective_recovery_status": status,
        "chain_lower_bound_minutes": lower_bound,
        "reason": reason,
    }


def rto_status(stated, recovery):
    """Compare a stated objective to the evidence.

    Deliberately asymmetric. Partial evidence can prove an objective is
    ALREADY exceeded -- a lower bound above the target settles it. Partial
    evidence can never prove an objective is met, so a pass requires a
    complete measured chain.
    """
    if stated is None:
        return UNKNOWN, "No stated RTO on record."
    lower = recovery["chain_lower_bound_minutes"]
    if lower is not None and lower > stated:
        return ("EXCEEDED",
                "At least %d minutes of measured restoration in the chain against "
                "a stated %d-minute objective. Conclusive despite the remaining "
                "unknowns -- the true figure can only be higher." % (lower, stated))
    if recovery["effective_recovery_status"] == "MEASURED":
        eff = recovery["effective_recovery_minutes"]
        if eff <= stated:
            return ("WITHIN_STATED_RTO",
                    "Measured chain recovery %d minutes against a stated %d-minute "
                    "objective." % (eff, stated))
        return ("EXCEEDED",
                "Measured chain recovery %d minutes against a stated %d-minute "
                "objective." % (eff, stated))
    return (UNKNOWN,
            "Cannot be established: %s A pass requires a complete measured chain."
            % recovery["reason"])


def rpo_status(service, backup_records):
    """Whether the recorded backup schedule could bound data loss to the
    stated RPO. This checks the RECORDS, not the organisation -- an
    unrecorded mechanism may well exist, which is an interview question, not
    a failure."""
    stated = service["stated_rpo_minutes"]
    if stated is None:
        return UNKNOWN, "No stated RPO on record."
    data_backups = [b for b in backup_records if str(b["scope"]).lower() in DATA_SCOPES]
    if not data_backups:
        return (UNKNOWN,
                "No data-scope backup record for this service, so the recorded "
                "evidence cannot speak to data loss. Service data may reside in a "
                "dependency.")
    implied = []
    for b in data_backups:
        minutes = SCHEDULE_MINUTES.get(str(b["schedule"]).lower())
        if minutes is not None:
            implied.append(minutes)
    if not implied:
        return (UNKNOWN,
                "Backup schedule(s) not recognised, so implied data loss cannot "
                "be derived.")
    best = min(implied)
    if best > stated:
        return ("SCHEDULE_DOES_NOT_MEET_RPO",
                "The densest recorded data-scope schedule implies up to %d minutes "
                "of loss against a stated %d-minute objective. If a continuous or "
                "log-shipping mechanism exists it is not in these records -- ask "
                "for it rather than assuming either way." % (best, stated))
    return ("SCHEDULE_CONSISTENT_WITH_RPO",
            "The densest recorded data-scope schedule implies up to %d minutes of "
            "loss against a stated %d-minute objective." % (best, stated))


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------

def analyse(estate):
    services = estate["services"]
    as_of = estate["as_of"]

    own_measured = {}
    for sid in services:
        value, _src = own_measured_minutes(estate["exercises"].get(sid, []))
        own_measured[sid] = value

    rows = []
    for sid in sorted(services):
        service = services[sid]
        backup_records = estate["backups"].get(sid, [])
        exercise_records = estate["exercises"].get(sid, [])

        health, age_days, health_detail, chosen = assess_backup_health(backup_records, as_of)
        rung_info = assess_rung(service, health, exercise_records)
        measured, measured_src = own_measured_minutes(exercise_records)
        recovery = effective_recovery(sid, services, own_measured)
        rto_state, rto_detail = rto_status(service["stated_rto_minutes"], recovery)
        rpo_state, rpo_detail = rpo_status(service, backup_records)

        rows.append({
            "service_id": sid,
            "name": service["name"],
            "tier": service["tier"],
            "owner_role": service["owner_role"],
            "business_function": service["business_function"],
            "depends_on": service["depends_on"],
            "evidence_rung": rung_info["rung"],
            "evidence_rung_label": rung_info["rung_label"],
            "rung_uncapped": rung_info["rung_uncapped"],
            "rung_capped_from": rung_info["rung_capped_from"],
            "cap_reason": rung_info["cap_reason"],
            "rung_basis": rung_info["basis"],
            "rung_diagnostics": rung_info["diagnostics"],
            "latest_restore_exercise": rung_info["latest_restore_exercise"],
            "verifying_exercise": rung_info["verifying_exercise"],
            "backup_health": health,
            "backup_health_detail": health_detail,
            "last_backup_age_days": age_days,
            "backup_id": chosen["backup_id"] if chosen else None,
            "offsite_copy": chosen["offsite_copy"] if chosen else UNKNOWN,
            "own_measured_restore_minutes": measured,
            "own_measured_source": measured_src,
            "stated_rto_minutes": service["stated_rto_minutes"],
            "stated_rpo_minutes": service["stated_rpo_minutes"],
            "rto_status": rto_state,
            "rto_detail": rto_detail,
            "rpo_status": rpo_state,
            "rpo_detail": rpo_detail,
            "blast_radius": blast_radius(sid, services),
        })
        rows[-1].update(recovery)

    by_id = {r["service_id"]: r for r in rows}
    findings = derive_findings(rows, by_id, services)
    exercises = rank_next_exercises(rows)

    return {
        "as_of": as_of.isoformat(),
        "fiction_notice": estate["fiction_notice"],
        "schema_version": estate["schema_version"],
        "ladder": [{"rung": c, "label": l, "meaning": d} for c, l, d in RUNGS],
        "services": rows,
        "findings": findings,
        "next_exercises": exercises,
        "load_issues": estate["load_issues"],
        "counts": summarise_counts(rows),
    }


def summarise_counts(rows):
    counts = {code: 0 for code, _l, _d in RUNGS}
    for row in rows:
        counts[row["evidence_rung"]] += 1
    return {
        "services": len(rows),
        "by_rung": counts,
        "function_verified": counts["R4"],
        "restoration_demonstrated_or_better": counts["R3"] + counts["R4"],
        "recovery_time_unknown": sum(
            1 for r in rows if r["effective_recovery_status"] == UNKNOWN),
        "rto_conclusively_exceeded": sum(
            1 for r in rows if r["rto_status"] == "EXCEEDED"),
    }


def derive_findings(rows, by_id, services):
    """Cross-cutting conditions worth a reviewer's attention. Each finding
    names the records that support it so nothing has to be taken on trust."""
    findings = []

    def add(code, severity, service_id, statement, evidence):
        findings.append({
            "finding_id": "RF-%03d" % (len(findings) + 1),
            "code": code,
            "severity": severity,
            "service_id": service_id,
            "statement": statement,
            "evidence": evidence,
        })

    for row in rows:
        sid = row["service_id"]

        if row["evidence_rung"] == "R0":
            add("NO_RECOVERY_EVIDENCE", "high", sid,
                "%s has no backup record and no restoration evidence of any kind."
                % row["name"],
                ["no backup record", "no exercise record"])

        # The finding a green dashboard hides: something proven resting on
        # something unproven.
        if RUNG_INDEX[row["evidence_rung"]] >= RUNG_INDEX["R3"]:
            weak = []
            members, _cycle, _missing = closure(sid, services)
            for member in sorted(members):
                if member == sid or member not in by_id:
                    continue
                if RUNG_INDEX[by_id[member]["evidence_rung"]] <= RUNG_INDEX["R1"]:
                    weak.append(member)
            if weak:
                add("VERIFIED_SERVICE_ON_UNVERIFIED_DEPENDENCY", "high", sid,
                    "%s reaches %s, but depends on %s, which %s at R1 or below. "
                    "The proven service rests on an unproven foundation."
                    % (row["name"], row["evidence_rung"], ", ".join(weak),
                       "sits" if len(weak) == 1 else "sit"),
                    ["%s=%s" % (w, by_id[w]["evidence_rung"]) for w in weak])

        if row["chain_cycle"]:
            add("CIRCULAR_RECOVERY_DEPENDENCY", "high", sid,
                "%s sits in a circular recovery dependency (%s). Each side's "
                "measured restoration assumed the other was already available."
                % (row["name"], " <-> ".join(row["chain_cycle"])),
                row["chain_cycle"])

        if row["chain_missing_records"]:
            add("MISSING_DEPENDENCY_RECORD", "medium", sid,
                "%s depends on %s, for which no record exists in the estate. "
                "Recovery time cannot be established."
                % (row["name"], ", ".join(row["chain_missing_records"])),
                row["chain_missing_records"])

        if row["backup_health"] == "STALE":
            add("BACKUP_REPORTS_SUCCESS_BUT_IS_STALE", "high", sid,
                "%s: %s" % (row["name"], row["backup_health_detail"]),
                [row["backup_id"] or UNKNOWN])

        if row["backup_health"] == "FAILING":
            add("BACKUP_FAILING", "high", sid,
                "%s: %s" % (row["name"], row["backup_health_detail"]),
                [row["backup_id"] or UNKNOWN])

        if row["evidence_rung"] == "R3" and row["verifying_exercise"] is None:
            add("RESTORE_DEMONSTRATED_FUNCTION_UNVERIFIED", "medium", sid,
                "%s has a completed restoration but no passing business-function "
                "check. The data came back; whether the service can do its job "
                "with it is unestablished." % row["name"],
                [row["latest_restore_exercise"] or UNKNOWN])

        if row["rto_status"] == "EXCEEDED":
            add("STATED_RTO_EXCEEDED_BY_EVIDENCE", "high", sid,
                "%s: %s" % (row["name"], row["rto_detail"]),
                [row["own_measured_source"] or "chain measurement"])

        if row["rpo_status"] == "SCHEDULE_DOES_NOT_MEET_RPO":
            add("RPO_UNSUPPORTED_BY_RECORDED_SCHEDULE", "medium", sid,
                "%s: %s" % (row["name"], row["rpo_detail"]),
                [row["backup_id"] or UNKNOWN])

        if row["offsite_copy"] == UNKNOWN and row["backup_health"] in (
                "COMPLETING", "STALE"):
            add("OFFSITE_COPY_UNKNOWN", "low", sid,
                "%s: whether the backup copy leaves the primary facility was not "
                "established. Left UNKNOWN rather than assumed either way."
                % row["name"],
                [row["backup_id"] or UNKNOWN])

        for diag in row["rung_diagnostics"]:
            if "RAN AND FAILED" in diag:
                add("FUNCTION_CHECK_FAILED", "high", sid, "%s: %s" % (row["name"], diag),
                    [row["latest_restore_exercise"] or UNKNOWN])
            elif "did not complete" in diag:
                add("RESTORE_ATTEMPT_DID_NOT_COMPLETE", "medium", sid,
                    "%s: %s" % (row["name"], diag), [])

    return findings


def rank_next_exercises(rows):
    """Rank the exercises worth running next. The formula is printed in the
    output so a reviewer can disagree with the weights rather than with a
    black box."""
    out = []
    for row in rows:
        gap = MAX_RUNG_INDEX - RUNG_INDEX[row["evidence_rung"]]
        if gap == 0:
            continue
        weight = TIER_WEIGHT.get(row["tier"], 1)
        score = weight * gap * (1 + row["blast_radius"])
        out.append({
            "service_id": row["service_id"],
            "name": row["name"],
            "current_rung": row["evidence_rung"],
            "tier": row["tier"] if row["tier"] is not None else UNKNOWN,
            "tier_weight": weight,
            "evidence_gap": gap,
            "blast_radius": row["blast_radius"],
            "priority_score": score,
            "formula": "tier_weight(%d) x evidence_gap(%d) x (1 + blast_radius(%d)) = %d"
                       % (weight, gap, row["blast_radius"], score),
            "recommended_exercise": recommended_exercise(row),
        })
    out.sort(key=lambda e: (-e["priority_score"], -e["blast_radius"], e["service_id"]))
    for i, item in enumerate(out, start=1):
        item["rank"] = i
    return out


def recommended_exercise(row):
    rung = row["evidence_rung"]
    if rung == "R0":
        return ("Establish a backup record and a named owning role first. An "
                "exercise has nothing to restore from until that exists.")
    if rung == "R1":
        return ("Repair the backup job, then restore the first completing set "
                "into an isolated environment.")
    if rung == "R2":
        return ("Run a restoration exercise and measure wall-clock time to a "
                "running service. Record the figure even if it is unflattering.")
    return ("Repeat the restoration and add a business-function check: %s "
            "Record the evidence reference." % row["business_function"])


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

CSV_COLUMNS = [
    "service_id", "name", "tier", "owner_role", "evidence_rung",
    "evidence_rung_label", "rung_capped_from", "backup_health",
    "last_backup_age_days", "offsite_copy", "own_measured_restore_minutes",
    "chain_lower_bound_minutes", "effective_recovery_minutes",
    "effective_recovery_status", "stated_rto_minutes", "rto_status",
    "stated_rpo_minutes", "rpo_status", "blast_radius", "unmeasured_links",
    "chain_cycle", "chain_missing_records",
]


def _cell(value):
    """Render one cell. Absent values become the literal UNKNOWN, never a
    blank that a spreadsheet will read as zero."""
    if value is None:
        return UNKNOWN
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "; ".join(str(v) for v in value) if value else "none"
    text = str(value)
    # Neutralise spreadsheet formula injection without mangling the value.
    if text[:1] in ("=", "+", "@", "\t", "\r") or (
            text[:1] == "-" and not text[1:2].isdigit()):
        return "'" + text
    return text


def write_csv(report, path):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_COLUMNS)
        for row in report["services"]:
            writer.writerow([_cell(row.get(col)) for col in CSV_COLUMNS])
    return path


def write_json(report, path):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=False)
        handle.write("\n")
    return path


def _fmt(value, suffix=""):
    if value is None:
        return UNKNOWN
    return "%s%s" % (value, suffix)


def render_matrix_markdown(report):
    lines = []
    lines.append("| Service | Tier | Rung | Backup health | Own measured | "
                 "Chain recovery | Stated RTO | RTO status |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in report["services"]:
        if row["effective_recovery_status"] == "MEASURED":
            chain = "%d min" % row["effective_recovery_minutes"]
        elif row["chain_lower_bound_minutes"] is not None:
            chain = "UNKNOWN (>= %d min)" % row["chain_lower_bound_minutes"]
        else:
            chain = UNKNOWN
        lines.append("| %s (%s) | %s | %s %s | %s | %s | %s | %s | %s |" % (
            row["name"], row["service_id"],
            _fmt(row["tier"]),
            row["evidence_rung"], row["evidence_rung_label"],
            row["backup_health"],
            _fmt(row["own_measured_restore_minutes"], " min"),
            chain,
            _fmt(row["stated_rto_minutes"], " min"),
            row["rto_status"],
        ))
    return "\n".join(lines)


def render_scenario(report, service_id):
    """The worked restoration scenario: walk one service's chain and show the
    exact point it stops being evidenced."""
    by_id = {r["service_id"]: r for r in report["services"]}
    row = by_id.get(service_id)
    if row is None:
        return ("### Worked restoration scenario\n\n"
                "Requested service `%s` is not in the estate. Nothing is assumed "
                "in its place.\n" % service_id)

    out = []
    out.append("### Worked restoration scenario: %s (`%s`)" % (row["name"], service_id))
    out.append("")
    out.append("**Business function that must come back:** %s" % row["business_function"])
    out.append("")
    out.append("**Stated objective:** RTO %s, RPO %s. **Owning role:** %s." % (
        _fmt(row["stated_rto_minutes"], " minutes"),
        _fmt(row["stated_rpo_minutes"], " minutes"),
        row["owner_role"]))
    out.append("")
    out.append("**Restoration chain** (every service that must be back before this "
               "one can do its job):")
    out.append("")
    out.append("| Step | Service | Rung | Own measured restore | What is missing |")
    out.append("|---|---|---|---|---|")
    ordered = [service_id] + [m for m in row["chain_members"] if m != service_id]
    for member in ordered:
        dep = by_id.get(member)
        if dep is None:
            out.append("| - | `%s` | %s | %s | No record of this service exists in "
                       "the estate. |" % (member, UNKNOWN, UNKNOWN))
            continue
        missing = []
        if dep["own_measured_restore_minutes"] is None:
            missing.append("no measured restoration")
        if dep["evidence_rung"] in ("R0", "R1"):
            missing.append("no current backup evidence")
        if dep["evidence_rung"] == "R3":
            missing.append("business function unverified")
        out.append("| %s | `%s` %s | %s | %s | %s |" % (
            "self" if member == service_id else "dep",
            member, dep["name"], dep["evidence_rung"],
            _fmt(dep["own_measured_restore_minutes"], " min"),
            "; ".join(missing) if missing else "-"))
    out.append("")
    out.append("**Where this stalls.** %s" % row["reason"])
    out.append("")
    if row["chain_lower_bound_minutes"] is not None:
        out.append("**Measured recovery time:** the slowest *measured* link in this "
                   "chain is %d minutes. That is a **lower bound on the whole "
                   "chain**, not an estimate of it: the unmeasured links can only "
                   "push the real figure higher."
                   % row["chain_lower_bound_minutes"])
    else:
        out.append("**Measured recovery time:** UNKNOWN. No link in this chain has a "
                   "measured restoration, so no lower bound can be stated either.")
    out.append("")
    out.append("**Against the stated objective:** %s -- %s" % (
        row["rto_status"], row["rto_detail"]))
    out.append("")
    out.append("**Backup completion is not the same claim.** Backup health for this "
               "service is `%s` (%s). That establishes that a job exited "
               "successfully. It establishes nothing about restoration, and nothing "
               "about whether a restored instance could satisfy its business "
               "function: *%s*"
               % (row["backup_health"], row["backup_health_detail"],
                  row["business_function"]))
    if row["rung_diagnostics"]:
        out.append("")
        out.append("**Evidence notes for this service:**")
        out.append("")
        for diag in row["rung_diagnostics"]:
            out.append("- %s" % diag)
    return "\n".join(out)


INTERVIEW_PROMPTS = [
    ("Separating completion from restoration",
     "Show me the most recent restore you actually performed for {top_service}, not "
     "the backup job log. What was the wall-clock time from decision to a running "
     "service?"),
    ("Function, not process",
     "After that restore, what did someone do to confirm this held true -- "
     "*{function}* -- and where is that recorded?"),
    ("Dependency reality",
     "If {top_service} had to be rebuilt today, what has to be back first? Walk me "
     "down the chain until you reach something nobody has ever restored."),
    ("The unrecorded mechanism",
     "Several stated RPOs are denser than the recorded backup schedules support. Is "
     "there a continuous or log-shipping mechanism that is not in these records?"),
    ("Circularity",
     "If the backup control plane and its catalog were both unavailable, what is the "
     "documented order of operations to get either one back?"),
    ("Ownership as a role",
     "Which role -- not which person -- is accountable for deciding a restoration is "
     "complete, and what do they check before saying so?"),
    ("The exercise that was not run",
     "What restoration exercise has been deferred most often, and what has blocked "
     "it each time?"),
    ("Evidence retention",
     "Where do restoration exercise records live, how long are they kept, and who can "
     "produce one from two years ago?"),
]


def render_report(report, scenario_service):
    counts = report["counts"]
    out = []
    out.append("# Recovery evidence matrix (UIOWA-068)")
    out.append("")
    out.append("> %s" % report["fiction_notice"])
    out.append("")
    out.append("Generated from records as of **%s**. All ages are computed against "
               "that declared date, never the wall clock, so this output is "
               "reproducible." % report["as_of"])
    out.append("")
    out.append("## What this matrix does and does not claim")
    out.append("")
    out.append("A rung is a statement about **evidence on file**, not a maturity "
               "rating and not a judgement of any team. `UNKNOWN` means the evidence "
               "was not supplied; it is never converted into a zero, a pass, or a "
               "score. Owners are recorded as roles, never as individuals.")
    out.append("")
    for code, label, desc in RUNGS:
        out.append("- **%s %s** - %s" % (code, label, desc))
    out.append("")
    out.append("Two rules do most of the work: **a tabletop exercise never lifts a "
               "service above R2**, and **R4 requires a business-function check that "
               "was performed, passed, and carries an evidence reference**.")
    out.append("")
    out.append("## Position")
    out.append("")
    out.append("%d services. By rung: %s." % (
        counts["services"],
        ", ".join("%s=%d" % (k, counts["by_rung"][k]) for k, _l, _d in RUNGS)))
    out.append("")
    out.append("- **%d** service(s) have a verified business function after "
               "restoration (R4)." % counts["function_verified"])
    out.append("- **%d** service(s) have any demonstrated restoration at all "
               "(R3 or better)." % counts["restoration_demonstrated_or_better"])
    out.append("- **%d** service(s) have an UNKNOWN chain recovery time."
               % counts["recovery_time_unknown"])
    out.append("- **%d** service(s) have a stated RTO that the evidence already "
               "shows is exceeded." % counts["rto_conclusively_exceeded"])
    out.append("")
    out.append("## Evidence matrix")
    out.append("")
    out.append(render_matrix_markdown(report))
    out.append("")
    out.append("`UNKNOWN (>= N min)` is a lower bound, not an estimate. It means the "
               "chain contains at least one measured link of N minutes and at least "
               "one link nobody has measured.")
    out.append("")
    out.append(render_scenario(report, scenario_service))
    out.append("")
    out.append("## Findings")
    out.append("")
    if not report["findings"]:
        out.append("No cross-cutting findings derived from the supplied records.")
    else:
        out.append("| ID | Severity | Service | Finding |")
        out.append("|---|---|---|---|")
        for f in report["findings"]:
            out.append("| %s | %s | `%s` | %s |" % (
                f["finding_id"], f["severity"], f["service_id"],
                f["statement"].replace("|", "\\|")))
    out.append("")
    out.append("## Next exercises, ranked")
    out.append("")
    out.append("Ranking formula, stated so it can be argued with: "
               "`tier_weight x evidence_gap x (1 + blast_radius)`, where "
               "`tier_weight` is 3/2/1 for tiers 1/2/3, `evidence_gap` is how many "
               "rungs short of R4 the service sits, and `blast_radius` is how many "
               "other services transitively depend on it. Ties break on blast radius, "
               "then service id. A high rank is a claim about where evidence is "
               "cheapest to gain, not a claim that the service is failing.")
    out.append("")
    out.append("| Rank | Service | Rung | Score | Formula | Recommended exercise |")
    out.append("|---|---|---|---|---|---|")
    for item in report["next_exercises"]:
        out.append("| %d | %s (`%s`) | %s | %d | %s | %s |" % (
            item["rank"], item["name"], item["service_id"], item["current_rung"],
            item["priority_score"], item["formula"], item["recommended_exercise"]))
    out.append("")
    out.append("## Interview prompts")
    out.append("")
    top = report["next_exercises"][0] if report["next_exercises"] else None
    top_name = top["name"] if top else "the highest-ranked service"
    by_id = {r["service_id"]: r for r in report["services"]}
    function = (by_id[top["service_id"]]["business_function"]
                if top and top["service_id"] in by_id else "perform its business function")
    for heading, prompt in INTERVIEW_PROMPTS:
        out.append("- **%s.** %s" % (
            heading, prompt.format(top_service=top_name, function=function)))
    out.append("")
    if report["load_issues"]:
        out.append("## Input problems observed")
        out.append("")
        out.append("These records could not be used as supplied. They are listed "
                   "rather than dropped silently.")
        out.append("")
        for issue in report["load_issues"]:
            out.append("- %s" % issue)
        out.append("")
    out.append("## What is still UNKNOWN")
    out.append("")
    out.append("Every `UNKNOWN` above is an open evidence request, not a deficiency "
               "score. Nothing in this document is a certification, a compliance "
               "determination, or a comparison against any peer institution.")
    return "\n".join(out)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a recovery evidence matrix and worked restoration "
                    "scenario from service, backup and exercise records.")
    parser.add_argument("--estate", default="fixtures/synthetic_estate.json",
                        help="path to the estate JSON file")
    parser.add_argument("--outdir", default="out",
                        help="directory for generated artifacts")
    parser.add_argument("--scenario-service", default="SVC-REG",
                        help="service to walk in the worked restoration scenario")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress the console summary")
    args = parser.parse_args(argv)

    try:
        estate = load_estate(args.estate)
    except EstateError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 2

    report = analyse(estate)

    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)
    json_path = write_json(report, os.path.join(args.outdir, "recovery_evidence.json"))
    csv_path = write_csv(report, os.path.join(args.outdir, "recovery_evidence_matrix.csv"))
    md_path = os.path.join(args.outdir, "recovery_evidence_report.md")
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(render_report(report, args.scenario_service))
        handle.write("\n")

    if not args.quiet:
        counts = report["counts"]
        print("as_of %s   services %d" % (report["as_of"], counts["services"]))
        print("by rung: %s" % "  ".join(
            "%s=%d" % (k, counts["by_rung"][k]) for k, _l, _d in RUNGS))
        print("function verified (R4): %d" % counts["function_verified"])
        print("chain recovery UNKNOWN: %d" % counts["recovery_time_unknown"])
        print("stated RTO conclusively exceeded: %d" % counts["rto_conclusively_exceeded"])
        print("findings: %d" % len(report["findings"]))
        if report["next_exercises"]:
            top = report["next_exercises"][0]
            print("top next exercise: %s (%s) score %d" % (
                top["service_id"], top["current_rung"], top["priority_score"]))
        for path in (json_path, csv_path, md_path):
            print("wrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
