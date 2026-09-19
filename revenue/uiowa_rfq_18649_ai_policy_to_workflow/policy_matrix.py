#!/usr/bin/env python3
"""Policy-to-practice matrix generator (UIOWA-074, AI policy-to-workflow assessment).

WHY THIS EXISTS
---------------
Policy assessments fail in a predictable way: they collapse three different
things into one verdict. This tool refuses to collapse them.

    1. STATED POLICY        -- what the organization has written down.
    2. IMPLEMENTATION       -- what an assessor actually observed being done.
       EVIDENCE
    3. OPEN QUESTIONS       -- what cannot be decided without the University
                               telling us how its own policy is meant to read.

Those are three independent axes. They are carried side by side through every
output. A convenience "reading" is derived from axes 1 and 2 for leadership
discussion, but the axes are never overwritten, so any reading can be taken
apart again and argued with.

THE DISTINCTION THAT DOES THE MOST WORK
---------------------------------------
"We looked and found nothing" and "we never looked" are NOT the same cell.

    LOOKED_NONE_FOUND -> a real gap. Somebody checked; the practice is absent.
    NOT_GATHERED      -> UNKNOWN. It is not a gap, not a pass, not a zero.

Most tooling silently merges these, which manufactures gaps out of unfinished
fieldwork (or, worse, manufactures passes out of it). Here NOT_GATHERED is a
first-class state, is excluded from every gap and strength count, and forces a
caution line into the summary so an unfinished assessment cannot read as a
clean one.

WHAT THIS TOOL REFUSES TO DO
----------------------------
It will not produce a maturity level, a conformance score, an "RMF coverage"
percentage, or any single number summarizing the organization. Calling
`score()` raises ScoreRefused on purpose -- the refusal is a feature with a
test behind it. It also scores no individuals; the unit of accountability here
is a ROLE.

NIST AI RMF
-----------
Referenced, not certified against:
https://www.nist.gov/itl/ai-risk-management-framework

Only the four core functions (GOVERN, MAP, MEASURE, MANAGE) are used, and only
as a sort key so leadership can group discussion. Subcategory-level mapping is
deliberately UNKNOWN -- see SOURCE_NOTES.md. Nothing here is a conformance
claim, a certification, or a peer comparison.

Python 3 standard library only. No network. Deterministic: every output is
sorted, so two runs over the same fixtures produce byte-identical files.
"""

import argparse
import csv
import json
import os
import sys
from collections import OrderedDict

# --------------------------------------------------------------------------
# Axis 1: stated policy
# --------------------------------------------------------------------------
# A policy's force is not binary. A draft is written down but does not bind;
# a superseded policy binds nothing either. Both are "not NO_POLICY" and both
# are "not in force", so they get their own class rather than being rounded to
# whichever neighbour is convenient.
POLICY_CLASSES = ("HAS_ACTIVE_POLICY", "HAS_NONBINDING_POLICY", "NO_POLICY")

POLICY_STATUS_TO_CLASS = {
    "active": "HAS_ACTIVE_POLICY",
    "draft": "HAS_NONBINDING_POLICY",
    "superseded": "HAS_NONBINDING_POLICY",
}

# --------------------------------------------------------------------------
# Axis 2: implementation evidence
# --------------------------------------------------------------------------
# Ordered weakest -> strongest. ASSERTED_ONLY is deliberately ABOVE
# LOOKED_NONE_FOUND (somebody at least claims it happens) and deliberately
# BELOW EVIDENCED_INDIRECT (a claim is not an artifact). The single most
# common dishonesty in this kind of assessment is promoting an interview
# assertion to "implemented"; the ordering here makes that promotion
# impossible without editing this list.
EVIDENCE_LEVELS = (
    "NOT_GATHERED",        # nobody looked -- UNKNOWN, never a finding
    "LOOKED_NONE_FOUND",   # somebody looked and the practice was absent
    "ASSERTED_ONLY",       # stated in interview, nothing corroborates it
    "EVIDENCED_INDIRECT",  # a related artifact implies the practice
    "EVIDENCED_DIRECT",    # the artifact itself was inspected
)

