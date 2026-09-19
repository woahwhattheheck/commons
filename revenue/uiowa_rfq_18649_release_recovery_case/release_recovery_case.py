#!/usr/bin/env python3
"""UIOWA-109 -- integrated release-and-recovery case: cross-component agreement engine.

WHY THIS IS NOT ANOTHER ASSESSOR
--------------------------------
Order 109's completion bar is "each component's output agrees on the timeline and
source IDs; recovery claims follow actual synthetic verification records". Three
components already exist and each one is individually correct:

  * release provenance (UIOWA-057)  deployments -> artifacts -> builds -> sources
  * recovery evidence  (UIOWA-068)  backup / restore / dependency / business ladder
  * environment view                where a release was verified vs. where it ran

Three individually-correct components can still disagree with each other. The
provenance export can say a deployment happened at 22:00, the recovery export can
say the same deployment happened at 22:05, and BOTH tools return green because
neither can see the other's clock. That disagreement is the actual risk in a
multi-component delivery kit, and it is what this engine looks for.

So this file adds no new scoring model. It holds ONE case -- one shared event
register and one shared evidence register -- projects it into each component's
contract, and then checks the projections against each other.

THE DESIGN DECISION THAT MAKES DISAGREEMENT DETECTABLE
-----------------------------------------------------
Every moment in time is referenced through an "event reference":

    {"event_id": "EVT-DEPLOY", "asserted_at": "2026-09-17T22:00:00+00:00"}

The authoritative timestamp lives once, in `events`. A component reference MAY
also carry `asserted_at` -- what that component's own export claims. If a
component asserts a time that differs from the register, that is a
TIMELINE_DISAGREEMENT and it is reported with both values and both claimants.
`asserted_at: null` means "this component carries no clock of its own", which is
honest and is not a finding.

If every component's timestamp were read out of one field, agreement would be
structurally guaranteed and this checker would be theatre. It is not: the
disagreement has somewhere real to live.

UNKNOWN DISCIPLINE
------------------
An event with `observed_at: null` stays UNKNOWN. It is reported as UNORDERABLE
and is excluded from ordering checks -- it never defaults into position, never
becomes "earliest", never becomes a pass. An ordering constraint that touches an
unknown endpoint is reported UNKNOWN, which is neither a pass nor a violation.

Missing evidence is never a zero, a pass, or a maturity score. There is no
average, no confidence score, no percentile, no individual performance rating.

Exit codes mirror UIOWA-057 so the kits compose:
  0  AGREED         -- the components agree under this model
  1  GAPS           -- unknowns / unsupported claims, no contradiction
  1  CONTRADICTIONS -- at least one contradiction (outranks GAPS)
  2  malformed input -- diagnostic on stderr, NO report emitted

Exit 0 is not a release approval, a recovery certification, or a statement that
the release was safe. It means the supplied records do not contradict each other.

Every example in this kit is FICTIONAL. Nothing here describes the University of
Iowa, any real service, any real release, or any real incident.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import sys

SCHEMA_VERSION = 1
MAX_INPUT_BYTES = 4 * 1024 * 1024  # format safeguard, not a hostile-file sandbox

# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------

EVENT_KINDS = (
    "source_approved",
    "build_started",
    "build_finished",
    "deployment",
    "verification",
    "disruption",
    "restored_data_as_of",
    "restore_completed",
    "dependency_verification",
    "business_verification",
    "backup_completed",
)

EVIDENCE_KINDS = ("synthetic", "artifact", "interview")
VERIFICATION_OUTCOMES = ("PASSED", "FAILED", "NOT_PERFORMED")
DATA_CLASSES = ("synthetic", "assessment")

ROOT_FIELDS = {
    "fiction_notice": str,
    "schema_version": int,
    "case_id": str,
    "data_class": str,
    "as_of": str,
    "evidence": list,
    "events": list,
    "environments": list,
    "release": dict,
    "verifications": list,
    "recovery": dict,
}

EVIDENCE_FIELDS = ("evidence_id", "locator", "owner_role", "kind", "captured_at")
EVENT_FIELDS = ("event_id", "kind", "observed_at", "evidence_id")
ENVIRONMENT_FIELDS = ("environment_id", "purpose")
SOURCE_FIELDS = ("source_id", "repository", "revision", "approved_revision",
                 "approved", "approval_evidence_id")
BUILD_FIELDS = ("build_id", "source_id", "observed_repository", "observed_revision",
                "builder_id", "input_coverage", "started", "finished", "evidence_id")
ARTIFACT_FIELDS = ("artifact_id", "build_id", "version", "sha256", "evidence_id")
DEPLOYMENT_FIELDS = ("deployment_id", "artifact_id", "environment", "observed_version",
                     "observed_sha256", "deployed", "evidence_id")
VERIFICATION_FIELDS = ("verification_id", "environment", "artifact_version", "outcome",
                       "performed", "evidence_id")
SERVICE_FIELDS = ("service_id", "name", "business_function", "target_rpo_minutes",
                  "target_rto_minutes", "dependencies", "backup", "exercise")
BACKUP_FIELDS = ("last_successful", "evidence_id")
EXERCISE_FIELDS = ("exercise_id", "disruption", "restored_data_as_of", "restore_completed",
                   "business_verification", "dependency_results")
DEPRESULT_FIELDS = ("dependency_id", "verified", "evidence_id")
EVENTREF_FIELDS = ("event_id", "asserted_at")

# Ordering constraints. These are SCOPED, and the scoping is the whole point.
#
# A naive checker cross-products every event of kind A against every event of
# kind B in the whole case. That produces two false positives immediately:
#
#   * two services each have a disruption and a restore; service B's restore
#     legitimately completes before service A's disruption, and a global
#     cross-product calls that an inversion. Recovery rules are therefore scoped
#     PER SERVICE.
#   * a pre-release verification in a staging environment legitimately happens
#     BEFORE the deployment. Only a verification of the environment that actually
#     ran the release has an ordering relation to that deployment, so
#     DEPLOY_BEFORE_VERIFY reads the same-environment slot only.
#
# Valid work staying valid matters as much as catching the real inversions.
# (earlier_slot, later_slot, rule_id, why)
RELEASE_ORDERING_RULES = (
    ("build_started", "build_finished", "BUILD_SPAN",
     "a build cannot finish before it started"),
    ("build_finished", "deployment", "BUILD_BEFORE_DEPLOY",
     "the deployed artifact must have finished building before it was deployed"),
    ("source_approved", "deployment", "APPROVAL_BEFORE_DEPLOY",
     "source approval must not postdate the deployment it authorised (UIOWA-057 rule)"),
    ("deployment", "verification_same_environment", "DEPLOY_BEFORE_VERIFY",
     "a verification OF THE DEPLOYED ENVIRONMENT cannot precede the deployment; a "
     "verification in another environment has no ordering relation to it"),
)

SERVICE_ORDERING_RULES = (
    ("disruption", "restore_completed", "DISRUPTION_BEFORE_RESTORE",
     "a restore cannot complete before the disruption that required it"),
    ("restored_data_as_of", "disruption", "RPO_POINT_BEFORE_DISRUPTION",
     "restored data cannot be newer than the disruption (that is the RPO model)"),
    ("dependency_verification", "business_verification", "DEPENDENCY_BEFORE_BUSINESS",
     "a business function cannot be verified before the dependency it needs"),
)

# Finding codes that are contradictions rather than gaps. A contradiction says two
# records cannot both be true; a gap says evidence is absent. They are reported
# separately because they demand different follow-up: reconcile vs. request.
CONTRADICTION_CODES = {
    "TIMELINE_DISAGREEMENT",
    "ORDERING_INVERSION",
    "ID_COLLISION",
    "VERSION_DIFFERENCE",
    "DIGEST_DIFFERENCE",
    "REVISION_DIFFERENCE",
}


class CaseError(Exception):
    """Malformed input. Produces exit 2 and no report -- never a fabricated result."""


# ---------------------------------------------------------------------------
# Loading and structural validation
# ---------------------------------------------------------------------------

def _no_duplicate_keys(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise CaseError(f"duplicate JSON key {k!r}")
        seen[k] = v
    return seen


def _reject_nonfinite(x):
    raise CaseError("non-finite JSON constant (NaN/Infinity) is not accepted")


def load_case(path):
    try:
        with open(path, "rb") as fh:
            raw = fh.read(MAX_INPUT_BYTES + 1)
    except OSError as exc:
        raise CaseError(f"cannot read case file: {exc}") from exc
    if len(raw) > MAX_INPUT_BYTES:
        raise CaseError(f"case file exceeds {MAX_INPUT_BYTES} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CaseError(f"case file is not valid UTF-8: {exc}") from exc
    try:
        data = json.loads(text, object_pairs_hook=_no_duplicate_keys,
                          parse_constant=_reject_nonfinite)
    except json.JSONDecodeError as exc:
        raise CaseError(f"case file is not valid JSON: {exc}") from exc
    return validate_case(data)


def _require_fields(obj, fields, where):
    if not isinstance(obj, dict):
        raise CaseError(f"{where}: expected an object, got {type(obj).__name__}")
    missing = [f for f in fields if f not in obj]
    if missing:
        raise CaseError(f"{where}: missing required field(s) {', '.join(sorted(missing))}")
    unknown = [f for f in obj if f not in fields]
    if unknown:
        # Unknown fields are an error so an adapter mistake cannot silently vanish.
        raise CaseError(f"{where}: unknown field(s) {', '.join(sorted(unknown))}")


def _parse_ts(value, where):
    """Parse an ISO-8601 instant with an explicit offset. None stays None (UNKNOWN)."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise CaseError(f"{where}: timestamp must be a string or null")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(text)
    except ValueError as exc:
        raise CaseError(f"{where}: unparseable timestamp {value!r}: {exc}") from exc
    if parsed.tzinfo is None:
        raise CaseError(f"{where}: timestamp {value!r} has no UTC offset")
    if parsed.second == 0 and len(text.split("T")[-1].split("+")[0].split("-")[0]) < 8:
        raise CaseError(f"{where}: timestamp {value!r} omits seconds")
    return parsed.astimezone(datetime.timezone.utc)


