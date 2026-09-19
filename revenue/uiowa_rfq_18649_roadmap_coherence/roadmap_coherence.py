#!/usr/bin/env python3
"""Cross-artifact roadmap coherence: do the report, the plan and the deck agree?

Why this lane exists. A delivery kit ends up with the same roadmap expressed in
three different artifacts:

  * the REPORT's roadmap        - recommendation -> phase (the source of truth)
  * the PLAN's item set         - work item -> prerequisites, effort, phase
  * the DECK                    - phase claims on slides, and dependencies
                                  asserted in prose in the speaker notes

Each artifact has its own checker and each can be green on its own. Nothing
checks the triangle. A phase corrected in the report and not in the plan, or a
dependency that lives only as a sentence in an appendix bullet, passes every
individual check and reaches leadership as a plan that cannot be executed.

This was not hypothesised. The deck-to-report agreement checker in
`uiowa_rfq_18649_readout_deck` reported "PASS - 0 error(s), 0 warning(s)" on a
report whose roadmap placed R-004 before the two recommendations it is built on,
with a deck that agreed with it perfectly -- while the deck's own appendix slide
said in prose that the dependency existed.

So: prose claims are parsed and checked, phase claims are compared across all
three artifacts by name, and an artifact that was never given dependency
information is reported as NOT ASSESSED rather than coherent. Silence is not a
clean bill of health.

Python 3 standard library only. No network. Deterministic.
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import OrderedDict

ERROR = "error"
WARN = "warning"
INFO = "info"

NOT_ASSESSED = "NOT ASSESSED"
COHERENT = "COHERENT"
INCOHERENT = "INCOHERENT"

# Conservative: only a sentence that literally says "<rec> depends on <rec>..."
# is treated as a dependency claim. A parser that guessed would manufacture
# findings about prose that was never making a claim.
PROSE_DEPENDENCY = re.compile(r"\b(R-\d+)\b[^.]{0,100}?\bdepends on\b([^.]*)", re.IGNORECASE)
REC_ID = re.compile(r"\bR-\d+\b")

RULES = OrderedDict([
    ("RC001_REPORT_ROADMAP_NOT_ASSESSED", "A report roadmap declaring no prerequisites is NOT ASSESSED, never coherent."),
    ("RC002_REPORT_PREREQ_AFTER_DEPENDENT", "No report prerequisite sits in a later phase than its dependent."),
    ("RC003_REPORT_DEPENDENCY_CYCLE", "The report roadmap's prerequisite graph is acyclic."),
    ("RC004_REPORT_DANGLING_DEPENDENCY", "Every declared prerequisite resolves to a recommendation on the roadmap."),
    ("RC005_PLAN_PHASE_DISAGREES_WITH_REPORT", "The plan's phase for a recommendation equals the report's, naming both artifacts."),
    ("RC006_DECK_PHASE_DISAGREES_WITH_REPORT", "The deck's phase claim for a recommendation equals the report's."),
    ("RC007_PLAN_DEPENDENCY_MISSING_FROM_REPORT", "A prerequisite the plan enforces is also declared in the report."),
    ("RC008_REPORT_DEPENDENCY_MISSING_FROM_PLAN", "A prerequisite the report declares is also enforced by the plan."),
    ("RC009_PROSE_DEPENDENCY_UNBACKED", "A dependency asserted in deck prose is backed by a declared field."),
    ("RC010_DEPENDENCY_NEVER_PRESENTED", "A dependency that drives the schedule is mentioned somewhere in the deck."),
    ("RC011_RECOMMENDATION_MISSING_FROM_PLAN", "Every roadmap recommendation has at least one work item in the plan."),
    ("RC012_PLAN_ITEM_WITHOUT_RECOMMENDATION", "Every plan item links back to a recommendation on the roadmap."),
    ("RC013_COLLAPSE_RULE_DECIDES", "A phase disagreement that exists only under one collapse rule is named as such."),
])


class InputError(Exception):
    """Input is unusable. Raised instead of letting a KeyError surface."""


class Finding(object):
    __slots__ = ("code", "severity", "subject", "detail")

    def __init__(self, code, severity, subject, detail):
        self.code = code
        self.severity = severity
        self.subject = subject or "-"
        self.detail = detail

    def as_dict(self):
        return {"code": self.code, "severity": self.severity,
                "subject": self.subject, "detail": self.detail}

    def __repr__(self):
        return "Finding(%s,%s,%s)" % (self.code, self.severity, self.subject)


def errors(findings):
    return [f for f in findings if f.severity == ERROR]


# ---------------------------------------------------------------- loading

def load_json(path):
    if not os.path.exists(path):
        raise InputError("file not found: %s" % path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as exc:
        raise InputError("%s is not valid JSON: %s" % (path, exc))
    if not isinstance(data, dict):
        raise InputError("%s must contain a JSON object at the top level" % path)
    return data


def load_report(path):
    data = load_json(path)
    if "roadmap" not in data:
        raise InputError("report %s has no roadmap" % path)
    rm = data["roadmap"]
    for key in ("phases", "items"):
        if key not in rm:
            raise InputError("report %s roadmap has no %r" % (path, key))
    return data


def load_plan(path):
    if path is None:
        return None
    data = load_json(path)
    if "items" not in data:
        raise InputError("plan %s has no items" % path)
    return data


def load_deck(path):
    if path is None:
        return None
    data = load_json(path)
    if "slides" not in data:
        raise InputError("deck %s has no slides" % path)
    return data


# ---------------------------------------------------------------- views

class RoadmapView(object):
    """One artifact's opinion about phases and prerequisites, normalised."""

    def __init__(self, name, phase_by_rec, deps_by_rec, declares_deps):
        self.name = name
        self.phase_by_rec = phase_by_rec
        self.deps_by_rec = deps_by_rec
        self.declares_deps = declares_deps


