#!/usr/bin/env python3
"""Final-readout deck architecture: a deck that is checked against its report.

UIOWA-088. The order's completion test is "the deck agrees with its example
report". That is a checkable property, not a formatting preference, so this
module treats the report as the single source of truth and the deck as a set of
machine-readable CLAIMS about it. Every figure a presenter says out loud is a
claim citing a report id, and the checker fails closed on six real disagreement
classes plus the structural rules that keep a readout usable in the room.

Why fail closed: a readout deck is the artifact that outlives the engagement. A
deck that quietly drifts from its report -- a stale percentage, a dropped
priority finding, an UNKNOWN rounded into a number -- is worse than no deck,
because it is repeated by people who were not in the assessment.

Python 3 standard library only. No network. Deterministic: no clock, no RNG,
sorted traversal, so two operators get byte-identical output.
"""

import argparse
import csv
import json
import os
import sys
import textwrap
from collections import OrderedDict

UNKNOWN = "UNKNOWN"
ERROR = "error"
WARN = "warning"

# Canonical section order for the readout. The order is the argument: why we
# are here -> what it rests on -> what works -> what does not -> sequence ->
# cost -> decide. Detail goes behind it in the appendix.
CORE_SECTIONS = [
    "purpose",
    "evidence",
    "strengths",
    "priority_findings",
    "roadmap",
    "resources",
    "decisions",
]
SECTION_TITLES = {
    "purpose": "PURPOSE",
    "evidence": "EVIDENCE BASE",
    "strengths": "VALIDATED STRENGTHS",
    "priority_findings": "PRIORITY FINDINGS",
    "roadmap": "PHASED ROADMAP",
    "resources": "RESOURCE IMPLICATIONS",
    "decisions": "DECISIONS REQUESTED",
    "appendix": "APPENDIX",
}

# Executive readability budget for a core slide. Over this, the material is
# detail and belongs in the appendix -- which is exactly what the order asks.
MAX_CORE_BULLETS = 6
MAX_BULLET_CHARS = 180

RULES = OrderedDict([
    ("R001_SECTION_ORDER", "Core sections are all present, once each, in the canonical readout order."),
    ("R002_DANGLING_CITATION", "Every claim cites an id that exists in the report."),
    ("R003_FIGURE_DISAGREEMENT", "A figure stated on a slide equals the report's value and unit."),
    ("R004_UNKNOWN_FABRICATION", "A measure the report leaves UNKNOWN is not asserted as a number on a slide."),
    ("R005_OMITTED_PRIORITY_FINDING", "Every high-priority report gap is cited by at least one core slide."),
    ("R006_UNVALIDATED_STRENGTH", "A slide calls something a validated strength only if the report validated it."),
    ("R007_PHASE_DISAGREEMENT", "A recommendation's phase on a slide equals its phase in the report roadmap."),
    ("R008_MAIN_CLAIM_WITHOUT_APPENDIX", "A core slide stating a figure names an appendix slide that carries the same id."),
    ("R009_ORPHAN_APPENDIX", "Every appendix slide is reachable from at least one core slide."),
    ("R010_AGENDA_OVERRUN", "Core slide minutes fit the declared session length."),
    ("R011_MISSING_SPEAKER_NOTES", "Every core slide carries at least one speaker-note prompt."),
    ("R012_DETAIL_IN_MAIN_BODY", "Core slides stay inside the executive readability budget."),
    ("R013_UNRESOLVED_MEASURE", "A cited measure name exists on the cited report object."),
    ("R014_DECISION_UNLINKED", "A decision resolves to a recommendation whose phase agrees with the decision's."),
    ("R015_REPORT_MISMATCH", "The deck's report_ref is the report it is being checked against."),
    ("R016_AGENDA_UNDERRUN", "Core slide minutes use a reasonable share of the declared session (advisory)."),
    ("R017_ROADMAP_DEPENDENCY_UNDECLARED", "A roadmap that declares no prerequisites is reported as NOT ASSESSED, never as coherent."),
    ("R018_ROADMAP_PREREQ_AFTER_DEPENDENT", "No roadmap prerequisite sits in a later phase than the item that depends on it."),
    ("R019_ROADMAP_DEPENDENCY_CYCLE", "The roadmap's prerequisite graph is acyclic."),
    ("R020_ROADMAP_DANGLING_DEPENDENCY", "Every declared prerequisite resolves to a recommendation on the roadmap."),
])


class DeckDataError(Exception):
    """Input is not usable. Raised instead of letting a KeyError surface."""


class Issue(object):
    __slots__ = ("code", "severity", "slide", "detail")

    def __init__(self, code, severity, slide, detail):
        self.code = code
        self.severity = severity
        self.slide = slide or "-"
        self.detail = detail

    def __repr__(self):
        return "Issue(%s,%s,%s,%s)" % (self.code, self.severity, self.slide, self.detail)

    def as_dict(self):
        return {"code": self.code, "severity": self.severity, "slide": self.slide, "detail": self.detail}


# ---------------------------------------------------------------- loading

def load_json(path):
    if not os.path.exists(path):
        raise DeckDataError("file not found: %s" % path)
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
    except ValueError as exc:
        raise DeckDataError("%s is not valid JSON: %s" % (path, exc))
    if not isinstance(data, dict):
        raise DeckDataError("%s must contain a JSON object at the top level" % path)
    return data


def _require(data, keys, what):
    missing = [k for k in keys if k not in data]
    if missing:
        raise DeckDataError("%s is missing required key(s): %s" % (what, ", ".join(sorted(missing))))


def load_report(path):
    data = load_json(path)
    _require(data, ["meta", "evidence", "findings", "recommendations", "roadmap",
                    "resource_implications", "decisions"], "report %s" % path)
    _require(data["meta"], ["report_id"], "report meta in %s" % path)
    _require(data["roadmap"], ["phases", "items"], "report roadmap in %s" % path)
    return data


def load_deck(path):
    data = load_json(path)
    _require(data, ["meta", "slides"], "deck %s" % path)
    _require(data["meta"], ["deck_id", "report_ref", "session_minutes"], "deck meta in %s" % path)
    if not isinstance(data["slides"], list) or not data["slides"]:
        raise DeckDataError("deck %s has no slides" % path)
    for i, slide in enumerate(data["slides"]):
        if not isinstance(slide, dict):
            raise DeckDataError("deck %s slide %d is not an object" % (path, i))
        _require(slide, ["id", "section", "track", "title"], "deck %s slide %d" % (path, i))
    return data