def _eventref(obj, where):
    _require_fields(obj, EVENTREF_FIELDS, where)
    if not isinstance(obj["event_id"], str) or not obj["event_id"].strip():
        raise CaseError(f"{where}.event_id: must be a non-empty string")
    return {"event_id": obj["event_id"],
            "asserted_at": _parse_ts(obj["asserted_at"], f"{where}.asserted_at"),
            "asserted_raw": obj["asserted_at"],
            "path": where}


def _unique(ids, where):
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise CaseError(f"{where}: duplicate id(s) {', '.join(dupes)}")


def validate_case(data):
    """Structural validation. Fails closed -- a malformed case never yields a report."""
    _require_fields(data, tuple(ROOT_FIELDS), "case")
    for field, expected in ROOT_FIELDS.items():
        if not isinstance(data[field], expected) or isinstance(data[field], bool):
            raise CaseError(f"case.{field}: expected {expected.__name__}")
    if data["schema_version"] != SCHEMA_VERSION:
        raise CaseError(f"case.schema_version: expected {SCHEMA_VERSION}, "
                        f"got {data['schema_version']!r}")
    if data["data_class"] not in DATA_CLASSES:
        raise CaseError(f"case.data_class: expected one of {DATA_CLASSES}")
    if not data["case_id"].strip():
        raise CaseError("case.case_id: must be non-empty")
    as_of = _parse_ts(data["as_of"], "case.as_of")
    if as_of is None:
        raise CaseError("case.as_of: required, all arithmetic is against this "
                        "declared instant and never the wall clock")

    case = {"case_id": data["case_id"], "data_class": data["data_class"],
            "fiction_notice": data["fiction_notice"], "as_of": as_of,
            "as_of_raw": data["as_of"]}

    # --- evidence register -------------------------------------------------
    evidence = {}
    for i, row in enumerate(data["evidence"]):
        _require_fields(row, EVIDENCE_FIELDS, f"case.evidence[{i}]")
        if row["kind"] not in EVIDENCE_KINDS:
            raise CaseError(f"case.evidence[{i}].kind: expected one of {EVIDENCE_KINDS}")
        for f in ("evidence_id", "locator", "owner_role"):
            if not isinstance(row[f], str) or not row[f].strip():
                raise CaseError(f"case.evidence[{i}].{f}: must be a non-empty string")
        evidence[row["evidence_id"]] = {
            "evidence_id": row["evidence_id"], "locator": row["locator"],
            "owner_role": row["owner_role"], "kind": row["kind"],
            "captured_at": _parse_ts(row["captured_at"], f"case.evidence[{i}].captured_at"),
        }
    _unique([r["evidence_id"] for r in data["evidence"]], "case.evidence")

    # --- event register ----------------------------------------------------
    events = {}
    for i, row in enumerate(data["events"]):
        _require_fields(row, EVENT_FIELDS, f"case.events[{i}]")
        if row["kind"] not in EVENT_KINDS:
            raise CaseError(f"case.events[{i}].kind: expected one of {EVENT_KINDS}")
        if not isinstance(row["event_id"], str) or not row["event_id"].strip():
            raise CaseError(f"case.events[{i}].event_id: must be a non-empty string")
        if row["evidence_id"] is not None and not isinstance(row["evidence_id"], str):
            raise CaseError(f"case.events[{i}].evidence_id: must be a string or null")
        events[row["event_id"]] = {
            "event_id": row["event_id"], "kind": row["kind"],
            "observed_at": _parse_ts(row["observed_at"], f"case.events[{i}].observed_at"),
            "observed_raw": row["observed_at"], "evidence_id": row["evidence_id"],
        }
    _unique([r["event_id"] for r in data["events"]], "case.events")

    # --- environments ------------------------------------------------------
    environments = {}
    for i, row in enumerate(data["environments"]):
        _require_fields(row, ENVIRONMENT_FIELDS, f"case.environments[{i}]")
        for f in ENVIRONMENT_FIELDS:
            if not isinstance(row[f], str) or not row[f].strip():
                raise CaseError(f"case.environments[{i}].{f}: must be a non-empty string")
        environments[row["environment_id"]] = dict(row)
    _unique([r["environment_id"] for r in data["environments"]], "case.environments")

    # --- release chain -----------------------------------------------------
    rel = data["release"]
    _require_fields(rel, ("source", "build", "artifact", "deployment"), "case.release")
    src = rel["source"]
    _require_fields(src, SOURCE_FIELDS, "case.release.source")
    bld = rel["build"]
    _require_fields(bld, BUILD_FIELDS, "case.release.build")
    if bld["input_coverage"] not in ("declared_complete", "partial", "unknown"):
        raise CaseError("case.release.build.input_coverage: expected "
                        "declared_complete | partial | unknown")
    art = rel["artifact"]
    _require_fields(art, ARTIFACT_FIELDS, "case.release.artifact")
    dep = rel["deployment"]
    _require_fields(dep, DEPLOYMENT_FIELDS, "case.release.deployment")

    release = {
        "source": dict(src, approved=_eventref(src["approved"],
                                               "case.release.source.approved")),
        "build": dict(bld,
                      started=_eventref(bld["started"], "case.release.build.started"),
                      finished=_eventref(bld["finished"], "case.release.build.finished")),
        "artifact": dict(art),
        "deployment": dict(dep, deployed=_eventref(dep["deployed"],
                                                   "case.release.deployment.deployed")),
    }

    # --- verifications -----------------------------------------------------
    verifications = []
    for i, row in enumerate(data["verifications"]):
        _require_fields(row, VERIFICATION_FIELDS, f"case.verifications[{i}]")
        if row["outcome"] not in VERIFICATION_OUTCOMES:
            raise CaseError(f"case.verifications[{i}].outcome: expected one of "
                            f"{VERIFICATION_OUTCOMES}")
        verifications.append(dict(
            row, performed=_eventref(row["performed"],
                                     f"case.verifications[{i}].performed")))
    _unique([r["verification_id"] for r in data["verifications"]], "case.verifications")

    # --- recovery ----------------------------------------------------------
    rec = data["recovery"]
    _require_fields(rec, ("assessment_id", "services"), "case.recovery")
    if not isinstance(rec["services"], list):
        raise CaseError("case.recovery.services: expected a list")
    if not rec["services"]:
        # Mirrors UIOWA-057's "empty deployment collections are never a pass".
        raise CaseError("case.recovery.services: empty service list is never a pass; "
                        "supply the services in scope or state the scope boundary")
    services = []
    for i, svc in enumerate(rec["services"]):
        where = f"case.recovery.services[{i}]"
        _require_fields(svc, SERVICE_FIELDS, where)
        if not isinstance(svc["dependencies"], list):
            raise CaseError(f"{where}.dependencies: expected a list")
        for f in ("target_rpo_minutes", "target_rto_minutes"):
            if svc[f] is not None and (not isinstance(svc[f], int)
                                       or isinstance(svc[f], bool) or svc[f] < 0):
                raise CaseError(f"{where}.{f}: expected a non-negative integer or null")
        bak = svc["backup"]
        _require_fields(bak, BACKUP_FIELDS, f"{where}.backup")
        backup = dict(bak, last_successful=_eventref(bak["last_successful"],
                                                     f"{where}.backup.last_successful"))
        exercise = None
        if svc["exercise"] is not None:
            ex = svc["exercise"]
            _require_fields(ex, EXERCISE_FIELDS, f"{where}.exercise")
            bizver = None
            if ex["business_verification"] is not None:
                bizver = _eventref(ex["business_verification"],
                                   f"{where}.exercise.business_verification")
            deps = []
            if not isinstance(ex["dependency_results"], list):
                raise CaseError(f"{where}.exercise.dependency_results: expected a list")
            for j, dr in enumerate(ex["dependency_results"]):
                drw = f"{where}.exercise.dependency_results[{j}]"
                _require_fields(dr, DEPRESULT_FIELDS, drw)
                deps.append(dict(dr, verified=_eventref(dr["verified"], f"{drw}.verified")))
            exercise = dict(
                ex,
                disruption=_eventref(ex["disruption"], f"{where}.exercise.disruption"),
                restored_data_as_of=_eventref(ex["restored_data_as_of"],
                                              f"{where}.exercise.restored_data_as_of"),
                restore_completed=_eventref(ex["restore_completed"],
                                            f"{where}.exercise.restore_completed"),
                business_verification=bizver, dependency_results=deps)
        services.append(dict(svc, backup=backup, exercise=exercise))
    _unique([s["service_id"] for s in rec["services"]], "case.recovery.services")

    case.update(evidence=evidence, events=events, environments=environments,
                release=release, verifications=verifications,
                recovery={"assessment_id": rec["assessment_id"], "services": services})
    return case