def report_view(report):
    rm = report["roadmap"]
    phase_by_rec = OrderedDict((i["rec"], i.get("phase")) for i in rm["items"])
    deps_by_rec = OrderedDict()
    declares = False
    for i in rm["items"]:
        raw = i.get("depends_on")
        if raw is not None:
            declares = True
        deps_by_rec[i["rec"]] = sorted(raw or [])
    return RoadmapView("report", phase_by_rec, deps_by_rec, declares)


def plan_view(plan, rule="last"):
    """Collapse the plan's work items up to the recommendation level.

    A plan has many work items per recommendation; a report roadmap has one
    phase per recommendation. Collapsing many into one needs a rule, and the
    rule was the actual defect the first real cross-lane run exposed: the two
    artifacts disagreed about R-003 because "the phase of a recommendation"
    silently meant different things on each side -- when its work STARTS in one,
    when it COMPLETES in the other.

    So the rule is named, selectable, and reported in the finding rather than
    assumed. The default is "last", because a recommendation is not delivered
    until its final item is; calling it done when its first item starts is the
    optimistic reading, and the optimistic reading is the one that surprises
    people in month four.
    """
    if plan is None:
        return None
    if rule not in ("last", "first"):
        raise InputError("rec_phase_rule must be 'last' or 'first', not %r" % rule)
    phases = plan.get("meta", {}).get("horizon_phases", [])
    pidx = dict((p, n) for n, p in enumerate(phases))
    item_rec = OrderedDict((i["id"], i.get("rec")) for i in plan["items"])
    phase_by_rec, deps_by_rec = OrderedDict(), OrderedDict()
    declares = False
    for item in plan["items"]:
        rec = item.get("rec")
        if not rec:
            continue
        here = item.get("proposed_phase")
        if rec not in phase_by_rec:
            phase_by_rec[rec] = here
        elif rule == "last" and pidx.get(here, -1) > pidx.get(phase_by_rec[rec], -1):
            phase_by_rec[rec] = here
        elif rule == "first" and pidx.get(here, len(pidx)) < pidx.get(phase_by_rec[rec], len(pidx)):
            phase_by_rec[rec] = here
        for p in item.get("prerequisites", []) or []:
            declares = True
            prec = item_rec.get(p)
            if prec and prec != rec:
                deps_by_rec.setdefault(rec, set()).add(prec)
    deps_by_rec = OrderedDict((r, sorted(v)) for r, v in sorted(deps_by_rec.items()))
    for rec in phase_by_rec:
        deps_by_rec.setdefault(rec, [])
    view = RoadmapView("plan", phase_by_rec, deps_by_rec, declares)
    view.rule = rule
    return view