EVIDENCE_KIND_TO_LEVEL = {
    "artifact": "EVIDENCED_DIRECT",
    "record": "EVIDENCED_DIRECT",
    "config": "EVIDENCED_DIRECT",
    "log": "EVIDENCED_INDIRECT",
    "related_artifact": "EVIDENCED_INDIRECT",
    "interview": "ASSERTED_ONLY",
    "none": None,  # resolved by the `checked` flag -- see _evidence_level()
}

VALID_EVIDENCE_KINDS = tuple(sorted(EVIDENCE_KIND_TO_LEVEL))

# --------------------------------------------------------------------------
# Derived reading (leadership convenience only -- axes above are authoritative)
# --------------------------------------------------------------------------
# Fully enumerated 3 x 5 table. It is written out longhand rather than computed
# so that every combination is reviewable by a human who does not read Python,
# and so a test can assert the table is total (no combination falls through to
# a default). A default branch in this table is how "unknown" quietly becomes
# "fine".
READING_TABLE = {
    ("HAS_ACTIVE_POLICY", "EVIDENCED_DIRECT"):      "ALIGNED",
    ("HAS_ACTIVE_POLICY", "EVIDENCED_INDIRECT"):    "ALIGNED_INDIRECT",
    ("HAS_ACTIVE_POLICY", "ASSERTED_ONLY"):         "STATED_PRACTICE_UNCORROBORATED",
    ("HAS_ACTIVE_POLICY", "LOOKED_NONE_FOUND"):     "STATED_NOT_PRACTICED",
    ("HAS_ACTIVE_POLICY", "NOT_GATHERED"):          "NOT_ASSESSED",

    ("HAS_NONBINDING_POLICY", "EVIDENCED_DIRECT"):   "PRACTICE_AHEAD_OF_POLICY",
    ("HAS_NONBINDING_POLICY", "EVIDENCED_INDIRECT"): "PRACTICE_AHEAD_OF_POLICY",
    ("HAS_NONBINDING_POLICY", "ASSERTED_ONLY"):      "UNCLEAR_ON_BOTH_SIDES",
    ("HAS_NONBINDING_POLICY", "LOOKED_NONE_FOUND"):  "POLICY_NOT_IN_FORCE",
    ("HAS_NONBINDING_POLICY", "NOT_GATHERED"):       "NOT_ASSESSED",

    ("NO_POLICY", "EVIDENCED_DIRECT"):   "UNDOCUMENTED_PRACTICE",
    ("NO_POLICY", "EVIDENCED_INDIRECT"): "UNDOCUMENTED_PRACTICE",
    ("NO_POLICY", "ASSERTED_ONLY"):      "UNCLEAR_ON_BOTH_SIDES",
    ("NO_POLICY", "LOOKED_NONE_FOUND"):  "NOT_ADDRESSED",
    ("NO_POLICY", "NOT_GATHERED"):       "NOT_ASSESSED",
}

BLOCKED = "BLOCKED_ON_CLARIFICATION"

# How each reading is allowed to be counted. Note that several readings are
# neither a gap nor a strength; forcing every cell into good/bad is exactly the
# flattening this tool exists to prevent.
READING_META = OrderedDict([
    ("ALIGNED", {
        "gap": False, "strength": True, "assessed": True,
        "means": "Policy is in force and an artifact was inspected showing the practice."}),
    ("ALIGNED_INDIRECT", {
        "gap": False, "strength": True, "assessed": True,
        "means": "Policy is in force; a related artifact implies the practice. Weaker than a direct inspection."}),
    ("STATED_PRACTICE_UNCORROBORATED", {
        "gap": False, "strength": False, "assessed": True,
        "means": "Policy is in force and staff say they follow it, but nothing was found that corroborates it. Not a finding either way."}),
    ("STATED_NOT_PRACTICED", {
        "gap": True, "strength": False, "assessed": True,
        "means": "Policy is in force, an assessor looked, and the practice was absent. A real gap."}),
    ("PRACTICE_AHEAD_OF_POLICY", {
        "gap": False, "strength": True, "assessed": True,
        "means": "The practice is happening, but the policy behind it is draft or superseded. The work is real; the mandate is not."}),
    ("POLICY_NOT_IN_FORCE", {
        "gap": False, "strength": False, "assessed": True,
        "means": "A draft or superseded policy exists and the practice was not found. Not a violation -- nothing binds yet."}),
    ("UNDOCUMENTED_PRACTICE", {
        "gap": False, "strength": True, "assessed": True,
        "means": "The practice is demonstrably happening with no written policy behind it. A strength that depends on the people currently doing it."}),
    ("UNCLEAR_ON_BOTH_SIDES", {
        "gap": False, "strength": False, "assessed": True,
        "means": "Nothing binding is written and nothing corroborates the claimed practice. Needs fieldwork, not a verdict."}),
    ("NOT_ADDRESSED", {
        "gap": True, "strength": False, "assessed": True,
        "means": "No policy covers this task and an assessor confirmed the practice is absent."}),
    ("NOT_ASSESSED", {
        "gap": False, "strength": False, "assessed": False,
        "means": "UNKNOWN. No evidence was gathered for this cell. Not a gap, not a pass, not a zero."}),
    (BLOCKED, {
        "gap": False, "strength": False, "assessed": False,
        "means": "Cannot be resolved until the University answers an interpretation question. Any verdict here would be guesswork."}),
])