# ---------------------------------------------------------------- report index

class ReportIndex(object):
    """Lookup surface over the report. Everything the checker asks goes here."""

    def __init__(self, report):
        self.report = report
        self.report_id = report["meta"]["report_id"]
        self.findings = OrderedDict((f["id"], f) for f in report.get("findings", []))
        self.recommendations = OrderedDict((r["id"], r) for r in report.get("recommendations", []))
        self.evidence = OrderedDict((e["id"], e) for e in report.get("evidence", []))
        self.resources = OrderedDict((r["id"], r) for r in report.get("resource_implications", []))
        self.decisions = OrderedDict((d["id"], d) for d in report.get("decisions", []))
        self.phases = OrderedDict((p["id"], p) for p in report["roadmap"].get("phases", []))
        self.rec_phase = OrderedDict()
        for item in report["roadmap"].get("items", []):
            self.rec_phase[item["rec"]] = item["phase"]

    def kind_of(self, ref):
        for name, table in (("finding", self.findings), ("recommendation", self.recommendations),
                            ("evidence", self.evidence), ("resource", self.resources),
                            ("decision", self.decisions)):
            if ref in table:
                return name
        return None

    def obj(self, ref):
        for table in (self.findings, self.recommendations, self.evidence, self.resources, self.decisions):
            if ref in table:
                return table[ref]
        return None

    def measure(self, ref, name):
        """Uniform measure lookup: any report object may carry a `measures` dict."""
        obj = self.obj(ref)
        if obj is None:
            return None
        return obj.get("measures", {}).get(name)

    def high_priority_gaps(self):
        return [f for f in self.findings.values()
                if f.get("kind") == "gap" and str(f.get("priority", "")).lower() == "high"]

    def open_inputs(self):
        """Every measure the report leaves UNKNOWN, plus any declared open inputs."""
        rows = []
        for table in (self.findings, self.resources):
            for ref, obj in table.items():
                for name in sorted(obj.get("measures", {})):
                    m = obj["measures"][name]
                    if is_unknown(m.get("value")):
                        rows.append((ref, name, m.get("basis", "not assessed")))
        rows.sort()
        return rows


def is_unknown(value):
    return isinstance(value, str) and value.strip().upper() == UNKNOWN


# ---------------------------------------------------------------- checking

def _core_slides(deck):
    return [s for s in deck["slides"] if s.get("track") == "core"]


def _appendix_slides(deck):
    return [s for s in deck["slides"] if s.get("track") == "appendix"]




def roadmap_dependency_checks(report):
    """Is the report's own roadmap possible?

    Added after a demonstrated hole: the deck checker verified a deck against a
    report whose roadmap put R-004 ("extend the practice to the remaining
    groups") BEFORE the recommendations that establish the practice, and
    reported PASS with zero findings. Deck-to-report agreement says nothing
    about whether the report's plan can happen, and a deck that faithfully
    presents an impossible plan is still an impossible plan in front of
    leadership.

    The dependency was in the deck all along -- as prose on appendix slide S-A4.
    A claim in a bullet is decoration; the same claim in a field is a check.
    """
    issues = []
    roadmap = report.get("roadmap", {})
    phases = [p["id"] for p in roadmap.get("phases", [])]
    pidx = dict((p, n) for n, p in enumerate(phases))
    items = roadmap.get("items", [])
    rec_phase = dict((i["rec"], i.get("phase")) for i in items)
    declared = dict((i["rec"], i.get("depends_on")) for i in items)

    # Absence of declared dependencies is NOT ASSESSED, never a pass. A roadmap
    # nobody expressed prerequisites for has not been shown to be coherent.
    if not any(d is not None for d in declared.values()):
        issues.append(Issue("R017_ROADMAP_DEPENDENCY_UNDECLARED", WARN, "-",
                            "no roadmap item declares depends_on, so roadmap dependency coherence "
                            "is NOT ASSESSED; that is not the same as coherent"))
        return issues

    edges = OrderedDict((rec, list(declared.get(rec) or [])) for rec in rec_phase)
    for rec, deps in edges.items():
        for dep in deps:
            if dep not in rec_phase:
                issues.append(Issue("R020_ROADMAP_DANGLING_DEPENDENCY", ERROR, rec,
                                    "%s declares a prerequisite %r that is not on the roadmap"
                                    % (rec, dep)))

    # Cycle detection, so an impossible loop is named rather than scheduled.
    WHITE, GREY, BLACK = 0, 1, 2
    colour = dict((r, WHITE) for r in edges)
    stack = []

    def visit(node):
        colour[node] = GREY
        stack.append(node)
        for nxt in sorted(d for d in edges.get(node, []) if d in edges):
            if colour[nxt] == GREY:
                return stack[stack.index(nxt):] + [nxt]
            if colour[nxt] == WHITE:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        colour[node] = BLACK
        return None

    cycle = None
    for node in sorted(edges):
        if colour[node] == WHITE:
            cycle = visit(node)
            if cycle:
                break
    if cycle:
        issues.append(Issue("R019_ROADMAP_DEPENDENCY_CYCLE", ERROR, " -> ".join(cycle),
                            "roadmap prerequisite cycle: %s" % " -> ".join(cycle)))
        return issues

    for rec, deps in edges.items():
        here = pidx.get(rec_phase.get(rec))
        if here is None:
            continue
        for dep in deps:
            there = pidx.get(rec_phase.get(dep))
            if there is None:
                continue
            if there > here:
                issues.append(Issue("R018_ROADMAP_PREREQ_AFTER_DEPENDENT", ERROR, rec,
                                    "%s is scheduled in %s but its prerequisite %s is scheduled in "
                                    "%s, which is later; the plan cannot be executed in that order"
                                    % (rec, rec_phase[rec], dep, rec_phase[dep])))
    return issues