def deck_phase_claims(deck):
    """Every phase a slide asserts, with the slide that asserted it."""
    out = []
    if deck is None:
        return out
    for slide in deck.get("slides", []):
        for claim in slide.get("claims", []) or []:
            if claim.get("type") == "phase" and claim.get("cites"):
                out.append((slide.get("id"), claim["cites"], claim.get("phase")))
    return out


def deck_prose_dependencies(deck):
    """Dependency sentences in deck bullets and speaker notes.

    Only "<rec> depends on <rec>[, <rec>]" is read as a claim. Anything looser
    would invent findings about prose that was not asserting anything.
    """
    out = []
    if deck is None:
        return out
    for slide in deck.get("slides", []):
        texts = list(slide.get("bullets", []) or []) + list(slide.get("speaker_notes", []) or [])
        for text in texts:
            for match in PROSE_DEPENDENCY.finditer(text):
                subject = match.group(1).upper()
                targets = [t.upper() for t in REC_ID.findall(match.group(2))]
                if targets:
                    out.append((slide.get("id"), subject, sorted(set(targets)), text.strip()))
    return out


def deck_mentions(deck):
    blob = []
    if deck is None:
        return ""
    for slide in deck.get("slides", []):
        blob.extend(slide.get("bullets", []) or [])
        blob.extend(slide.get("speaker_notes", []) or [])
        for claim in slide.get("claims", []) or []:
            blob.append(str(claim.get("text", "")))
    return "\n".join(blob)


# ---------------------------------------------------------------- checks

def _cycle(deps):
    WHITE, GREY, BLACK = 0, 1, 2
    colour = dict((n, WHITE) for n in deps)
    stack = []

    def visit(node):
        colour[node] = GREY
        stack.append(node)
        for nxt in sorted(d for d in deps.get(node, []) if d in deps):
            if colour[nxt] == GREY:
                return stack[stack.index(nxt):] + [nxt]
            if colour[nxt] == WHITE:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        colour[node] = BLACK
        return None

    for node in sorted(deps):
        if colour[node] == WHITE:
            found = visit(node)
            if found:
                return found
    return None