# ---------------------------------------------------------------------------
# Event-reference collection -- the spine of every cross-component check
# ---------------------------------------------------------------------------

def collect_eventrefs(case):
    """Every place a component points at a moment in time, tagged by component.

    The `component` tag is what lets a disagreement name both claimants instead
    of just announcing that one exists.
    """
    refs = []

    def add(ref, component):
        refs.append(dict(ref, component=component))

    add(case["release"]["source"]["approved"], "provenance")
    add(case["release"]["build"]["started"], "provenance")
    add(case["release"]["build"]["finished"], "provenance")
    add(case["release"]["deployment"]["deployed"], "provenance")
    for ver in case["verifications"]:
        add(ver["performed"], "environment")
    for svc in case["recovery"]["services"]:
        add(svc["backup"]["last_successful"], "recovery")
        ex = svc["exercise"]
        if ex is None:
            continue
        add(ex["disruption"], "recovery")
        add(ex["restored_data_as_of"], "recovery")
        add(ex["restore_completed"], "recovery")
        if ex["business_verification"] is not None:
            add(ex["business_verification"], "recovery")
        for dr in ex["dependency_results"]:
            add(dr["verified"], "recovery")
    return refs


def collect_evidence_refs(case):
    """Every evidence_id any component cites, with the citing path."""
    out = []

    def add(eid, path, component):
        if eid is not None:
            out.append({"evidence_id": eid, "path": path, "component": component})

    for ev in case["events"].values():
        add(ev["evidence_id"], f"events[{ev['event_id']}].evidence_id", "register")
    rel = case["release"]
    add(rel["source"]["approval_evidence_id"],
        "release.source.approval_evidence_id", "provenance")
    add(rel["build"]["evidence_id"], "release.build.evidence_id", "provenance")
    add(rel["artifact"]["evidence_id"], "release.artifact.evidence_id", "provenance")
    add(rel["deployment"]["evidence_id"], "release.deployment.evidence_id", "provenance")
    for ver in case["verifications"]:
        add(ver["evidence_id"],
            f"verifications[{ver['verification_id']}].evidence_id", "environment")
    for svc in case["recovery"]["services"]:
        sid = svc["service_id"]
        add(svc["backup"]["evidence_id"],
            f"recovery.services[{sid}].backup.evidence_id", "recovery")
        ex = svc["exercise"]
        if ex is None:
            continue
        for dr in ex["dependency_results"]:
            add(dr["evidence_id"],
                f"recovery.services[{sid}].exercise.dependency_results"
                f"[{dr['dependency_id']}].evidence_id", "recovery")
    return out


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _finding(code, subject, detail, component=None, cites=None):
    return {"code": code, "subject": subject, "detail": detail,
            "component": component or "cross-component",
            "cites": sorted(cites or []),
            "class": "contradiction" if code in CONTRADICTION_CODES else "gap"}


def check_source_ids(case, findings):
    """Every referenced id resolves. An unresolved id is a gap, never a silent drop."""
    for ref in collect_eventrefs(case):
        if ref["event_id"] not in case["events"]:
            findings.append(_finding(
                "UNRESOLVED_EVENT_ID", ref["event_id"],
                f"{ref['path']} references event {ref['event_id']!r}, which is not in "
                f"the shared event register; the components cannot be aligned on it",
                ref["component"]))
    for ref in collect_evidence_refs(case):
        if ref["evidence_id"] not in case["evidence"]:
            findings.append(_finding(
                "UNRESOLVED_SOURCE_ID", ref["evidence_id"],
                f"{ref['path']} cites source {ref['evidence_id']!r}, which is not in the "
                f"shared evidence register; the claim it supports cannot be traced",
                ref["component"]))


def check_id_collisions(case, findings):
    """One identifier must not mean two different things across namespaces.

    UIOWA-103's problem restated for this case: an evidence id reused as an event
    id joins two unrelated records in any downstream tool that keys on the string.
    """
    namespaces = {
        "evidence": set(case["evidence"]),
        "event": set(case["events"]),
        "environment": set(case["environments"]),
        "service": {s["service_id"] for s in case["recovery"]["services"]},
        "verification": {v["verification_id"] for v in case["verifications"]},
    }
    names = sorted(namespaces)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for shared in sorted(namespaces[a] & namespaces[b]):
                findings.append(_finding(
                    "ID_COLLISION", shared,
                    f"identifier {shared!r} is used as both a {a} id and a {b} id; "
                    f"same-looking ids from different origins must not silently join",
                    cites=[shared]))