def check(report, deck):
    """Return the full issue list. Empty error list means the deck agrees."""
    idx = ReportIndex(report)
    issues = []
    slides = deck["slides"]
    by_id = OrderedDict((s["id"], s) for s in slides)

    if len(by_id) != len(slides):
        seen, dupes = set(), set()
        for s in slides:
            if s["id"] in seen:
                dupes.add(s["id"])
            seen.add(s["id"])
        issues.append(Issue("R001_SECTION_ORDER", ERROR, "-",
                            "duplicate slide id(s): %s" % ", ".join(sorted(dupes))))

    # R015 -- checking a deck against the wrong report invalidates every other rule.
    if deck["meta"].get("report_ref") != idx.report_id:
        issues.append(Issue("R015_REPORT_MISMATCH", ERROR, "-",
                            "deck report_ref %r is not report_id %r"
                            % (deck["meta"].get("report_ref"), idx.report_id)))

    # R001 -- core sections present, once each, in canonical order.
    core = _core_slides(deck)
    seen_sections = [s.get("section") for s in core]
    for section in CORE_SECTIONS:
        n = seen_sections.count(section)
        if n == 0:
            issues.append(Issue("R001_SECTION_ORDER", ERROR, "-", "core section %r is missing" % section))
        elif n > 1:
            issues.append(Issue("R001_SECTION_ORDER", ERROR, "-",
                                "core section %r appears %d times" % (section, n)))
    ordered = [s for s in seen_sections if s in CORE_SECTIONS]
    expected = [s for s in CORE_SECTIONS if s in ordered]
    if ordered != expected:
        issues.append(Issue("R001_SECTION_ORDER", ERROR, "-",
                            "core sections out of order: got %s, expected %s"
                            % (" > ".join(ordered), " > ".join(expected))))
    for s in core:
        if s.get("section") not in CORE_SECTIONS:
            issues.append(Issue("R001_SECTION_ORDER", ERROR, s["id"],
                                "unknown core section %r" % s.get("section")))

    # Per-slide rules.
    cited_ids = set()
    for slide in slides:
        sid = slide["id"]
        is_core = slide.get("track") == "core"
        claims = slide.get("claims", []) or []

        if is_core:
            if not (slide.get("speaker_notes") or []):
                issues.append(Issue("R011_MISSING_SPEAKER_NOTES", ERROR, sid,
                                    "core slide has no speaker-note prompt"))
            bullets = slide.get("bullets", []) or []
            if len(bullets) > MAX_CORE_BULLETS:
                issues.append(Issue("R012_DETAIL_IN_MAIN_BODY", ERROR, sid,
                                    "%d bullets exceeds the executive budget of %d; move detail to an appendix slide"
                                    % (len(bullets), MAX_CORE_BULLETS)))
            for b in bullets:
                if len(b) > MAX_BULLET_CHARS:
                    issues.append(Issue("R012_DETAIL_IN_MAIN_BODY", ERROR, sid,
                                        "a bullet is %d characters (budget %d); move detail to an appendix slide"
                                        % (len(b), MAX_BULLET_CHARS)))

        for ci, claim in enumerate(claims):
            tag = "%s claim %d" % (sid, ci)
            ref = claim.get("cites")
            if not ref:
                issues.append(Issue("R002_DANGLING_CITATION", ERROR, sid, "%s cites nothing" % tag))
                continue
            cited_ids.add(ref)
            kind = idx.kind_of(ref)
            if kind is None:
                issues.append(Issue("R002_DANGLING_CITATION", ERROR, sid,
                                    "%s cites %s, which is not in the report" % (tag, ref)))
                continue

            ctype = claim.get("type")

            # R006 -- "validated strength" is a claim about the report, not a tone.
            if ctype == "strength":
                obj = idx.obj(ref)
                if kind != "finding":
                    issues.append(Issue("R006_UNVALIDATED_STRENGTH", ERROR, sid,
                                        "%s presents %s as a strength but it is a %s" % (tag, ref, kind)))
                elif obj.get("kind") != "strength" or obj.get("validated") is not True:
                    issues.append(Issue("R006_UNVALIDATED_STRENGTH", ERROR, sid,
                                        "%s presents %s as a validated strength; report has kind=%r validated=%r"
                                        % (tag, ref, obj.get("kind"), obj.get("validated"))))

            # R007 -- phase assignments must match the report roadmap.
            if ctype == "phase":
                deck_phase = claim.get("phase")
                report_phase = idx.rec_phase.get(ref)
                if report_phase is None:
                    issues.append(Issue("R007_PHASE_DISAGREEMENT", ERROR, sid,
                                        "%s places %s in a phase, but the report roadmap has no item for it" % (tag, ref)))
                elif deck_phase != report_phase:
                    issues.append(Issue("R007_PHASE_DISAGREEMENT", ERROR, sid,
                                        "%s places %s in %r; report roadmap says %r"
                                        % (tag, ref, deck_phase, report_phase)))

            # R014 -- a decision must land on a real recommendation in an agreeing phase.
            if ctype == "decision":
                if kind != "decision":
                    issues.append(Issue("R014_DECISION_UNLINKED", ERROR, sid,
                                        "%s is a decision claim but %s is a %s" % (tag, ref, kind)))
                else:
                    dec = idx.obj(ref)
                    rec = dec.get("recommendation")
                    if rec not in idx.recommendations:
                        issues.append(Issue("R014_DECISION_UNLINKED", ERROR, sid,
                                            "%s: decision %s points at recommendation %r, which is not in the report"
                                            % (tag, ref, rec)))
                    elif dec.get("phase") != idx.rec_phase.get(rec):
                        issues.append(Issue("R014_DECISION_UNLINKED", ERROR, sid,
                                            "%s: decision %s says phase %r but %s sits in %r"
                                            % (tag, ref, dec.get("phase"), rec, idx.rec_phase.get(rec))))

            # R003 / R004 / R013 -- the figures.
            if "measure" in claim:
                mname = claim["measure"]
                m = idx.measure(ref, mname)
                if m is None:
                    issues.append(Issue("R013_UNRESOLVED_MEASURE", ERROR, sid,
                                        "%s cites measure %r on %s, which the report does not carry" % (tag, mname, ref)))
                else:
                    rv, dv = m.get("value"), claim.get("value")
                    if is_unknown(rv) and not is_unknown(dv):
                        issues.append(Issue("R004_UNKNOWN_FABRICATION", ERROR, sid,
                                            "%s states %r for %s.%s, which the report leaves UNKNOWN (%s)"
                                            % (tag, dv, ref, mname, m.get("basis", "not assessed"))))
                    elif not is_unknown(rv) and is_unknown(dv):
                        issues.append(Issue("R003_FIGURE_DISAGREEMENT", ERROR, sid,
                                            "%s shows UNKNOWN for %s.%s, but the report has %r"
                                            % (tag, ref, mname, rv)))
                    elif rv != dv:
                        issues.append(Issue("R003_FIGURE_DISAGREEMENT", ERROR, sid,
                                            "%s states %r for %s.%s; report says %r"
                                            % (tag, dv, ref, mname, rv)))
                    elif claim.get("unit") is not None and m.get("unit") is not None \
                            and claim.get("unit") != m.get("unit"):
                        issues.append(Issue("R003_FIGURE_DISAGREEMENT", ERROR, sid,
                                            "%s states unit %r for %s.%s; report says %r"
                                            % (tag, claim.get("unit"), ref, mname, m.get("unit"))))

                # R008 -- a figure in the main body must be traceable from the appendix.
                if is_core:
                    support = slide.get("appendix_support", []) or []
                    backed = False
                    for aid in support:
                        asl = by_id.get(aid)
                        if asl is None:
                            issues.append(Issue("R008_MAIN_CLAIM_WITHOUT_APPENDIX", ERROR, sid,
                                                "%s names appendix slide %s, which does not exist" % (tag, aid)))
                            continue
                        for ac in asl.get("claims", []) or []:
                            if ac.get("cites") == ref:
                                backed = True
                    if not backed:
                        issues.append(Issue("R008_MAIN_CLAIM_WITHOUT_APPENDIX", ERROR, sid,
                                            "%s states a figure for %s with no appendix slide carrying that id"
                                            % (tag, ref)))

    # R005 -- a high-priority gap that never reaches a core slide has been dropped.
    core_cited = set()
    for slide in _core_slides(deck):
        for claim in slide.get("claims", []) or []:
            if claim.get("cites"):
                core_cited.add(claim["cites"])
    for f in idx.high_priority_gaps():
        if f["id"] not in core_cited:
            issues.append(Issue("R005_OMITTED_PRIORITY_FINDING", ERROR, "-",
                                "high-priority gap %s (%s) is not on any core slide" % (f["id"], f.get("statement", ""))))

    # R017-R020 -- is the report's own roadmap possible? A deck that agrees with
    # an impossible plan is still presenting an impossible plan.
    issues.extend(roadmap_dependency_checks(report))

    # R009 -- appendix slides nobody can reach.
    reachable = set()
    for slide in _core_slides(deck):
        for aid in slide.get("appendix_support", []) or []:
            reachable.add(aid)
    for slide in _appendix_slides(deck):
        if slide["id"] not in reachable:
            issues.append(Issue("R009_ORPHAN_APPENDIX", WARN, slide["id"],
                                "appendix slide is not referenced by any core slide"))

    # R010 / R016 -- the agenda has to fit the room.
    session = deck["meta"].get("session_minutes")
    total = sum(int(s.get("minutes", 0) or 0) for s in _core_slides(deck))
    if isinstance(session, (int, float)) and session > 0:
        if total > session:
            issues.append(Issue("R010_AGENDA_OVERRUN", ERROR, "-",
                                "core slides total %d minutes against a declared session of %d" % (total, session)))
        elif total < 0.75 * session:
            issues.append(Issue("R016_AGENDA_UNDERRUN", WARN, "-",
                                "core slides total %d minutes of a %d minute session" % (total, session)))
    else:
        issues.append(Issue("R010_AGENDA_OVERRUN", ERROR, "-",
                            "session_minutes is missing or not a positive number"))

    issues.sort(key=lambda i: (0 if i.severity == ERROR else 1, i.slide, i.code, i.detail))
    return issues