def check(report, plan=None, deck=None, rec_phase_rule="last"):
    findings = []
    rv = report_view(report)
    pv = plan_view(plan, rec_phase_rule)
    phases = [p["id"] for p in report["roadmap"]["phases"]]
    pidx = dict((p, n) for n, p in enumerate(phases))

    # --- the report's own roadmap ------------------------------------
    if not rv.declares_deps:
        findings.append(Finding(
            "RC001_REPORT_ROADMAP_NOT_ASSESSED", WARN, "report",
            "no roadmap item declares depends_on, so the report's dependency coherence is "
            "NOT ASSESSED. That is not the same as coherent: a plan nobody expressed "
            "prerequisites for has not been shown to be executable."))
    else:
        for rec, deps in rv.deps_by_rec.items():
            for dep in deps:
                if dep not in rv.phase_by_rec:
                    findings.append(Finding("RC004_REPORT_DANGLING_DEPENDENCY", ERROR, rec,
                                            "%s declares prerequisite %r, which is not on the "
                                            "report roadmap" % (rec, dep)))
        cyc = _cycle(OrderedDict((r, d) for r, d in rv.deps_by_rec.items()))
        if cyc:
            findings.append(Finding("RC003_REPORT_DEPENDENCY_CYCLE", ERROR, " -> ".join(cyc),
                                    "report roadmap prerequisite cycle: %s" % " -> ".join(cyc)))
        else:
            for rec, deps in rv.deps_by_rec.items():
                here = pidx.get(rv.phase_by_rec.get(rec))
                if here is None:
                    continue
                for dep in deps:
                    there = pidx.get(rv.phase_by_rec.get(dep))
                    if there is not None and there > here:
                        findings.append(Finding(
                            "RC002_REPORT_PREREQ_AFTER_DEPENDENT", ERROR, rec,
                            "report schedules %s in %s but its prerequisite %s in %s, which is "
                            "later" % (rec, rv.phase_by_rec[rec], dep, rv.phase_by_rec[dep])))

    # --- report vs plan ----------------------------------------------
    if pv is not None:
        for rec, phase in rv.phase_by_rec.items():
            if rec not in pv.phase_by_rec:
                findings.append(Finding("RC011_RECOMMENDATION_MISSING_FROM_PLAN", ERROR, rec,
                                        "the report roadmap carries %s but no plan item links to "
                                        "it; it has no work behind it" % rec))
            elif pv.phase_by_rec[rec] != phase:
                findings.append(Finding(
                    "RC005_PLAN_PHASE_DISAGREES_WITH_REPORT", ERROR, rec,
                    "report roadmap says %s is in %r; the plan's %s item for it is in %r "
                    "(collapse rule: %s -- a recommendation is not delivered until its final "
                    "item is)" % (rec, phase, rec_phase_rule, pv.phase_by_rec[rec],
                                  rec_phase_rule)))
        # A disagreement that flips when the collapse rule flips is a semantic
        # mismatch between the artifacts, not a scheduling error. Say which.
        other = "first" if rec_phase_rule == "last" else "last"
        ov = plan_view(plan, other)
        for rec, phase in rv.phase_by_rec.items():
            if rec in pv.phase_by_rec and pv.phase_by_rec[rec] != phase \
                    and ov.phase_by_rec.get(rec) == phase:
                findings.append(Finding(
                    "RC013_COLLAPSE_RULE_DECIDES", WARN, rec,
                    "%s agrees with the report under the %r rule and disagrees under %r: the two "
                    "artifacts mean different things by 'the phase of a recommendation'. Decide "
                    "which, and record it." % (rec, other, rec_phase_rule)))
        for rec in pv.phase_by_rec:
            if rec not in rv.phase_by_rec:
                findings.append(Finding("RC012_PLAN_ITEM_WITHOUT_RECOMMENDATION", ERROR, rec,
                                        "the plan carries work for %s, which is not on the report "
                                        "roadmap" % rec))
        if rv.declares_deps and pv.declares_deps:
            for rec in sorted(set(rv.deps_by_rec) & set(pv.deps_by_rec)):
                report_deps, plan_deps = set(rv.deps_by_rec[rec]), set(pv.deps_by_rec[rec])
                for dep in sorted(plan_deps - report_deps):
                    findings.append(Finding(
                        "RC007_PLAN_DEPENDENCY_MISSING_FROM_REPORT", WARN, rec,
                        "the plan enforces %s before %s, but the report roadmap does not declare "
                        "that prerequisite" % (dep, rec)))
                for dep in sorted(report_deps - plan_deps):
                    findings.append(Finding(
                        "RC008_REPORT_DEPENDENCY_MISSING_FROM_PLAN", WARN, rec,
                        "the report declares %s before %s, but no plan item enforces it"
                        % (dep, rec)))

    # --- report vs deck ----------------------------------------------
    for slide_id, rec, phase in deck_phase_claims(deck):
        expected = rv.phase_by_rec.get(rec)
        if expected is not None and phase != expected:
            findings.append(Finding("RC006_DECK_PHASE_DISAGREES_WITH_REPORT", ERROR, slide_id,
                                    "slide %s puts %s in %r; the report roadmap says %r"
                                    % (slide_id, rec, phase, expected)))

    # --- prose promoted to a checkable claim -------------------------
    for slide_id, subject, targets, sentence in deck_prose_dependencies(deck):
        declared = set(rv.deps_by_rec.get(subject, []))
        unbacked = [t for t in targets if t not in declared]
        if unbacked:
            findings.append(Finding(
                "RC009_PROSE_DEPENDENCY_UNBACKED", ERROR if rv.declares_deps else WARN, slide_id,
                "slide %s states %s depends on %s, but %s not declared in the report roadmap. "
                "A dependency that exists only as a sentence cannot be checked: %r"
                % (slide_id, subject, ", ".join(targets),
                   "that is" if len(unbacked) == 1 else "those are", sentence[:110])))

    # --- a dependency leadership is never told about -----------------
    if deck is not None and rv.declares_deps:
        blob = deck_mentions(deck)
        for rec, deps in rv.deps_by_rec.items():
            for dep in deps:
                if rec not in blob or dep not in blob:
                    findings.append(Finding(
                        "RC010_DEPENDENCY_NEVER_PRESENTED", WARN, rec,
                        "%s waits on %s, which is why it sits where it does, and the deck never "
                        "puts both in front of the room" % (rec, dep)))

    findings.sort(key=lambda f: ({ERROR: 0, WARN: 1, INFO: 2}[f.severity], f.subject, f.code))
    return findings