def check_timeline_agreement(case, findings):
    """Do the components agree on when each shared event happened?"""
    matrix = []
    by_event = {}
    for ref in collect_eventrefs(case):
        by_event.setdefault(ref["event_id"], []).append(ref)

    for event_id in sorted(by_event):
        event = case["events"].get(event_id)
        register = event["observed_at"] if event else None
        for ref in sorted(by_event[event_id], key=lambda r: (r["component"], r["path"])):
            if event is None:
                agreement = "UNRESOLVED"
            elif ref["asserted_at"] is None:
                # The component carries no clock of its own. Honest, not a finding.
                agreement = "NO_ASSERTION"
            elif register is None:
                agreement = "REGISTER_UNKNOWN"
            elif ref["asserted_at"] == register:
                agreement = "AGREES"
            else:
                agreement = "DISAGREES"
            matrix.append({
                "event_id": event_id,
                "event_kind": event["kind"] if event else "UNKNOWN",
                "register_observed_at": _iso(register),
                "asserting_component": ref["component"],
                "asserting_path": ref["path"],
                "asserted_at": _iso(ref["asserted_at"]),
                "agreement": agreement,
            })
            if agreement == "DISAGREES":
                findings.append(_finding(
                    "TIMELINE_DISAGREEMENT", event_id,
                    f"{ref['component']} ({ref['path']}) asserts {_iso(ref['asserted_at'])} "
                    f"for event {event_id!r}, but the shared register records "
                    f"{_iso(register)}; the components do not agree on this timeline point",
                    ref["component"], cites=[event_id]))
            elif agreement == "REGISTER_UNKNOWN":
                findings.append(_finding(
                    "REGISTER_UNKNOWN_BUT_ASSERTED", event_id,
                    f"{ref['component']} ({ref['path']}) asserts "
                    f"{_iso(ref['asserted_at'])} for event {event_id!r}, but the shared "
                    f"register leaves observed_at UNKNOWN; the register is not updated "
                    f"from a component assertion -- reconcile the export instead",
                    ref["component"], cites=[event_id]))
    return sorted(matrix, key=lambda r: (r["event_id"], r["asserting_component"],
                                         r["asserting_path"]))


def check_unknown_timestamps(case, findings):
    """An event with no observed time stays UNKNOWN and is reported unschedulable."""
    unorderable = []
    referenced = {r["event_id"] for r in collect_eventrefs(case)}
    for event_id in sorted(case["events"]):
        event = case["events"][event_id]
        if event["observed_at"] is not None:
            continue
        unorderable.append(event_id)
        findings.append(_finding(
            "UNORDERABLE_EVENT", event_id,
            f"event {event_id!r} ({event['kind']}) has no observed timestamp; it stays "
            f"UNKNOWN and is excluded from ordering checks. It is NOT placed at the "
            f"start of the timeline and NOT treated as satisfied"
            + ("" if event_id in referenced else "; it is also unreferenced by any component"),
            cites=[event_id]))
    return unorderable


def _slot_times(case, slots):
    """Resolve {slot: [event_id, ...]} to {slot: [(event_id, time_or_None), ...]}."""
    out = {}
    for slot, ids in slots.items():
        rows = []
        for eid in ids:
            event = case["events"].get(eid)
            rows.append((eid, event["observed_at"] if event else None))
        out[slot] = sorted(rows, key=lambda r: r[0])
    return out


def _apply_rules(rules, slots, scope, findings, results):
    for earlier_slot, later_slot, rule_id, why in rules:
        for a_id, a_t in slots.get(earlier_slot, []):
            for b_id, b_t in slots.get(later_slot, []):
                if a_id == b_id:
                    continue
                if a_t is None or b_t is None:
                    # An unknown endpoint is neither a pass nor a violation.
                    results.append({"scope": scope, "rule": rule_id, "earlier": a_id,
                                    "later": b_id, "result": "UNKNOWN", "why": why})
                    continue
                ok = a_t <= b_t
                results.append({"scope": scope, "rule": rule_id, "earlier": a_id,
                                "later": b_id,
                                "result": "HOLDS" if ok else "VIOLATED", "why": why})
                if not ok:
                    findings.append(_finding(
                        "ORDERING_INVERSION", f"{a_id}>{b_id}",
                        f"{rule_id} ({scope}): {a_id} ({_iso(a_t)}) must not be later than "
                        f"{b_id} ({_iso(b_t)}) -- {why}",
                        cites=[a_id, b_id]))


def check_ordering(case, findings):
    """Ordering constraints, scoped so that legitimately-independent work stays legitimate."""
    results = []
    rel = case["release"]
    dep_env = rel["deployment"]["environment"]
    release_slots = _slot_times(case, {
        "source_approved": [rel["source"]["approved"]["event_id"]],
        "build_started": [rel["build"]["started"]["event_id"]],
        "build_finished": [rel["build"]["finished"]["event_id"]],
        "deployment": [rel["deployment"]["deployed"]["event_id"]],
        "verification_same_environment": [
            v["performed"]["event_id"] for v in case["verifications"]
            if v["environment"] == dep_env],
    })
    _apply_rules(RELEASE_ORDERING_RULES, release_slots, "release", findings, results)

    for svc in sorted(case["recovery"]["services"], key=lambda s: s["service_id"]):
        ex = svc["exercise"]
        if ex is None:
            continue
        biz = ex["business_verification"]
        service_slots = _slot_times(case, {
            "disruption": [ex["disruption"]["event_id"]],
            "restored_data_as_of": [ex["restored_data_as_of"]["event_id"]],
            "restore_completed": [ex["restore_completed"]["event_id"]],
            "dependency_verification": [d["verified"]["event_id"]
                                        for d in ex["dependency_results"]],
            "business_verification": [biz["event_id"]] if biz else [],
        })
        _apply_rules(SERVICE_ORDERING_RULES, service_slots,
                     f"service:{svc['service_id']}", findings, results)

    return sorted(results, key=lambda r: (r["scope"], r["rule"], r["earlier"], r["later"]))


def check_environment_agreement(case, findings):
    """The order's 'environment difference': verified where vs. deployed where."""
    dep = case["release"]["deployment"]
    dep_env = dep["environment"]
    art = case["release"]["artifact"]
    view = {
        "deployment_id": dep["deployment_id"],
        "deployment_environment": dep_env,
        "deployed_version": dep["observed_version"],
        "deployed_sha256": dep["observed_sha256"],
        "verifications": [],
    }
    if dep_env is not None and dep_env not in case["environments"]:
        findings.append(_finding(
            "UNRESOLVED_ENVIRONMENT", str(dep_env),
            f"deployment {dep['deployment_id']!r} names environment {dep_env!r}, which is "
            f"not described in case.environments", "environment"))

    passed_envs = set()
    for ver in case["verifications"]:
        row = {"verification_id": ver["verification_id"],
               "environment": ver["environment"], "outcome": ver["outcome"],
               "artifact_version": ver["artifact_version"],
               "same_environment_as_deployment": ver["environment"] == dep_env}
        view["verifications"].append(row)
        if ver["environment"] is not None and ver["environment"] not in case["environments"]:
            findings.append(_finding(
                "UNRESOLVED_ENVIRONMENT", str(ver["environment"]),
                f"verification {ver['verification_id']!r} names environment "
                f"{ver['environment']!r}, which is not described in case.environments",
                "environment"))
        if ver["outcome"] == "PASSED":
            passed_envs.add(ver["environment"])
        if (ver["artifact_version"] is not None
                and dep["observed_version"] is not None
                and ver["artifact_version"] != dep["observed_version"]):
            findings.append(_finding(
                "VERSION_DIFFERENCE", ver["verification_id"],
                f"verification {ver['verification_id']!r} exercised version "
                f"{ver['artifact_version']!r} but the deployment records "
                f"{dep['observed_version']!r}; the verification does not cover what ran",
                "environment", cites=[ver["verification_id"], dep["deployment_id"]]))

    # Artifact-vs-deployment record agreement (provenance side of the same question).
    if art["version"] is not None and dep["observed_version"] is not None \
            and art["version"] != dep["observed_version"]:
        findings.append(_finding(
            "VERSION_DIFFERENCE", dep["deployment_id"],
            f"artifact {art['artifact_id']!r} is version {art['version']!r} but "
            f"deployment {dep['deployment_id']!r} observed {dep['observed_version']!r}",
            "provenance", cites=[art["artifact_id"], dep["deployment_id"]]))
    if art["sha256"] is not None and dep["observed_sha256"] is not None \
            and art["sha256"] != dep["observed_sha256"]:
        findings.append(_finding(
            "DIGEST_DIFFERENCE", dep["deployment_id"],
            f"artifact digest {art['sha256']} does not match the digest observed at "
            f"deployment {dep['observed_sha256']}",
            "provenance", cites=[art["artifact_id"], dep["deployment_id"]]))

    # The named deliverable of this order: verification ran somewhere else.
    if passed_envs and dep_env is not None and dep_env not in passed_envs:
        findings.append(_finding(
            "ENVIRONMENT_DIFFERENCE", dep_env,
            f"every PASSED verification ran in {sorted(passed_envs)}, but the release was "
            f"deployed to {dep_env!r}; a pass in another environment is not evidence about "
            f"the environment that actually ran the release",
            "environment", cites=[dep["deployment_id"]]))
    if not case["verifications"]:
        findings.append(_finding(
            "NO_VERIFICATION_RECORD", dep["deployment_id"],
            f"deployment {dep['deployment_id']!r} has no verification record at all; "
            f"absence of a record is UNKNOWN, not a pass", "environment"))
    view["passed_environments"] = sorted(e for e in passed_envs if e is not None)
    view["environment_difference"] = bool(
        passed_envs and dep_env is not None and dep_env not in passed_envs)
    return view