def errors(issues):
    return [i for i in issues if i.severity == ERROR]


# ---------------------------------------------------------------- claim rows

def claim_rows(report, deck):
    """The planning table: one row per claim, with deck value beside report value."""
    idx = ReportIndex(report)
    by_id = OrderedDict((s["id"], s) for s in deck["slides"])
    rows = []
    for slide in deck["slides"]:
        claims = slide.get("claims", []) or []
        if not claims:
            rows.append(OrderedDict([
                ("slide_id", slide["id"]), ("section", slide.get("section", "")),
                ("track", slide.get("track", "")), ("minutes", slide.get("minutes", 0)),
                ("title", slide.get("title", "")), ("claim_index", ""), ("claim_type", ""),
                ("cites", ""), ("cited_kind", ""), ("measure", ""), ("deck_value", ""),
                ("report_value", ""), ("unit", ""), ("agreement", "NO-CLAIMS"),
                ("appendix_support", ";".join(slide.get("appendix_support", []) or [])),
                ("evidence", ""),
            ]))
            continue
        for ci, claim in enumerate(claims):
            ref = claim.get("cites", "")
            kind = idx.kind_of(ref) or ""
            obj = idx.obj(ref) or {}
            mname = claim.get("measure", "")
            report_value, unit, agreement = "", claim.get("unit", "") or "", ""
            if not kind:
                agreement = "UNRESOLVED-CITATION"
            elif mname:
                m = idx.measure(ref, mname)
                if m is None:
                    agreement = "UNRESOLVED-MEASURE"
                else:
                    report_value = m.get("value")
                    unit = m.get("unit", "") or unit
                    dv = claim.get("value")
                    if is_unknown(report_value) and is_unknown(dv):
                        agreement = "UNKNOWN-IN-REPORT"
                    elif is_unknown(report_value) or is_unknown(dv) or report_value != dv:
                        agreement = "DISAGREE"
                    elif claim.get("unit") is not None and m.get("unit") is not None \
                            and claim.get("unit") != m.get("unit"):
                        agreement = "DISAGREE-UNIT"
                    else:
                        agreement = "MATCH"
            elif claim.get("type") == "phase":
                report_value = idx.rec_phase.get(ref, "")
                agreement = "MATCH" if report_value == claim.get("phase") else "DISAGREE"
            else:
                agreement = "LINK-ONLY"
            rows.append(OrderedDict([
                ("slide_id", slide["id"]), ("section", slide.get("section", "")),
                ("track", slide.get("track", "")), ("minutes", slide.get("minutes", 0)),
                ("title", slide.get("title", "")), ("claim_index", ci),
                ("claim_type", claim.get("type", "")), ("cites", ref), ("cited_kind", kind),
                ("measure", mname),
                ("deck_value", claim.get("value", claim.get("phase", ""))),
                ("report_value", report_value), ("unit", unit), ("agreement", agreement),
                ("appendix_support", ";".join(slide.get("appendix_support", []) or [])),
                ("evidence", ";".join(obj.get("evidence", []) or [])),
            ]))
    _ = by_id
    return rows