def verdict(findings, report):
    if errors(findings):
        return INCOHERENT
    if any(f.code == "RC001_REPORT_ROADMAP_NOT_ASSESSED" for f in findings):
        return NOT_ASSESSED
    _ = report
    return COHERENT


# ---------------------------------------------------------------- render

W = 78


def _line(ch="-"):
    return "+" + ch * (W - 2) + "+"


def _row(text=""):
    t = str(text).encode("ascii", "replace").decode("ascii")
    return "| " + t[:W - 4].ljust(W - 4) + " |"


def render_ascii(report, plan, deck, findings, rec_phase_rule="last"):
    rv = report_view(report)
    pv = plan_view(plan, rec_phase_rule)
    claims = {}
    for _sid, rec, phase in deck_phase_claims(deck):
        claims.setdefault(rec, set()).add(phase)
    out = [_line("="), _row("ROADMAP COHERENCE - three artifacts, one plan"), _line("=")]
    out.append(_row("VERDICT: %s" % verdict(findings, report)))
    out.append(_line("="))
    out.append(_row("LEGEND  ok  all artifacts agree    XX  they disagree"))
    out.append(_row("        ??  the artifact says nothing about this"))
    out.append(_row("        marks only, no colour"))
    out.append(_line("="))
    out.append(_row(" %-6s %-12s %-12s %-12s %s" % ("rec", "report", "plan", "deck", "")))
    out.append(_line("-"))
    for rec in rv.phase_by_rec:
        rp = rv.phase_by_rec.get(rec) or "??"
        pp = (pv.phase_by_rec.get(rec) if pv else None) or "??"
        dv = sorted(claims.get(rec, []))
        dp = (", ".join(dv) if dv else "??")
        vals = [v for v in (rp, pp, dp) if v != "??"]
        mark = "ok" if len(set(vals)) <= 1 else "XX"
        out.append(_row(" %-6s %-12s %-12s %-12s %s" % (rec, rp, pp, dp[:12], mark)))
    out.append(_line("="))
    out.append(_row("DECLARED PREREQUISITES"))
    out.append(_line("-"))
    if not rv.declares_deps:
        out.append(_row("  report declares none -> dependency coherence NOT ASSESSED"))
        out.append(_row("  (an absent declaration is not a clean bill of health)"))
    else:
        for rec, deps in rv.deps_by_rec.items():
            out.append(_row("  %-6s <- %s" % (rec, ", ".join(deps) if deps else "(none)")))
    out.append(_line("="))
    out.append(_row("FINDINGS"))
    out.append(_line("-"))
    if not findings:
        out.append(_row("  none: the three artifacts agree and the plan is executable"))
    for f in findings:
        out.append(_row("  [%s] %s %s" % (f.severity[:4], f.code, f.subject)))
        for chunk in _wrap(f.detail, W - 10):
            out.append(_row("       " + chunk))
    out.append(_line("="))
    return "\n".join(out) + "\n"


def _wrap(text, width):
    words, line, out = str(text).split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out


def render_markdown(report, plan, deck, findings):
    rv = report_view(report)
    out = ["# Roadmap coherence report", ""]
    out.append("**Verdict: %s**" % verdict(findings, report))
    out.append("")
    if verdict(findings, report) == NOT_ASSESSED:
        out.append("> The report roadmap declares no prerequisites, so its coherence has not been "
                   "assessed. This is reported as NOT ASSESSED rather than as a pass.")
        out.append("")
    out.append("| Severity | Rule | Subject | Detail |")
    out.append("|---|---|---|---|")
    for f in findings:
        out.append("| %s | %s | %s | %s |" % (f.severity, f.code, f.subject,
                                              f.detail.replace("|", "\\|")))
    if not findings:
        out.append("| - | - | - | No disagreement between the report, the plan and the deck. |")
    out.append("")
    out.append("## Declared prerequisites (report)")
    out.append("")
    for rec, deps in rv.deps_by_rec.items():
        out.append("- `%s` <- %s" % (rec, ", ".join("`%s`" % d for d in deps) if deps else "(none)"))
    out.append("")
    out.append("## Rules")
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