def check_provenance_chain(case, findings):
    """The 057-shaped link check: deployment -> artifact -> build -> source."""
    rel = case["release"]
    src, bld, art, dep = rel["source"], rel["build"], rel["artifact"], rel["deployment"]
    trace = []
    if dep["artifact_id"] != art["artifact_id"]:
        findings.append(_finding(
            "BROKEN_CHAIN_LINK", dep["deployment_id"],
            f"deployment references artifact {dep['artifact_id']!r} but the case carries "
            f"artifact {art['artifact_id']!r}", "provenance"))
    else:
        trace.append(f"{dep['deployment_id']} -> {art['artifact_id']}")
    if art["build_id"] is None:
        findings.append(_finding(
            "MISSING_CHAIN_LINK", art["artifact_id"],
            f"artifact {art['artifact_id']!r} records no build_id; the build that produced "
            f"it is UNKNOWN", "provenance"))
    elif art["build_id"] != bld["build_id"]:
        findings.append(_finding(
            "BROKEN_CHAIN_LINK", art["artifact_id"],
            f"artifact references build {art['build_id']!r} but the case carries build "
            f"{bld['build_id']!r}", "provenance"))
    else:
        trace.append(f"{art['artifact_id']} -> {bld['build_id']}")
    if bld["source_id"] is None:
        findings.append(_finding(
            "MISSING_CHAIN_LINK", bld["build_id"],
            f"build {bld['build_id']!r} records no source_id; the source revision is UNKNOWN",
            "provenance"))
    elif bld["source_id"] != src["source_id"]:
        findings.append(_finding(
            "BROKEN_CHAIN_LINK", bld["build_id"],
            f"build references source {bld['source_id']!r} but the case carries source "
            f"{src['source_id']!r}", "provenance"))
    else:
        trace.append(f"{bld['build_id']} -> {src['source_id']}")

    # Compare repository and revision independently -- a matching commit on a
    # different repository is still a reconciliation question.
    if bld["observed_revision"] is not None and src["approved_revision"] is not None \
            and bld["observed_revision"] != src["approved_revision"]:
        findings.append(_finding(
            "REVISION_DIFFERENCE", bld["build_id"],
            f"build observed revision {bld['observed_revision']} but the approval record "
            f"identifies {src['approved_revision']}", "provenance"))
    if bld["observed_repository"] is not None and src["repository"] is not None \
            and bld["observed_repository"] != src["repository"]:
        findings.append(_finding(
            "REVISION_DIFFERENCE", bld["build_id"],
            f"build observed repository {bld['observed_repository']!r} but the source "
            f"record names {src['repository']!r}", "provenance"))
    if bld["input_coverage"] != "declared_complete":
        findings.append(_finding(
            "INPUT_COVERAGE_INCOMPLETE", bld["build_id"],
            f"build {bld['build_id']!r} declares input_coverage="
            f"{bld['input_coverage']!r}; the recorded input inventory is not complete",
            "provenance"))
    return {"trace": trace, "linked": len(trace) == 3}


def _evidence_support(case, evidence_id):
    """Is a cited source actually usable support, or does it stay UNKNOWN?

    Mirrors UIOWA-057: interview evidence without artifact corroboration remains
    UNKNOWN. A synthetic row supports a synthetic rehearsal and nothing further.
    """
    if evidence_id is None:
        return "ABSENT", "no source cited"
    row = case["evidence"].get(evidence_id)
    if row is None:
        return "UNRESOLVED", f"source {evidence_id!r} is not in the evidence register"
    if row["kind"] == "interview":
        return "UNKNOWN", (f"source {evidence_id!r} is interview evidence; without artifact "
                           f"corroboration it remains UNKNOWN")
    if row["captured_at"] is None:
        return "UNKNOWN", (f"source {evidence_id!r} has no capture time; its provenance "
                           f"cannot be placed")
    return "EVIDENCED", f"source {evidence_id!r} ({row['kind']}, {row['locator']})"


def _resolved_time(case, ref):
    """The register's time for an eventref, or None if unknown/unresolved."""
    if ref is None:
        return None
    event = case["events"].get(ref["event_id"])
    return event["observed_at"] if event else None