# Reference only. See module docstring and SOURCE_NOTES.md.
NIST_AI_RMF_URL = "https://www.nist.gov/itl/ai-risk-management-framework"
RMF_FUNCTIONS = ("GOVERN", "MAP", "MEASURE", "MANAGE")

FICTION_BANNER = (
    "FICTIONAL DATA. Example State University is an invented organization. "
    "No record here describes the University of Iowa or any real institution, "
    "policy, system, or person."
)


class FixtureError(Exception):
    """Raised when input data is malformed, orphaned, or internally inconsistent.

    Deliberately collects EVERY problem before raising. A validator that dies on
    the first error trains its operator to fix one line and rerun; a validator
    that reports all of them gets the fixture actually repaired.
    """


class ScoreRefused(Exception):
    """Raised by score(). The refusal is the point -- see refusals()."""


# --------------------------------------------------------------------------
# Loading + validation
# --------------------------------------------------------------------------

def _read_json(path):
    if not os.path.exists(path):
        raise FixtureError("missing input file: %s" % path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise FixtureError("%s is not valid JSON: %s" % (os.path.basename(path), exc))


def _require(obj, keys, label, problems):
    for key in keys:
        if key not in obj:
            problems.append("%s is missing required field %r" % (label, key))


def load_dataset(fixture_dir):
    """Load and validate the four fixture files. Returns a dict of dicts/lists."""
    policies = _read_json(os.path.join(fixture_dir, "policies.json"))
    tasks = _read_json(os.path.join(fixture_dir, "tasks.json"))
    evidence = _read_json(os.path.join(fixture_dir, "evidence.json"))
    questions = _read_json(os.path.join(fixture_dir, "questions.json"))

    problems = []
    for name, blob in (("policies.json", policies), ("tasks.json", tasks),
                       ("evidence.json", evidence), ("questions.json", questions)):
        if not isinstance(blob, list):
            problems.append("%s must contain a JSON list, got %s"
                            % (name, type(blob).__name__))
    if problems:
        raise FixtureError("; ".join(problems))

    by_policy, by_task = {}, {}

    for pol in policies:
        label = "policy %s" % pol.get("policy_id", "<no policy_id>")
        _require(pol, ["policy_id", "title", "status", "owner_role",
                       "applies_to_tasks", "rmf_functions"], label, problems)
        pid = pol.get("policy_id")
        if pid in by_policy:
            problems.append("duplicate policy_id %r" % pid)
        if pol.get("status") not in POLICY_STATUS_TO_CLASS:
            problems.append("%s has unknown status %r (expected one of %s)"
                            % (label, pol.get("status"),
                               ", ".join(sorted(POLICY_STATUS_TO_CLASS))))
        for fn in pol.get("rmf_functions", []) or []:
            if fn not in RMF_FUNCTIONS:
                problems.append("%s references unknown NIST AI RMF function %r"
                                % (label, fn))
        if pid:
            by_policy[pid] = pol

    for task in tasks:
        label = "task %s" % task.get("task_id", "<no task_id>")
        _require(task, ["task_id", "name", "accountable_role"], label, problems)
        tid = task.get("task_id")
        if tid in by_task:
            problems.append("duplicate task_id %r" % tid)
        if tid:
            by_task[tid] = task

    # Orphan checks. An evidence record pointing at an id that does not exist is
    # never silently dropped: a dropped record is an assessment finding that
    # vanished, which is worse than a crash.
    for pol in policies:
        for tid in pol.get("applies_to_tasks", []) or []:
            if tid not in by_task:
                problems.append("policy %s applies_to_tasks references unknown task %r"
                                % (pol.get("policy_id"), tid))

    for idx, ev in enumerate(evidence):
        label = "evidence[%d] %s" % (idx, ev.get("evidence_id", "<no evidence_id>"))
        _require(ev, ["evidence_id", "task_id", "kind", "locator", "observed_date"],
                 label, problems)
        if ev.get("kind") not in EVIDENCE_KIND_TO_LEVEL:
            problems.append("%s has unknown kind %r (expected one of %s)"
                            % (label, ev.get("kind"), ", ".join(VALID_EVIDENCE_KINDS)))
        if ev.get("kind") == "none" and "checked" not in ev:
            problems.append("%s has kind 'none' but no 'checked' flag -- cannot tell "
                            "'we looked and found nothing' from 'we never looked'" % label)
        if ev.get("task_id") not in by_task:
            problems.append("%s references unknown task_id %r" % (label, ev.get("task_id")))
        pid = ev.get("policy_id")
        if pid is not None and pid not in by_policy:
            problems.append("%s references unknown policy_id %r" % (label, pid))

    for idx, q in enumerate(questions):
        label = "question[%d] %s" % (idx, q.get("question_id", "<no question_id>"))
        _require(q, ["question_id", "question", "why_it_matters", "blocking",
                     "asked_of"], label, problems)
        if not isinstance(q.get("blocking"), bool):
            problems.append("%s field 'blocking' must be true or false, got %r"
                            % (label, q.get("blocking")))
        if q.get("task_id") is not None and q.get("task_id") not in by_task:
            problems.append("%s references unknown task_id %r" % (label, q.get("task_id")))
        if q.get("policy_id") is not None and q.get("policy_id") not in by_policy:
            problems.append("%s references unknown policy_id %r" % (label, q.get("policy_id")))

    if problems:
        raise FixtureError("%d fixture problem(s): %s"
                           % (len(problems), " | ".join(sorted(problems))))

    return {"policies": policies, "tasks": tasks,
            "evidence": evidence, "questions": questions,
            "by_policy": by_policy, "by_task": by_task}


# --------------------------------------------------------------------------
# Cell resolution
# --------------------------------------------------------------------------

def _evidence_level(record):
    """Map one evidence record to a level on the EVIDENCE_LEVELS scale."""
    kind = record.get("kind")
    mapped = EVIDENCE_KIND_TO_LEVEL.get(kind)
    if mapped is not None:
        return mapped
    # kind == "none": the `checked` flag is the whole distinction.
    #   checked=True  -> an assessor looked and the practice was absent (a gap)
    #   checked=False -> it was on the plan and never done (still UNKNOWN)
    return "LOOKED_NONE_FOUND" if record.get("checked") is True else "NOT_GATHERED"


def _strongest(levels):
    if not levels:
        return "NOT_GATHERED"
    return max(levels, key=EVIDENCE_LEVELS.index)


def _policy_class(policy):
    if policy is None:
        return "NO_POLICY"
    return POLICY_STATUS_TO_CLASS[policy["status"]]


def resolve_cell(policy, task, evidence, questions):
    """Resolve one (policy, task) intersection into three axes plus a reading.

    `policy` may be None, meaning "no written policy claims this task".
    """
    pid = policy["policy_id"] if policy else None
    tid = task["task_id"]

    # Evidence for this cell: matched on task, and on policy when the record
    # names one. A record with policy_id=None is evidence about the task in
    # general and counts toward any policy covering that task.
    levels = []
    used = []
    for ev in evidence:
        if ev["task_id"] != tid:
            continue
        ev_pid = ev.get("policy_id")
        if ev_pid is not None and ev_pid != pid:
            continue
        if ev_pid is None and pid is None:
            pass  # general evidence, no-policy column
        levels.append(_evidence_level(ev))
        used.append(ev["evidence_id"])

    evidence_axis = _strongest(levels)
    policy_axis = _policy_class(policy)
    reading = READING_TABLE[(policy_axis, evidence_axis)]

    # Axis 3. A blocking question overrides the READING but never erases the
    # other two axes -- `reading_if_unblocked` is kept so leadership can see
    # what the answer would change.
    cell_questions = sorted(
        q["question_id"] for q in questions
        if (q.get("task_id") in (None, tid) and q.get("policy_id") in (None, pid))
        and not (q.get("task_id") is None and q.get("policy_id") is None)
    )
    blocking = sorted(
        q["question_id"] for q in questions
        if q["question_id"] in cell_questions and q["blocking"] is True
    )

    reading_if_unblocked = reading
    if blocking:
        reading = BLOCKED

    return {
        "policy_id": pid or "(none)",
        "policy_title": policy["title"] if policy else "(no written policy covers this task)",
        "policy_status": policy["status"] if policy else "none",
        "policy_owner_role": policy["owner_role"] if policy else "UNKNOWN",
        "task_id": tid,
        "task_name": task["name"],
        "accountable_role": task["accountable_role"],
        "rmf_functions": ";".join(policy.get("rmf_functions", [])) if policy else "UNKNOWN",
        # -- the three axes, never merged --
        "policy_axis": policy_axis,
        "evidence_axis": evidence_axis,
        "open_questions": ";".join(cell_questions) if cell_questions else "",
        "blocking_questions": ";".join(blocking) if blocking else "",
        # -- derived convenience --
        "reading": reading,
        "reading_if_unblocked": reading_if_unblocked,
        "evidence_ids": ";".join(sorted(used)),
    }


def build_matrix(data):
    """Build every (policy x covered task) cell, plus a no-policy cell for any
    task that no active or nonbinding policy claims."""
    cells = []
    claimed = set()
    for pol in sorted(data["policies"], key=lambda p: p["policy_id"]):
        for tid in sorted(pol.get("applies_to_tasks", []) or []):
            claimed.add(tid)
            cells.append(resolve_cell(pol, data["by_task"][tid],
                                      data["evidence"], data["questions"]))
    for task in sorted(data["tasks"], key=lambda t: t["task_id"]):
        if task["task_id"] not in claimed:
            cells.append(resolve_cell(None, task, data["evidence"], data["questions"]))
    cells.sort(key=lambda c: (c["task_id"], c["policy_id"]))
    return cells


# --------------------------------------------------------------------------
# Summary + the refusals
# --------------------------------------------------------------------------

def refusals():
    """Everything this tool deliberately does not compute, and why.

    Carried into findings.json and the Markdown so the refusal travels with the
    deliverable instead of living only in a docstring nobody opens.
    """
    return [
        "No maturity level, readiness level, or tier is computed. The four "
        "NIST AI RMF functions are used as a sort key only; this is not a "
        "conformance assessment and the AI RMF is not a certification. "
        "Reference: " + NIST_AI_RMF_URL,
        "No single score, index, or percentage summarizing the organization is "
        "produced. Calling score() raises ScoreRefused.",
        "No percentage is reported over a denominator that includes NOT_ASSESSED "
        "cells. Counts are raw integers so an unfinished assessment cannot be "
        "read as a proportion of a complete one.",
        "NOT_ASSESSED is never counted as a gap, a pass, or a zero. It means "
        "nobody looked.",
        "An interview assertion is never promoted to implementation evidence.",
        "No individual is scored. The accountable unit is a ROLE.",
        "No peer comparison, percentile, benchmark, or 'typical institution' "
        "claim is made.",
        "NIST AI RMF subcategory-level mapping is UNKNOWN and is not invented.",
    ]


def score(*_args, **_kwargs):
    """Deliberately unimplemented. Present so the refusal is discoverable."""
    raise ScoreRefused(
        "This assessment does not produce a maturity score, conformance "
        "percentage, or single productivity/readiness number. Collapsing "
        "stated policy, implementation evidence, and open interpretation "
        "questions into one number destroys exactly the distinctions the "
        "assessment exists to make. Read summarize() instead: it reports each "
        "axis separately and keeps UNKNOWN out of every denominator."
    )


def summarize(cells, questions):
    counts = OrderedDict((r, 0) for r in READING_META)
    for cell in cells:
        counts[cell["reading"]] += 1

    gaps = sum(n for r, n in counts.items() if READING_META[r]["gap"])
    strengths = sum(n for r, n in counts.items() if READING_META[r]["strength"])
    assessed = sum(n for r, n in counts.items() if READING_META[r]["assessed"])
    not_assessed = counts["NOT_ASSESSED"]
    blocked = counts[BLOCKED]

    cautions = []
    if not_assessed:
        cautions.append(
            "%d of %d cells were never assessed. Gap and strength counts below "
            "describe ONLY the %d assessed cells. Do not read '%d gaps' as "
            "'%d gaps exist' -- unexamined ground is not clean ground."
            % (not_assessed, len(cells), assessed, gaps, gaps))
    if blocked:
        cautions.append(
            "%d cells cannot be resolved until the University answers a blocking "
            "interpretation question. They are excluded from gap and strength "
            "counts; their provisional reading is kept in reading_if_unblocked."
            % blocked)
    if assessed and not gaps and not_assessed:
        cautions.append(
            "Zero gaps among assessed cells with assessment still incomplete. "
            "This is not a clean result; it is a partial one.")

    return OrderedDict([
        ("fiction_notice", FICTION_BANNER),
        ("cells_total", len(cells)),
        ("cells_assessed", assessed),
        ("cells_not_assessed", not_assessed),
        ("cells_blocked_on_clarification", blocked),
        ("gaps_among_assessed", gaps),
        ("strengths_among_assessed", strengths),
        ("by_reading", counts),
        ("open_questions_total", len(questions)),
        ("open_questions_blocking",
         sum(1 for q in questions if q["blocking"])),
        ("cautions", cautions),
        ("refusals", refusals()),
        ("nist_ai_rmf_reference", NIST_AI_RMF_URL),
    ])


# --------------------------------------------------------------------------
# Renderers (deterministic)
# --------------------------------------------------------------------------

MATRIX_COLUMNS = [
    "task_id", "task_name", "accountable_role",
    "policy_id", "policy_title", "policy_status", "policy_owner_role",
    "rmf_functions",
    "policy_axis", "evidence_axis", "reading", "reading_if_unblocked",
    "open_questions", "blocking_questions", "evidence_ids",
]


def write_matrix_csv(cells, path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=MATRIX_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for cell in cells:
            writer.writerow(cell)


def write_questions_csv(questions, path):
    cols = ["question_id", "policy_id", "task_id", "blocking", "asked_of",
            "question", "why_it_matters"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for q in sorted(questions, key=lambda x: x["question_id"]):
            row = dict(q)
            row["policy_id"] = row.get("policy_id") or "(any)"
            row["task_id"] = row.get("task_id") or "(any)"
            writer.writerow(row)


def _md_escape(text):
    return str(text).replace("|", "\\|")


def write_matrix_md(cells, summary, questions, path):
    out = []
    a = out.append
    a("# Policy-to-practice matrix — Example State University (FICTIONAL)")
    a("")
    a("> **%s**" % FICTION_BANNER)
    a("")
    a("Prepared for leadership discussion. NIST AI RMF is used as a reference "
      "for organizing discussion, **not** as a certification checklist: "
      "<%s>." % NIST_AI_RMF_URL)
    a("")
    a("## How to read this")
    a("")
    a("Three things are kept apart on purpose and are never merged into one verdict:")
    a("")
    a("| Column | What it is |")
    a("|---|---|")
    a("| **Stated policy** | What is written down, and whether it is in force. |")
    a("| **Implementation evidence** | What an assessor actually observed. |")
    a("| **Open questions** | What the University must clarify before anyone can judge the cell. |")
    a("")
    a("`LOOKED_NONE_FOUND` (somebody checked, the practice was absent) and "
      "`NOT_GATHERED` (nobody checked) are different states. Only the first is "
      "a gap. The second stays UNKNOWN and is excluded from every count below.")
    a("")

    a("## Counts")
    a("")
    a("| Measure | Count |")
    a("|---|---|")
    for key in ("cells_total", "cells_assessed", "cells_not_assessed",
                "cells_blocked_on_clarification", "gaps_among_assessed",
                "strengths_among_assessed", "open_questions_total",
                "open_questions_blocking"):
        a("| %s | %d |" % (key.replace("_", " "), summary[key]))
    a("")
    a("Raw integers only. No percentage is reported, because a percentage "
      "implies a complete denominator and this assessment has %d unassessed cells."
      % summary["cells_not_assessed"])
    a("")

    if summary["cautions"]:
        a("### Read this before quoting any count above")
        a("")
        for caution in summary["cautions"]:
            a("- %s" % caution)
        a("")

    a("## Matrix")
    a("")
    a("| Task | Accountable role | Stated policy | Policy in force? | "
      "Implementation evidence | Reading | Open questions |")
    a("|---|---|---|---|---|---|---|")
    for cell in cells:
        a("| %s — %s | %s | %s %s | %s | %s | **%s** | %s |" % (
            _md_escape(cell["task_id"]), _md_escape(cell["task_name"]),
            _md_escape(cell["accountable_role"]),
            _md_escape(cell["policy_id"]), _md_escape(cell["policy_title"]),
            _md_escape(cell["policy_axis"]),
            _md_escape(cell["evidence_axis"]),
            _md_escape(cell["reading"]),
            _md_escape(cell["open_questions"] or "—"),
        ))
    a("")

    a("## What each reading means")
    a("")
    a("| Reading | Counts as | Meaning |")
    a("|---|---|---|")
    for reading, meta in READING_META.items():
        if reading == "NOT_ASSESSED":
            kind = "neither — UNKNOWN"
        elif meta["gap"]:
            kind = "gap"
        elif meta["strength"]:
            kind = "strength"
        elif reading == BLOCKED:
            kind = "neither — blocked"
        else:
            kind = "neither"
        a("| `%s` | %s | %s |" % (reading, kind, _md_escape(meta["means"])))
    a("")

    a("## Questions requiring University clarification")
    a("")
    a("These are not findings. They are the points where the assessor cannot "
      "honestly decide a cell without the University saying how its own policy "
      "is meant to read.")
    a("")
    a("| ID | Blocking? | Asked of | Question | Why it matters |")
    a("|---|---|---|---|---|")
    for q in sorted(questions, key=lambda x: x["question_id"]):
        a("| %s | %s | %s | %s | %s |" % (
            q["question_id"], "**YES**" if q["blocking"] else "no",
            _md_escape(q["asked_of"]), _md_escape(q["question"]),
            _md_escape(q["why_it_matters"])))
    a("")

    a("## What this assessment refuses to produce")
    a("")
    for item in summary["refusals"]:
        a("- %s" % item)
    a("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))


def write_findings_json(cells, summary, path):
    payload = OrderedDict([
        ("fiction_notice", FICTION_BANNER),
        ("nist_ai_rmf_reference", NIST_AI_RMF_URL),
        ("summary", summary),
        ("cells", cells),
    ])
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=False)
        fh.write("\n")


def run(fixture_dir, out_dir):
    data = load_dataset(fixture_dir)
    cells = build_matrix(data)
    summary = summarize(cells, data["questions"])
    os.makedirs(out_dir, exist_ok=True)
    write_matrix_csv(cells, os.path.join(out_dir, "matrix.csv"))
    write_matrix_md(cells, summary, data["questions"],
                    os.path.join(out_dir, "matrix.md"))
    write_questions_csv(data["questions"], os.path.join(out_dir, "open_questions.csv"))
    write_findings_json(cells, summary, os.path.join(out_dir, "findings.json"))
    return cells, summary


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fixtures", default=os.path.join(here, "fixtures"))
    parser.add_argument("--out", default=os.path.join(here, "sample"))
    args = parser.parse_args(argv)
    try:
        cells, summary = run(args.fixtures, args.out)
    except FixtureError as exc:
        print("FIXTURE ERROR: %s" % exc, file=sys.stderr)
        return 2
    print(FICTION_BANNER)
    print("cells=%d assessed=%d not_assessed=%d blocked=%d gaps=%d strengths=%d"
          % (summary["cells_total"], summary["cells_assessed"],
             summary["cells_not_assessed"],
             summary["cells_blocked_on_clarification"],
             summary["gaps_among_assessed"], summary["strengths_among_assessed"]))
    for caution in summary["cautions"]:
        print("CAUTION: %s" % caution)
    print("wrote matrix.csv matrix.md open_questions.csv findings.json -> %s"
          % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