def write_csv(path, report, plan, deck, rec_phase_rule="last"):
    rv = report_view(report)
    pv = plan_view(plan, rec_phase_rule)
    claims = {}
    for sid, rec, phase in deck_phase_claims(deck):
        claims.setdefault(rec, []).append("%s=%s" % (sid, phase))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        write_provenance(fh, provenance_statement(
            report.get("meta", {}), (plan or {}).get("meta", {}), (deck or {}).get("meta", {})))
        w = csv.writer(fh)
        w.writerow(["rec", "report_phase", "plan_phase", "deck_phase_claims",
                    "report_depends_on", "plan_depends_on", "agree"])
        for rec in rv.phase_by_rec:
            rp = rv.phase_by_rec.get(rec)
            pp = pv.phase_by_rec.get(rec) if pv else ""
            dcs = ";".join(sorted(claims.get(rec, [])))
            vals = set(v for v in (rp, pp) if v)
            for c in claims.get(rec, []):
                vals.add(c.split("=", 1)[1])
            w.writerow([rec, rp or "", pp or "", dcs,
                        ";".join(rv.deps_by_rec.get(rec, [])),
                        ";".join(pv.deps_by_rec.get(rec, [])) if pv else "",
                        "yes" if len(vals) <= 1 else "no"])


# ---------------------------------------------------------------- cli

def _load(args):
    return (load_report(args.report), load_plan(getattr(args, "plan", None)),
            load_deck(getattr(args, "deck", None)))


def cmd_check(args):
    report, plan, deck = _load(args)
    findings = check(report, plan, deck, args.rec_phase_rule)
    if args.json:
        sys.stdout.write(json.dumps([f.as_dict() for f in findings], indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(render_markdown(report, plan, deck, findings))
    return 1 if errors(findings) else 0


def cmd_report(args):
    report, plan, deck = _load(args)
    findings = check(report, plan, deck, args.rec_phase_rule)
    outdir = args.outdir
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    with open(os.path.join(outdir, "coherence-ascii.txt"), "w", encoding="utf-8", newline="") as fh:
        fh.write(render_ascii(report, plan, deck, findings, args.rec_phase_rule))
    with open(os.path.join(outdir, "coherence-report.md"), "w", encoding="utf-8", newline="") as fh:
        fh.write(render_markdown(report, plan, deck, findings))
    write_csv(os.path.join(outdir, "phase-agreement.csv"), report, plan, deck,
              args.rec_phase_rule)
    for name in ("coherence-ascii.txt", "coherence-report.md", "phase-agreement.csv"):
        sys.stdout.write("wrote %s\n" % os.path.join(outdir, name))
    sys.stdout.write("verdict: %s (%d error(s), %d warning(s))\n"
                     % (verdict(findings, report), len(errors(findings)),
                        len(findings) - len(errors(findings))))
    return 1 if errors(findings) else 0


def cmd_rules(args):
    for code, desc in RULES.items():
        sys.stdout.write("%-42s %s\n" % (code, desc))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Check that a report roadmap, a work plan and a readout deck agree.")
    sub = ap.add_subparsers(dest="cmd")
    for name, fn in (("check", cmd_check), ("report", cmd_report)):
        p = sub.add_parser(name)
        p.add_argument("--report", required=True)
        p.add_argument("--plan", default=None)
        p.add_argument("--deck", default=None)
        p.add_argument("--rec-phase-rule", choices=("last", "first"), default="last",
                       dest="rec_phase_rule",
                       help="how a recommendation's phase is read off a multi-item plan "
                            "(default: last -- not delivered until its final item is)")
        if name == "check":
            p.add_argument("--json", action="store_true")
        else:
            p.add_argument("--outdir", default="examples")
        p.set_defaults(func=fn)
    u = sub.add_parser("rules")
    u.set_defaults(func=cmd_rules)
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 2
    try:
        return args.func(args)
    except InputError as exc:
        sys.stderr.write("INPUT ERROR: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