def check_recovery_claims(case, findings):
    """THE check this order turns on: does a recovery claim follow a real record?

    A claim is supported only when (a) the event exists in the shared register,
    (b) it has a known timestamp, and (c) its cited source resolves to usable
    evidence. Anything short of that is reported as an unsupported claim and the
    derived status is held down. The status is DERIVED here, never asserted by
    the input -- there is no field an input can set to claim DEMONSTRATED.

    SEMANTICS ARE UIOWA-068'S, NOT NEWLY INVENTED ONES. This was a real defect,
    found by actually executing `assess_recovery.py` on this kit's projection
    instead of only matching its field names:

        RTO is measured to BUSINESS-FUNCTION VERIFICATION, not to technical
        restore completion.

    Measuring to `restore_completed` reports a technical restore time as though
    it were the recovery time -- precisely the conflation UIOWA-068 exists to
    prevent. The technical restore instant is still reported, in its own field,
    so nothing is lost; it just is not called RTO. `conformance.py` executes the
    sibling tool and fails if these two ever drift apart again.

    Where this kit is STRICTER than UIOWA-068 the divergence is declared in
    `conformance.py` and checked for direction: stricter is allowed, looser is
    never allowed.
    """
    services = {s["service_id"]: s for s in case["recovery"]["services"]}
    results = []
    for sid in sorted(services):
        svc = services[sid]
        row = {
            "service_id": sid, "name": svc["name"],
            "business_function": svc["business_function"],
            "dependencies": list(svc["dependencies"]),
            "target_rpo_minutes": svc["target_rpo_minutes"],
            "target_rto_minutes": svc["target_rto_minutes"],
            "backup_status": "UNKNOWN", "restoration_status": "NOT_DEMONSTRATED",
            "observed_rpo_minutes": None, "rpo_result": "UNKNOWN",
            "observed_rto_minutes": None, "rto_result": "UNKNOWN",
            # Kept separate from RTO on purpose. A technical restore is not a
            # business recovery, and collapsing the two is the defect above.
            "technical_restore_completed_at": None,
            "observed_technical_restore_minutes": None,
            "dependency_verification": (
                "NOT_APPLICABLE" if not svc["dependencies"] else "UNKNOWN"),
            "business_verification": "NOT_EVIDENCED", "gaps": [],
        }

        for dep_id in svc["dependencies"]:
            if dep_id not in services:
                findings.append(_finding(
                    "UNRESOLVED_DEPENDENCY", f"{sid}->{dep_id}",
                    f"service {sid!r} declares dependency {dep_id!r}, which is not a "
                    f"service in this case; its recovery state is UNKNOWN", "recovery"))
                row["gaps"].append(f"dependency {dep_id} is not in scope of this case")

        # --- backup ---------------------------------------------------------
        bstate, bwhy = _evidence_support(case, svc["backup"]["evidence_id"])
        btime = _resolved_time(case, svc["backup"]["last_successful"])
        if bstate == "EVIDENCED" and btime is not None:
            row["backup_status"] = "EVIDENCED"
        else:
            # UIOWA-068 accepts any non-empty evidence id here; this kit also
            # requires the id to RESOLVE and not to be interview-only. Stricter.
            row["backup_status"] = "PARTIAL"
            row["gaps"].append(
                f"backup completion not evidenced: {bwhy}" if bstate != "EVIDENCED"
                else "backup completion has no observed timestamp")
        row["last_successful_backup_at"] = _iso(btime)

        ex = svc["exercise"]
        if ex is None:
            row["exercise_id"] = None
            row["gaps"].append("no restoration exercise recorded; restoration is "
                               "NOT_DEMONSTRATED, which is an absence of evidence and "
                               "not a failed exercise")
            if row["backup_status"] == "EVIDENCED":
                row["gaps"].append("a successful backup does not demonstrate restoration")
            results.append(row)
            continue
        row["exercise_id"] = ex["exercise_id"]

        disruption = _resolved_time(case, ex["disruption"])
        restored_pit = _resolved_time(case, ex["restored_data_as_of"])
        restore_done = _resolved_time(case, ex["restore_completed"])
        row["technical_restore_completed_at"] = _iso(restore_done)

        if restore_done is None:
            row["gaps"].append("restore completion has no observed timestamp; "
                               "restoration stays UNKNOWN rather than assumed complete")

        # --- business-function verification claim (resolved FIRST: the RTO
        #     clock and the dependency lateness check both depend on it) -------
        biz_time = None
        if ex["business_verification"] is None:
            row["gaps"].append("business-function verification was not attempted in the "
                               "records; it stays NOT_EVIDENCED")
        else:
            bref = ex["business_verification"]
            bevent = case["events"].get(bref["event_id"])
            biz_time = _resolved_time(case, bref)
            bsrc = bevent["evidence_id"] if bevent else None
            vstate, vwhy = _evidence_support(case, bsrc)
            if bevent is None:
                reason = f"event {bref['event_id']!r} is not in the shared event register"
            elif biz_time is None:
                reason = "the verification event has no observed timestamp"
            elif vstate != "EVIDENCED":
                reason = vwhy
            else:
                reason = None
            if reason is None:
                row["business_verification"] = "EVIDENCED"
            else:
                findings.append(_finding(
                    "UNSUPPORTED_RECOVERY_CLAIM", f"{sid}:business_verification",
                    f"service {sid!r} claims its business function was verified after "
                    f"recovery, but the claim is not carried by a verification record "
                    f"({reason}); business_verification is held at NOT_EVIDENCED and "
                    f"restoration cannot reach DEMONSTRATED on this record set",
                    "recovery", cites=[bref["event_id"]]))
                row["gaps"].append(f"business-function verification claimed but "
                                   f"unsupported: {reason}")

        # --- RPO / RTO: arithmetic over observed records only, never estimated
        if disruption is not None and restored_pit is not None:
            row["observed_rpo_minutes"] = int((disruption - restored_pit).total_seconds() // 60)
            if svc["target_rpo_minutes"] is not None:
                row["rpo_result"] = ("MEETS_TARGET"
                                     if row["observed_rpo_minutes"] <= svc["target_rpo_minutes"]
                                     else "EXCEEDS_TARGET")
        else:
            row["gaps"].append("observed RPO cannot be computed from the supplied records")

        # RTO runs to the BUSINESS-FUNCTION verification (UIOWA-068's definition).
        if disruption is not None and biz_time is not None:
            row["observed_rto_minutes"] = int((biz_time - disruption).total_seconds() // 60)
            if svc["target_rto_minutes"] is not None:
                row["rto_result"] = ("MEETS_TARGET"
                                     if row["observed_rto_minutes"] <= svc["target_rto_minutes"]
                                     else "EXCEEDS_TARGET")
        else:
            row["gaps"].append("observed RTO cannot be computed: it runs to business-"
                               "function verification, which is not recorded here. The "
                               "technical restore time is reported separately and is NOT "
                               "an RTO")
        if disruption is not None and restore_done is not None:
            row["observed_technical_restore_minutes"] = int(
                (restore_done - disruption).total_seconds() // 60)

        # --- dependency verification claims ---------------------------------
        if svc["dependencies"]:
            claimed = {dr["dependency_id"]: dr for dr in ex["dependency_results"]}
            missing, late = [], []
            for dep_id in svc["dependencies"]:
                dr = claimed.get(dep_id)
                if dr is None:
                    missing.append(dep_id)
                    row["gaps"].append(f"dependency {dep_id} has no verification record")
                    continue
                state, why = _evidence_support(case, dr["evidence_id"])
                when = _resolved_time(case, dr["verified"])
                if state != "EVIDENCED" or when is None:
                    missing.append(dep_id)
                    reason = why if state != "EVIDENCED" else "no observed verification time"
                    findings.append(_finding(
                        "UNSUPPORTED_RECOVERY_CLAIM", f"{sid}:dependency:{dep_id}",
                        f"service {sid!r} claims dependency {dep_id!r} was verified, but "
                        f"the claim is not carried by a verification record ({reason}); "
                        f"the claim is reported unsupported and does not raise the status",
                        "recovery", cites=[dr["verified"]["event_id"]]))
                    row["gaps"].append(f"dependency {dep_id} verification claimed but "
                                       f"unsupported: {reason}")
                elif biz_time is not None and when > biz_time:
                    late.append(dep_id)
            for dr in ex["dependency_results"]:
                if dr["dependency_id"] not in svc["dependencies"]:
                    findings.append(_finding(
                        "UNDECLARED_DEPENDENCY_RESULT", f"{sid}:{dr['dependency_id']}",
                        f"service {sid!r} carries a verification result for "
                        f"{dr['dependency_id']!r}, which it does not declare as a "
                        f"dependency; the records disagree about the dependency set",
                        "recovery"))
            if missing:
                row["dependency_verification"] = "PARTIAL"
            elif late:
                # UIOWA-068's name for it; the ordering rule reports it too.
                row["dependency_verification"] = "INCONSISTENT"
                row["gaps"].append("dependency verified after business-function "
                                   "verification: " + ", ".join(sorted(late)))
            else:
                row["dependency_verification"] = "EVIDENCED"

        # --- derived status (never asserted by the input) -------------------
        # Deliberately matches UIOWA-068: backup evidence is NOT part of this
        # ladder, because a backup does not demonstrate a restoration. That is
        # 068's design decision and re-deciding it here would be the drift this
        # kit exists to prevent.
        complete = (disruption is not None
                    and restored_pit is not None
                    and restore_done is not None
                    and row["business_verification"] == "EVIDENCED"
                    and row["dependency_verification"] in ("EVIDENCED", "NOT_APPLICABLE"))
        row["restoration_status"] = "DEMONSTRATED" if complete else "PARTIAL"
        results.append(row)
    return results


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------

def _iso(dt):
    return None if dt is None else dt.astimezone(datetime.timezone.utc).isoformat()


def assess(case):
    findings = []
    provenance = check_provenance_chain(case, findings)
    check_source_ids(case, findings)
    check_id_collisions(case, findings)
    agreement_matrix = check_timeline_agreement(case, findings)
    unorderable = check_unknown_timestamps(case, findings)
    ordering = check_ordering(case, findings)
    environment = check_environment_agreement(case, findings)
    recovery = check_recovery_claims(case, findings)

    findings.sort(key=lambda f: (f["class"], f["code"], f["subject"], f["detail"]))
    contradictions = [f for f in findings if f["class"] == "contradiction"]
    gaps = [f for f in findings if f["class"] == "gap"]
    # Aggregate preserves contradiction, then gap. No average, no score, no ranking.
    if contradictions:
        status = "CONTRADICTIONS"
    elif gaps:
        status = "GAPS"
    else:
        status = "AGREED"

    return {
        "case_id": case["case_id"],
        "data_class": case["data_class"],
        "as_of": _iso(case["as_of"]),
        "fiction_notice": case["fiction_notice"],
        "status": status,
        "provenance": provenance,
        "environment": environment,
        "recovery": {"assessment_id": case["recovery"]["assessment_id"],
                     "services": recovery},
        "timeline": {
            "agreement_matrix": agreement_matrix,
            "ordering_checks": ordering,
            "unorderable_events": unorderable,
            "events_total": len(case["events"]),
            "events_with_known_time": sum(
                1 for e in case["events"].values() if e["observed_at"] is not None),
        },
        "findings": findings,
        "summary": {
            "contradiction_count": len(contradictions),
            "gap_count": len(gaps),
            "finding_codes": sorted({f["code"] for f in findings}),
            "services_total": len(recovery),
            "restoration_demonstrated": sum(
                1 for r in recovery if r["restoration_status"] == "DEMONSTRATED"),
            "restoration_partial": sum(
                1 for r in recovery if r["restoration_status"] == "PARTIAL"),
            "restoration_not_demonstrated": sum(
                1 for r in recovery if r["restoration_status"] == "NOT_DEMONSTRATED"),
        },
        "interpretation_boundary": {
            "agreement_is_not_correctness": True,
            "exit_zero_is_not_a_release_approval": True,
            "backup_completion_is_restoration_proof": False,
            "missing_evidence_is_failure": False,
            "missing_evidence_is_a_pass": False,
            "live_restore_performed": False,
            "university_finding": False,
            "maturity_or_confidence_score_emitted": False,
            "individual_performance_rated": False,
        },
    }


EXIT_AGREED, EXIT_FINDINGS, EXIT_MALFORMED = 0, 1, 2


def exit_code(report):
    return EXIT_AGREED if report["status"] == "AGREED" else EXIT_FINDINGS


# ---------------------------------------------------------------------------
# Projections -- the same events in each component's own contract
# ---------------------------------------------------------------------------

def project_provenance(case):
    """Emit a UIOWA-057-shaped assessment packet from this case.

    Field names mirror that kit's packet.schema.json so the two compose without a
    fourth vocabulary. Timestamps come from the shared register, so the packet
    this produces is by construction consistent with the recovery projection.
    """
    rel = case["release"]
    src, bld, art, dep = rel["source"], rel["build"], rel["artifact"], rel["deployment"]
    reg = case["events"]

    def at(ref):
        event = reg.get(ref["event_id"])
        return _iso(event["observed_at"]) if event else None

    return {
        "schema_version": 1,
        "packet_id": f"{case['case_id']}-provenance",
        "data_class": case["data_class"],
        "evidence": [
            {"id": e["evidence_id"], "locator": e["locator"], "owner_role": e["owner_role"],
             "kind": e["kind"], "captured_at": _iso(e["captured_at"])}
            for e in sorted(case["evidence"].values(), key=lambda r: r["evidence_id"])
        ],
        "sources": [{
            "id": src["source_id"], "repository": src["repository"],
            "revision": src["revision"], "approved_revision": src["approved_revision"],
            "approved_at": at(src["approved"]),
            "approval_evidence_id": src["approval_evidence_id"],
        }],
        "builds": [{
            "id": bld["build_id"], "source_id": bld["source_id"],
            "observed_repository": bld["observed_repository"],
            "observed_revision": bld["observed_revision"],
            "builder_id": bld["builder_id"], "recipe_uri": None, "recipe_sha256": None,
            "started_at": at(bld["started"]), "finished_at": at(bld["finished"]),
            "evidence_id": bld["evidence_id"], "input_coverage": bld["input_coverage"],
            "materials": [],
        }],
        "artifacts": [{
            "id": art["artifact_id"], "build_id": art["build_id"],
            "version": art["version"], "sha256": art["sha256"], "local_path": None,
            "evidence_id": art["evidence_id"],
        }],
        "deployments": [{
            "id": dep["deployment_id"], "artifact_id": dep["artifact_id"],
            "environment": dep["environment"],
            "observed_version": dep["observed_version"],
            "observed_sha256": dep["observed_sha256"],
            "observed_at": at(dep["deployed"]), "evidence_id": dep["evidence_id"],
        }],
    }


def project_recovery(case):
    """Emit a UIOWA-068-shaped recovery-records file from this case."""
    reg = case["events"]

    def at(ref):
        if ref is None:
            return None
        event = reg.get(ref["event_id"])
        return _iso(event["observed_at"]) if event else None

    services = []
    for svc in sorted(case["recovery"]["services"], key=lambda s: s["service_id"]):
        ex = svc["exercise"]
        exercise = None
        if ex is not None:
            bizref = ex["business_verification"]
            biz_event = reg.get(bizref["event_id"]) if bizref else None
            exercise = {
                "exercise_id": ex["exercise_id"],
                "disruption_at": at(ex["disruption"]),
                "restored_data_as_of": at(ex["restored_data_as_of"]),
                "restore_completed_at": at(ex["restore_completed"]),
                "business_verified_at": at(bizref),
                "business_verification_evidence_id": (
                    biz_event["evidence_id"] if biz_event else None),
                "dependency_results": [
                    {"dependency_id": dr["dependency_id"], "verified_at": at(dr["verified"]),
                     "evidence_id": dr["evidence_id"]}
                    for dr in sorted(ex["dependency_results"],
                                     key=lambda d: d["dependency_id"])
                ],
            }
        services.append({
            "service_id": svc["service_id"], "name": svc["name"],
            "business_function": svc["business_function"],
            "target_rpo_minutes": svc["target_rpo_minutes"],
            "target_rto_minutes": svc["target_rto_minutes"],
            "dependencies": list(svc["dependencies"]),
            "backup": {"last_successful_at": at(svc["backup"]["last_successful"]),
                       "evidence_id": svc["backup"]["evidence_id"]},
            "exercise": exercise,
        })
    return {"assessment_id": case["recovery"]["assessment_id"],
            "synthetic": case["data_class"] == "synthetic", "services": services}


def project_environment(case):
    """Emit the environment view: what ran where, and what was verified where."""
    dep = case["release"]["deployment"]
    reg = case["events"]
    rows = []
    for ver in sorted(case["verifications"], key=lambda v: v["verification_id"]):
        event = reg.get(ver["performed"]["event_id"])
        rows.append({
            "verification_id": ver["verification_id"], "environment": ver["environment"],
            "artifact_version": ver["artifact_version"], "outcome": ver["outcome"],
            "performed_at": _iso(event["observed_at"]) if event else None,
            "evidence_id": ver["evidence_id"],
            "covers_deployment_environment": ver["environment"] == dep["environment"],
        })
    return {
        "case_id": case["case_id"],
        "environments": [case["environments"][k] for k in sorted(case["environments"])],
        "deployment": {"deployment_id": dep["deployment_id"],
                       "environment": dep["environment"],
                       "observed_version": dep["observed_version"]},
        "verifications": rows,
    }


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def render_csv(report):
    """The agreement matrix -- the reviewer's evidence that the components align."""
    buf = io.StringIO()
    cols = ["event_id", "event_kind", "register_observed_at", "asserting_component",
            "asserting_path", "asserted_at", "agreement"]
    writer = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    writer.writeheader()
    for row in report["timeline"]["agreement_matrix"]:
        writer.writerow({c: ("" if row[c] is None else row[c]) for c in cols})
    return buf.getvalue()


def _cell(value):
    """Escape a Markdown table cell.

    The findings table renders operator-supplied identifiers (environment names,
    service ids, subjects). One of those containing a pipe silently breaks the
    table and shifts every later column -- a reviewer then reads the wrong value
    under the wrong heading. Escape every cell, not just the prose one.
    """
    if value is None:
        return ""
    return str(value).replace("\\", "\\\\").replace("|", "\\|")


def render_markdown(report):
    out = []
    w = out.append
    w(f"# Integrated release-and-recovery case — {report['case_id']}")
    w("")
    w(f"> {report['fiction_notice']}")
    w("")
    w(f"**Cross-component status: `{report['status']}`** · "
      f"{report['summary']['contradiction_count']} contradiction(s), "
      f"{report['summary']['gap_count']} gap(s) · as of `{report['as_of']}`")
    w("")
    w("`AGREED` means the supplied records do not contradict each other. It is not a "
      "release approval, a recovery certification, or a statement that the release was "
      "safe. No maturity score, confidence score or individual rating is produced.")
    w("")

    w("## 1. Provenance chain (UIOWA-057 view)")
    w("")
    trace = report["provenance"]["trace"]
    w(f"- Chain: `{' -> '.join(trace) if trace else 'NOT LINKED'}`")
    w(f"- Fully linked: **{'yes' if report['provenance']['linked'] else 'no'}**")
    w("")

    env = report["environment"]
    w("## 2. Environment view")
    w("")
    w(f"- Deployed `{_cell(env['deployed_version'])}` to "
      f"**`{_cell(env['deployment_environment'])}`**")
    w(f"- Verifications passed in: "
      f"{', '.join('`%s`' % e for e in env['passed_environments']) or '_none_'}")
    w(f"- Environment difference: "
      f"**{'YES' if env['environment_difference'] else 'no'}**")
    w("")
    w("| Verification | Environment | Version | Outcome | Covers deployed env |")
    w("|---|---|---|---|---|")
    for row in env["verifications"]:
        w(f"| `{_cell(row['verification_id'])}` | `{_cell(row['environment'])}` | "
          f"`{_cell(row['artifact_version'])}` | **{_cell(row['outcome'])}** | "
          f"{'yes' if row['same_environment_as_deployment'] else 'no'} |")
    w("")

    w("## 3. Recovery evidence (UIOWA-068 ladder)")
    w("")
    # Technical restore gets its own column so a reader cannot mistake it for the
    # RTO. They are different measurements and the gap between them is the point.
    w("| Service | Backup | Restoration | Observed RPO | Observed RTO "
      "(to business verification) | Technical restore | Dependencies | "
      "Business function |")
    w("|---|---|---|---|---|---|---|---|")
    for svc in report["recovery"]["services"]:
        rpo = ("UNKNOWN" if svc["observed_rpo_minutes"] is None
               else f"{svc['observed_rpo_minutes']} min ({svc['rpo_result']})")
        rto = ("UNKNOWN" if svc["observed_rto_minutes"] is None
               else f"{svc['observed_rto_minutes']} min ({svc['rto_result']})")
        tech = ("UNKNOWN" if svc["observed_technical_restore_minutes"] is None
                else f"{svc['observed_technical_restore_minutes']} min")
        w(f"| `{_cell(svc['service_id'])}` | {_cell(svc['backup_status'])} | "
          f"**{_cell(svc['restoration_status'])}** | {rpo} | {rto} | {tech} | "
          f"{_cell(svc['dependency_verification'])} | "
          f"{_cell(svc['business_verification'])} |")
    w("")
    for svc in report["recovery"]["services"]:
        if svc["gaps"]:
            w(f"**`{svc['service_id']}` evidence gaps**")
            w("")
            for gap in svc["gaps"]:
                w(f"- {gap}")
            w("")

    tl = report["timeline"]
    w("## 4. Timeline agreement")
    w("")
    w(f"- Events in the shared register: **{tl['events_total']}** "
      f"({tl['events_with_known_time']} with a known time)")
    if tl["unorderable_events"]:
        w(f"- **Unorderable (UNKNOWN time, excluded from ordering):** "
          f"{', '.join('`%s`' % e for e in tl['unorderable_events'])}")
    disagreements = [r for r in tl["agreement_matrix"] if r["agreement"] == "DISAGREES"]
    w(f"- Component assertions checked: **{len(tl['agreement_matrix'])}** · "
      f"disagreements: **{len(disagreements)}**")
    violated = [r for r in tl["ordering_checks"] if r["result"] == "VIOLATED"]
    unknown_rules = [r for r in tl["ordering_checks"] if r["result"] == "UNKNOWN"]
    w(f"- Ordering constraints: **{len(violated)}** violated, "
      f"**{len(unknown_rules)}** UNKNOWN (an unknown endpoint is neither a pass nor a "
      f"violation)")
    w("")

    w("## 5. Findings")
    w("")
    if not report["findings"]:
        w("_No contradictions and no gaps under this model._")
    else:
        w("| Class | Code | Subject | Component | Detail |")
        w("|---|---|---|---|---|")
        for f in report["findings"]:
            w(f"| {_cell(f['class'])} | `{_cell(f['code'])}` | `{_cell(f['subject'])}` | "
              f"{_cell(f['component'])} | {_cell(f['detail'])} |")
    w("")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def contract_description():
    return {
        "schema_version": SCHEMA_VERSION,
        "root_fields": sorted(ROOT_FIELDS),
        "event_kinds": list(EVENT_KINDS),
        "evidence_kinds": list(EVIDENCE_KINDS),
        "verification_outcomes": list(VERIFICATION_OUTCOMES),
        "eventref": {"fields": list(EVENTREF_FIELDS),
                     "note": "asserted_at is the component's OWN claim; null means the "
                             "component carries no clock. The authoritative time lives "
                             "once, in events[].observed_at."},
        "ordering_rules": {
            "release_scope": [{"rule": r[2], "earlier": r[0], "later": r[1],
                               "why": r[3]} for r in RELEASE_ORDERING_RULES],
            "service_scope": [{"rule": r[2], "earlier": r[0], "later": r[1],
                               "why": r[3]} for r in SERVICE_ORDERING_RULES],
        },
        "contradiction_codes": sorted(CONTRADICTION_CODES),
        "exit_codes": {"0": "AGREED", "1": "GAPS or CONTRADICTIONS", "2": "malformed input"},
        "downstream_contracts": {
            "provenance": "UIOWA-057 revenue/uiowa_rfq_18649_release_provenance "
                          "packet.schema.json v1",
            "recovery": "UIOWA-068 revenue/uiowa_rfq_18649_recovery_evidence "
                        "fixtures/synthetic_recovery_records.json",
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="UIOWA-109 integrated release-and-recovery case: check that the "
                    "provenance, environment and recovery views of one event set agree.")
    parser.add_argument("case", nargs="?", help="path to a case JSON file")
    parser.add_argument("--format", choices=("json", "markdown", "csv"), default="markdown")
    parser.add_argument("--json-output", help="also write the full JSON report here")
    parser.add_argument("--csv-output", help="also write the agreement matrix CSV here")
    parser.add_argument("--markdown-output", help="also write the Markdown report here")
    parser.add_argument("--emit-provenance", help="write the UIOWA-057-shaped packet here")
    parser.add_argument("--emit-recovery", help="write the UIOWA-068-shaped records here")
    parser.add_argument("--emit-environment", help="write the environment view here")
    parser.add_argument("--schema", action="store_true",
                        help="print the case contract and exit")
    args = parser.parse_args(argv)

    if args.schema:
        print(json.dumps(contract_description(), indent=2, sort_keys=True))
        return EXIT_AGREED
    if not args.case:
        parser.error("a case file is required unless --schema is given")

    try:
        case = load_case(args.case)
    except CaseError as exc:
        # No report is emitted for malformed input -- never a fabricated result.
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_MALFORMED

    report = assess(case)

    for path, payload in (
        (args.emit_provenance, project_provenance(case)),
        (args.emit_recovery, project_recovery(case)),
        (args.emit_environment, project_environment(case)),
        (args.json_output, report),
    ):
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, sort_keys=True)
                fh.write("\n")
    if args.csv_output:
        with open(args.csv_output, "w", encoding="utf-8", newline="") as fh:
            fh.write(render_csv(report))
    if args.markdown_output:
        with open(args.markdown_output, "w", encoding="utf-8") as fh:
            fh.write(render_markdown(report))

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.format == "csv":
        sys.stdout.write(render_csv(report))
    else:
        sys.stdout.write(render_markdown(report))
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