# ---------------------------------------------------------------- rendering

BOX_W = 78
MARK = {
    "MATCH": "[ok]",
    "UNKNOWN-IN-REPORT": "[??]",
    "DISAGREE": "[XX]",
    "DISAGREE-UNIT": "[XX]",
    "UNRESOLVED-CITATION": "[XX]",
    "UNRESOLVED-MEASURE": "[XX]",
    "LINK-ONLY": "[->]",
    "NO-CLAIMS": "[--]",
}


def _ascii(text):
    return str(text).encode("ascii", "replace").decode("ascii")


def _line(ch="-"):
    return "+" + ch * (BOX_W - 2) + "+"


def _row(text=""):
    t = _ascii(text)
    return "| " + t[:BOX_W - 4].ljust(BOX_W - 4) + " |"


def _wrapped(text, indent="", hang=None):
    """Wrap into box rows with a hanging indent, so a wrapped bullet still
    reads as one bullet on paper."""
    hang = indent if hang is None else hang
    lines = textwrap.wrap(_ascii(text), BOX_W - 4,
                          initial_indent=indent, subsequent_indent=hang) or [indent]
    return [_row(ln) for ln in lines]


def render_ascii(report, deck, rows=None):
    """Slide frames drawn in plain ASCII. No color, no glyphs: the marks
    [ok] [??] [XX] [->] carry the state, so this reads on paper, in a terminal,
    and for anyone who cannot distinguish a red cell from a green one."""
    rows = rows if rows is not None else claim_rows(report, deck)
    by_slide = {}
    for r in rows:
        by_slide.setdefault(r["slide_id"], []).append(r)
    idx = ReportIndex(report)
    out = []
    meta = deck["meta"]
    out.append(_line("="))
    out.append(_row(_ascii(meta.get("title", "readout deck"))))
    out.append(_row("deck %s  ->  report %s" % (meta.get("deck_id"), meta.get("report_ref"))))
    out.append(_row("session: %s minutes   audience: %s" % (meta.get("session_minutes"), meta.get("audience", "-"))))
    out.append(_line("="))
    out.append(_row("LEGEND  [ok] deck figure equals report   [??] UNKNOWN in report, shown as UNKNOWN"))
    out.append(_row("        [XX] disagrees with report       [->] link only, no figure"))
    out.append(_row("        This view uses marks, not color."))
    out.append(_line("="))
    if meta.get("fiction_notice"):
        for ln in _wrapped(meta["fiction_notice"], "  ", "  "):
            out.append(ln)
        out.append(_line("-"))
    out.append("")

    for slide in deck["slides"]:
        sid = slide["id"]
        section = SECTION_TITLES.get(slide.get("section"), str(slide.get("section", "")).upper())
        head = "%s  %s" % (sid, section)
        tail = "[%s] %s min" % (slide.get("track", ""), slide.get("minutes", 0))
        pad = BOX_W - 4 - len(head) - len(tail)
        out.append(_line("="))
        out.append(_row(head + " " * max(1, pad) + tail))
        out.extend(_wrapped(slide.get("title", ""), "", "  "))
        out.append(_line("-"))
        for b in slide.get("bullets", []) or []:
            out.extend(_wrapped(b, "  - ", "    "))
        srows = [r for r in by_slide.get(sid, []) if r["agreement"] != "NO-CLAIMS"]
        if srows:
            out.append(_row(""))
            out.append(_row("  CLAIMS AGAINST THE REPORT"))
            for r in srows:
                mark = MARK.get(r["agreement"], "[XX]")
                if r["measure"]:
                    dv = "UNKNOWN (not assessed)" if is_unknown(r["deck_value"]) else r["deck_value"]
                    rv = "UNKNOWN (not assessed)" if is_unknown(r["report_value"]) else r["report_value"]
                    body = "%s %s.%s  deck=%s  report=%s  %s" % (
                        mark, r["cites"], r["measure"], dv, rv, r["unit"])
                elif r["claim_type"] == "phase":
                    body = "%s %s phase deck=%s report=%s" % (mark, r["cites"], r["deck_value"], r["report_value"])
                else:
                    body = "%s %s (%s)" % (mark, r["cites"], r["cited_kind"] or "unresolved")
                out.extend(_wrapped(body, "   ", "        "))
        if slide.get("appendix_support"):
            out.extend(_wrapped("APPENDIX: " + ", ".join(slide["appendix_support"]), "  ", "    "))
        notes = slide.get("speaker_notes", []) or []
        if notes:
            out.append(_row(""))
            out.append(_row("  SPEAKER NOTES"))
            for n in notes:
                out.extend(_wrapped(n, "   > ", "     "))
        out.append(_line("="))
        out.append("")

    out.append(_line("="))
    out.append(_row("TRACK MAP"))
    out.append(_line("="))
    core = _core_slides(deck)
    total = sum(int(s.get("minutes", 0) or 0) for s in core)
    out.append(_row("EXECUTIVE PATH - core slides only, %d of %d minutes"
                    % (total, deck["meta"].get("session_minutes"))))
    for s in core:
        sup = ", ".join(s.get("appendix_support", []) or []) or "-"
        left = "  %s %s" % (s["id"], _ascii(s.get("title", ""))[:34].ljust(34))
        out.append(_row("%s %3s min  drill-down: %s" % (left, s.get("minutes", 0), sup)))
    out.append(_row(""))
    out.append(_row("PRACTITIONER DRILL-DOWN - appendix slides, reached from"))
    for s in _appendix_slides(deck):
        froms = sorted(c["id"] for c in core if s["id"] in (c.get("appendix_support", []) or []))
        out.append(_row("  %s %s <- %s" % (s["id"], _ascii(s.get("title", ""))[:40].ljust(40),
                                           ", ".join(froms) or "NOTHING (orphan)")))
    out.append(_line("="))
    out.append("")

    open_inputs = idx.open_inputs()
    out.append(_line("="))
    out.append(_row("OPEN INPUTS - stay UNKNOWN until supplied, never estimated"))
    out.append(_line("="))
    if not open_inputs:
        out.append(_row("  (none)"))
    for ref, name, basis in open_inputs:
        out.extend(_wrapped("%s.%s : %s" % (ref, name, basis), "  - ", "    "))
    for note in report.get("open_inputs", []) or []:
        out.extend(_wrapped(note, "  - ", "    "))
    out.append(_line("="))
    return "\n".join(out) + "\n"


def render_markdown(report, deck, issues, rows=None):
    rows = rows if rows is not None else claim_rows(report, deck)
    by_slide = {}
    for r in rows:
        by_slide.setdefault(r["slide_id"], []).append(r)
    err = errors(issues)
    meta = deck["meta"]
    out = []
    out.append("# %s" % meta.get("title", "Readout deck"))
    out.append("")
    status = "FAILED - %d disagreement(s) with the report" % len(err) if err else "PASSED"
    out.append("**Deck-to-report agreement: %s** (deck `%s` checked against report `%s`)"
               % (status, meta.get("deck_id"), meta.get("report_ref")))
    if err:
        out.append("")
        out.append("> This deck does not agree with its report. Do not present it until the "
                   "disagreements below are resolved; see the agreement report.")
    out.append("")
    if meta.get("fiction_notice"):
        out.append("> %s" % meta["fiction_notice"])
        out.append("")
    out.append("Session: %s minutes. Audience: %s." % (meta.get("session_minutes"), meta.get("audience", "-")))
    out.append("")
    out.append("## Executive path")
    out.append("")
    out.append("| Slide | Section | Min | Title | Drill-down |")
    out.append("|---|---|---|---|---|")
    for s in _core_slides(deck):
        out.append("| %s | %s | %s | %s | %s |" % (
            s["id"], s.get("section", ""), s.get("minutes", 0), s.get("title", ""),
            ", ".join(s.get("appendix_support", []) or []) or "-"))
    out.append("")
    for slide in deck["slides"]:
        out.append("## %s - %s" % (slide["id"], slide.get("title", "")))
        out.append("")
        out.append("*%s | %s | %s min*" % (SECTION_TITLES.get(slide.get("section"), slide.get("section", "")),
                                           slide.get("track", ""), slide.get("minutes", 0)))
        out.append("")
        for b in slide.get("bullets", []) or []:
            out.append("- %s" % b)
        out.append("")
        srows = [r for r in by_slide.get(slide["id"], []) if r["agreement"] != "NO-CLAIMS"]
        if srows:
            out.append("**Claims against the report**")
            out.append("")
            out.append("| Mark | Cites | Measure | Deck says | Report says | Agreement |")
            out.append("|---|---|---|---|---|---|")
            for r in srows:
                dv = "UNKNOWN (not assessed)" if is_unknown(r["deck_value"]) else r["deck_value"]
                rv = "UNKNOWN (not assessed)" if is_unknown(r["report_value"]) else r["report_value"]
                out.append("| %s | %s | %s | %s | %s | %s |" % (
                    MARK.get(r["agreement"], "[XX]"), r["cites"], r["measure"] or "-",
                    dv if dv != "" else "-", rv if rv != "" else "-", r["agreement"]))
            out.append("")
        if slide.get("speaker_notes"):
            out.append("**Speaker notes**")
            out.append("")
            for n in slide["speaker_notes"]:
                out.append("> %s" % n)
            out.append("")
    idx = ReportIndex(report)
    out.append("## Open inputs")
    out.append("")
    out.append("These stay UNKNOWN. None of them is presented as a zero, a pass, or a maturity level.")
    out.append("")
    for ref, name, basis in idx.open_inputs():
        out.append("- `%s.%s` - %s" % (ref, name, basis))
    for note in report.get("open_inputs", []) or []:
        out.append("- %s" % note)
    out.append("")
    return "\n".join(out) + "\n"


def render_agreement_report(report, deck, issues):
    err = errors(issues)
    warn = [i for i in issues if i.severity == WARN]
    out = []
    out.append("# Deck-to-report agreement report")
    out.append("")
    out.append("Deck `%s` checked against report `%s`." % (deck["meta"].get("deck_id"), report["meta"].get("report_id")))
    out.append("")
    out.append("**Result: %s** - %d error(s), %d warning(s)."
               % ("FAIL" if err else "PASS", len(err), len(warn)))
    out.append("")
    if issues:
        out.append("| Severity | Rule | Slide | Detail |")
        out.append("|---|---|---|---|")
        for i in issues:
            out.append("| %s | %s | %s | %s |" % (i.severity, i.code, i.slide, i.detail.replace("|", "\\|")))
        out.append("")
    else:
        out.append("No disagreements. Every figure on a slide equals the report's value, every "
                   "high-priority gap reaches a core slide, and every main-body figure is backed "
                   "by an appendix slide carrying the same id.")
        out.append("")
    out.append("## Rules applied")
    out.append("")
    out.append("| Rule | What it enforces |")
    out.append("|---|---|")
    for code, desc in RULES.items():
        out.append("| %s | %s |" % (code, desc))
    out.append("")
    return "\n".join(out) + "\n"




# ---------------------------------------------------------------- provenance

# Why this exists: the Markdown and ASCII outputs of this lane carried their
# provenance notice; the CSVs did not. A CSV is the most portable artifact here
# and the one most likely to be lifted out of the bundle and opened alone --
# which is exactly how a fictional number ends up quoted as a real finding.
#
# The requirement is a PROVENANCE statement, not a fiction label. A real
# measurement must not be stamped synthetic, and an artifact whose source says
# nothing must not be stamped either way: it is reported as undeclared.

PROVENANCE_PREFIX = "# PROVENANCE: "
UNDECLARED_PROVENANCE = ("PROVENANCE NOT DECLARED IN SOURCE. Do not treat these rows as "
                         "real or as synthetic until the source declares which.")


def provenance_statement(*metas):
    """An explicit provenance wins; a fiction notice implies synthetic; silence
    is reported as undeclared rather than assumed in either direction."""
    for meta in metas:
        if isinstance(meta, dict) and str(meta.get("provenance", "")).strip():
            return " ".join(str(meta["provenance"]).split())
    for meta in metas:
        if isinstance(meta, dict) and str(meta.get("fiction_notice", "")).strip():
            return "SYNTHETIC. " + " ".join(str(meta["fiction_notice"]).split())
    return UNDECLARED_PROVENANCE


def write_provenance(fh, statement):
    """One banner line, then the header row. A '#' first line is the convention
    the rest of the kit uses, and read_csv_rows() below strips it, so the banner
    cannot break machine parsing."""
    fh.write(PROVENANCE_PREFIX + statement.replace("\r", " ").replace("\n", " ") + "\n")


def read_csv_rows(path):
    """The documented reader contract for these CSVs.

    Returns (provenance_statement_or_None, list_of_dict_rows). Leading '#' lines
    are metadata, not data; everything after them parses as ordinary CSV.
    """
    with open(path, "r", newline="", encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    statement, start = None, 0
    for i, line in enumerate(lines):
        if line.startswith("#"):
            if statement is None and line.startswith(PROVENANCE_PREFIX):
                statement = line[len(PROVENANCE_PREFIX):].strip()
            start = i + 1
        else:
            break
    body = "\n".join(lines[start:])
    return statement, list(csv.DictReader(body.splitlines()))



def write_csv(path, rows, statement=None):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        write_provenance(fh, statement or UNDECLARED_PROVENANCE)
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)



# ---------------------------------------------------------------- fill

# Why this exists: the static template in templates/ is a single worked shape,
# and a shape silently assumes a count. Filled mechanically against a report
# carrying TWO high-priority gaps it failed R005 -- the priority-findings slide
# had one gap slot and one appendix drill-down. "The deliverable is present" is
# not the same as "the deliverable can be used", and a template an editor
# cannot fill into a passing deck is a defect in the deliverable.
#
# fill_template() sizes the deck to the report instead: one priority-findings
# claim per high-priority gap, one appendix slide per figure claim, phases read
# off the roadmap, and an agenda that sums to the declared session exactly. The
# editor writes prose; the structure is already correct.

MIN_SESSION_MINUTES = len(CORE_SECTIONS)
_SECTION_WEIGHTS = OrderedDict([
    ("purpose", 3), ("evidence", 4), ("strengths", 6), ("priority_findings", 10),
    ("roadmap", 8), ("resources", 6), ("decisions", 8),
])


def _allocate_minutes(session_minutes):
    """Distribute the session across the core sections so the total is exact.

    R010 fails a deck whose agenda overruns, so an allocator that leaves a
    rounding remainder would generate decks that fail their own checker.
    """
    if not isinstance(session_minutes, int) or session_minutes < MIN_SESSION_MINUTES:
        raise DeckDataError(
            "session_minutes must be an integer of at least %d, one per core section, not %r"
            % (MIN_SESSION_MINUTES, session_minutes))
    total_weight = sum(_SECTION_WEIGHTS.values())
    out = OrderedDict()
    for section, weight in _SECTION_WEIGHTS.items():
        out[section] = max(1, int(session_minutes * weight // total_weight))
    # Settle the remainder on the largest section, which is where a minute
    # matters least, and never below one minute anywhere.
    drift = session_minutes - sum(out.values())
    order = sorted(out, key=lambda k: (-_SECTION_WEIGHTS[k], k))
    i = 0
    while drift != 0:
        section = order[i % len(order)]
        if drift > 0:
            out[section] += 1
            drift -= 1
        elif out[section] > 1:
            out[section] -= 1
            drift += 1
        i += 1
        if i > 10000:  # unreachable for any session >= MIN_SESSION_MINUTES
            raise DeckDataError("could not fit %d minutes across %d sections"
                                % (session_minutes, len(out)))
    return out


def _first_measure(idx, ref):
    obj = idx.obj(ref) or {}
    names = sorted(obj.get("measures", {}))
    return names[0] if names else None


def _figure_claim(idx, ctype, ref):
    """A claim carrying the report's own value, so the generated deck agrees by
    construction rather than by the editor retyping a number."""
    name = _first_measure(idx, ref)
    claim = {"type": ctype, "cites": ref, "text": "REPLACE - say this in one sentence"}
    if name is not None:
        m = idx.measure(ref, name)
        claim.update({"measure": name, "value": m.get("value"), "unit": m.get("unit")})
    return claim


def fill_template(report, session_minutes=45):
    """Build a structurally valid deck skeleton sized to this report."""
    idx = ReportIndex(report)
    minutes = _allocate_minutes(int(session_minutes))
    slides, appendix = [], []
    counter = [0]

    def appendix_for(ref, title):
        counter[0] += 1
        aid = "S-A%02d" % counter[0]
        appendix.append({
            "id": aid, "section": "appendix", "track": "appendix", "minutes": 0,
            "title": "Appendix - %s" % title,
            "bullets": ["REPLACE - the exact records behind %s" % ref,
                        "REPLACE - the sampling basis or limitation"],
            "claims": [_figure_claim(idx, "evidence" if ref.startswith("EV-") else "gap", ref)],
            "appendix_support": [],
            "speaker_notes": ["REPLACE - read the locator, not the conclusion"],
        })
        return aid

    def core(section, title, bullets, claims, support, notes):
        slides.append({
            "id": "S-%02d" % (CORE_SECTIONS.index(section) + 1), "section": section,
            "track": "core", "minutes": minutes[section], "title": title,
            "bullets": bullets, "claims": claims, "appendix_support": support,
            "speaker_notes": notes,
        })

    core("purpose", "REPLACE - why we are in this room",
         ["REPLACE - scope in one line",
          "REPLACE - what this session decides",
          "REPLACE - anything unevidenced is shown as UNKNOWN, not estimated"],
         [], [], ["REPLACE - name the decisions on the last slide up front"])

    ev = [e["id"] for e in report.get("evidence", [])][:3]
    ev_support = [appendix_for(e, "evidence register") for e in ev[:1]]
    core("evidence", "REPLACE - what this rests on",
         ["REPLACE - sources and counts", "REPLACE - sampling basis",
          "REPLACE - a stated limitation"],
         [{"type": "evidence", "cites": e, "text": "REPLACE"} for e in ev],
         ev_support, ["REPLACE - where to go when a number is challenged"])

    strengths = [f for f in idx.findings.values()
                 if f.get("kind") == "strength" and f.get("validated") is True]
    s_claims, s_support = [], []
    for f in strengths:
        s_claims.append(_figure_claim(idx, "strength", f["id"]))
        if "measure" in s_claims[-1]:
            s_support.append(appendix_for(f["id"], "strength detail"))
    core("strengths", "REPLACE - what is already working",
         ["REPLACE - the practice worth naming",
          "REPLACE - why it is the internal model",
          "REPLACE - any candidate strength held back for lack of corroboration"],
         s_claims, s_support, ["REPLACE - why an internal model is cheaper than an imported one"])

    # One claim and one drill-down PER high-priority gap. This is the defect the
    # static template carried: it assumed exactly one.
    gaps = idx.high_priority_gaps()
    g_claims, g_support = [], []
    for f in gaps:
        g_claims.append(_figure_claim(idx, "gap", f["id"]))
        if "measure" in g_claims[-1]:
            g_support.append(appendix_for(f["id"], "priority gap detail"))
    core("priority_findings", "REPLACE - the gaps worth leadership time",
         ["REPLACE - the first gap in one line", "REPLACE - the second, if there is one",
          "REPLACE - state that findings are about the process record, not individuals"],
         g_claims, g_support, ["REPLACE - which gap to lead with and why",
                               "REPLACE - a question to put back to the room"])

    phase_claims = [{"type": "phase", "cites": rec, "phase": phase,
                     "text": "REPLACE"} for rec, phase in idx.rec_phase.items()]
    r_support = [appendix_for(list(idx.rec_phase)[0], "phase dependencies")] if idx.rec_phase else []
    core("roadmap", "REPLACE - sequence",
         ["REPLACE - first window", "REPLACE - second window", "REPLACE - beyond"],
         phase_claims, r_support,
         ["REPLACE - describe each phase by the evidence it produces, not a maturity level"])

    res_claims, res_support = [], []
    for rid in idx.resources:
        claim = _figure_claim(idx, "resource", rid)
        res_claims.append(claim)
        if "measure" in claim:
            res_support.append(appendix_for(rid, "resource assumptions"))
    core("resources", "REPLACE - what it costs, and what cannot be costed yet",
         ["REPLACE - one-time", "REPLACE - recurring",
          "REPLACE - what stays UNKNOWN and why"],
         res_claims, res_support,
         ["REPLACE - name who can supply each missing input, and by when"])

    core("decisions", "REPLACE - what we need from you today",
         ["REPLACE - decision one", "REPLACE - decision two", "REPLACE - decision three"],
         [{"type": "decision", "cites": d, "text": "REPLACE - the options"}
          for d in idx.decisions],
         [], ["REPLACE - record the chosen option and its owner in the room",
              "REPLACE - a defer is a legitimate outcome; record what would change it"])

    return {
        "meta": {
            "deck_id": "REPLACE-DECK-ID",
            "report_ref": report["meta"]["report_id"],
            "title": "REPLACE - readout deck title",
            "audience": "REPLACE - who is in the room",
            "session_minutes": int(session_minutes),
            "fiction_notice": "REPLACE or delete. If any content is synthetic, say so here.",
            "generated_from": ("Structure generated by deck_architecture.py fill-template from "
                               "report %s. Every value shown is the report's own; prose marked "
                               "REPLACE is the editor's." % report["meta"]["report_id"]),
        },
        "slides": slides + appendix,
    }

# ---------------------------------------------------------------- cli

def cmd_check(args):
    report = load_report(args.report)
    deck = load_deck(args.deck)
    issues = check(report, deck)
    if args.json:
        sys.stdout.write(json.dumps([i.as_dict() for i in issues], indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(render_agreement_report(report, deck, issues))
    return 1 if errors(issues) else 0


def cmd_render(args):
    report = load_report(args.report)
    deck = load_deck(args.deck)
    issues = check(report, deck)
    rows = claim_rows(report, deck)
    outdir = args.outdir
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    written = []
    targets = [
        ("readout-deck.md", render_markdown(report, deck, issues, rows)),
        ("readout-deck-ascii.txt", render_ascii(report, deck, rows)),
        ("deck-report-agreement.md", render_agreement_report(report, deck, issues)),
    ]
    for name, text in targets:
        p = os.path.join(outdir, name)
        with open(p, "w") as fh:
            fh.write(text)
        written.append(p)
    p = os.path.join(outdir, "readout-planning-table.csv")
    write_csv(p, rows, provenance_statement(deck.get("meta", {}), report.get("meta", {})))
    written.append(p)
    for p in written:
        sys.stdout.write("wrote %s\n" % p)
    err = errors(issues)
    sys.stdout.write("agreement: %s (%d error(s), %d warning(s))\n"
                     % ("FAIL" if err else "PASS", len(err), len(issues) - len(err)))
    return 1 if err else 0


def cmd_fill_template(args):
    report = load_report(args.report)
    deck = fill_template(report, args.session_minutes)
    issues = check(report, deck)
    err = errors(issues)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(deck, fh, indent=2, ensure_ascii=False)
    sys.stdout.write("wrote %s: %d slide(s), %d core minute(s) of a %d minute session\n"
                     % (args.out, len(deck["slides"]),
                        sum(sl["minutes"] for sl in deck["slides"] if sl["track"] == "core"),
                        deck["meta"]["session_minutes"]))
    sys.stdout.write("structure check: %s (%d error(s), %d warning(s))\n"
                     % ("FAIL" if err else "PASS", len(err), len(issues) - len(err)))
    for i in err:
        sys.stdout.write("  %s %s %s\n" % (i.code, i.slide, i.detail))
    return 1 if err else 0


def cmd_rules(args):
    for code, desc in RULES.items():
        sys.stdout.write("%-32s %s\n" % (code, desc))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Readout deck architecture: check and render a deck against its report.")
    sub = ap.add_subparsers(dest="cmd")

    c = sub.add_parser("check", help="check the deck against the report; exit 1 on disagreement")
    c.add_argument("--report", required=True)
    c.add_argument("--deck", required=True)
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_check)

    r = sub.add_parser("render", help="render deck markdown, ASCII frames, agreement report and planning CSV")
    r.add_argument("--report", required=True)
    r.add_argument("--deck", required=True)
    r.add_argument("--outdir", default="examples")
    r.set_defaults(func=cmd_render)

    f = sub.add_parser("fill-template",
                       help="generate a deck skeleton sized to a report (one priority-findings "
                            "claim per high-priority gap, appendix backing for every figure)")
    f.add_argument("--report", required=True)
    f.add_argument("--out", required=True)
    f.add_argument("--session-minutes", type=int, default=45, dest="session_minutes")
    f.set_defaults(func=cmd_fill_template)

    u = sub.add_parser("rules", help="print the rule table")
    u.set_defaults(func=cmd_rules)

    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 2
    try:
        return args.func(args)
    except DeckDataError as exc:
        sys.stderr.write("INPUT ERROR: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
