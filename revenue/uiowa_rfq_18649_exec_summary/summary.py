"""The summary compiler: statements in, a traceable document out -- or a rejection.

This is not a template with a reminder to cite your sources. It is a compiler. A
statement is authored as text bound to finding IDs, and it only reaches the rendered
document if it survives every check below. A statement that fails does not get
silently softened or quietly dropped: it lands in the compile report with the reason
and the specific remedy, so the author fixes the sentence rather than the tool
fixing it for them.

Checks, in the order they are applied:

  NO_CITATION             the sentence cites nothing
  UNKNOWN_FINDING         it cites an ID that does not exist in the findings store
  ASSERTS_NOT_ESTABLISHED its evidence cannot support an assertion at all
  OVERCLAIM               its phrasing claims more than its weakest citation carries
  SCOPE_OVERREACH         it generalizes past the units the findings were established in
  UNSUPPORTED_NUMBER      it contains a figure that appears in none of its citations
  INDIVIDUAL_ATTRIBUTION  it evaluates a person rather than a workflow or a system

The one that matters most is OVERCLAIM, because it is the failure that passes review.
An unsourced sentence is obvious. A sentence with a real citation that says more than
the citation supports looks like diligence, and reads as fact to a reader who will
never open the appendix.
"""

import json
import re
from dataclasses import dataclass

from evidence import REMEDY, STRENGTH_MEANING, at_most, is_stronger

# ------------------------------------------------- reading strength off phrasing

_SINGLE_SOURCE_MARKERS = (
    "one unit", "one team", "one department", "one group", "a single unit",
    "a single team", "in one case", "one respondent", "a single respondent",
    "one interview",
)

_HEDGE_MARKERS = (
    "evidence indicates", "evidence suggests", "indicates that", "suggests that",
    "appears to", "appeared to", "in the units reviewed", "of the units reviewed",
    "among the units reviewed", "where observed", "reported that", "self-reported",
    "may ", "some units", "several units",
)

_UNIVERSAL_MARKERS = (
    "all units", "every unit", "all teams", "every team", "across the institution",
    "institution-wide", "institution wide", "organization-wide", "organisation-wide",
    "universally", "no unit", "none of the units", "throughout the institution",
    "in all cases", "without exception",
)

# Narrow by design: catches evaluative language about PEOPLE, which the engagement
# rules forbid. It does not attempt general name detection -- a broad name matcher
# produces false positives on system and unit names and would be switched off within
# a week, which is worse than a narrow check that people trust.
_INDIVIDUAL_MARKERS = (
    "underperform", "poor performer", "individual performance", "failed to perform",
    "is not competent", "incompetent", "individual staff member", "this employee",
    "rated the staff", "ranked the staff",
)

_NUMBER = re.compile(r"\b\d+(?:\.\d+)?%?\b")


@dataclass(frozen=True)
class Statement:
    statement_id: str
    text: str
    cites: tuple


def claimed_strength(text):
    """What the sentence's own phrasing asserts, read off the text."""
    lowered = text.lower()
    if any(marker in lowered for marker in _SINGLE_SOURCE_MARKERS):
        return "SINGLE_SOURCE"
    if any(marker in lowered for marker in _HEDGE_MARKERS):
        return "INDICATED"
    return "SETTLED"


def claims_universal_scope(text):
    lowered = text.lower()
    return [marker for marker in _UNIVERSAL_MARKERS if marker in lowered]


def evaluates_an_individual(text):
    lowered = text.lower()
    return [marker for marker in _INDIVIDUAL_MARKERS if marker in lowered]


def _supported_numbers(findings):
    """Every figure a statement is allowed to use, taken from its citations."""
    allowed = set()
    for finding in findings:
        allowed.update(_NUMBER.findall(finding.observed))
        for attribute in (finding.units_established, finding.units_in_scope,
                          finding.corroborating_sources):
            if isinstance(attribute, int):
                allowed.add(str(attribute))
    return allowed


def check_statement(statement, store):
    """Return (ok, problems). Each problem carries a code, a reason and a remedy."""
    problems = []

    if not statement.cites:
        problems.append({
            "code": "NO_CITATION",
            "reason": "the statement cites no finding",
            "remedy": "bind the statement to the finding ID that establishes it, or "
                      "delete the statement",
        })
        return False, problems

    missing = [finding_id for finding_id in statement.cites if finding_id not in store]
    if missing:
        problems.append({
            "code": "UNKNOWN_FINDING",
            "reason": f"cites finding ID(s) not present in the findings store: "
                      f"{', '.join(missing)}",
            "remedy": "correct the finding ID, or record the finding before citing it",
        })
        return False, problems

    cited = [store.get(finding_id) for finding_id in statement.cites]

    supported = "SETTLED"
    for finding in cited:
        supported = at_most(supported, finding.max_strength)
    claimed = claimed_strength(statement.text)

    if supported == "NOT_ESTABLISHED":
        weakest = [f.finding_id for f in cited if f.max_strength == "NOT_ESTABLISHED"]
        problems.append({
            "code": "ASSERTS_NOT_ESTABLISHED",
            "reason": f"cited finding(s) {', '.join(weakest)} are not established "
                      f"(basis or confidence is UNKNOWN / no evidence attached), so "
                      f"nothing may be asserted from them",
            "remedy": REMEDY["NOT_ESTABLISHED"],
        })
    elif is_stronger(claimed, supported):
        weakest = [f.finding_id for f in cited if f.max_strength == supported]
        problems.append({
            "code": "OVERCLAIM",
            "reason": f"phrasing asserts {claimed}, but the weakest citation "
                      f"({', '.join(weakest)}) supports only {supported}: "
                      f"{STRENGTH_MEANING[supported]}",
            "remedy": REMEDY.get(supported, "weaken the assertion to match the evidence"),
        })

    universal = claims_universal_scope(statement.text)
    if universal:
        partial = [f"{f.finding_id} ({f.scope_label})" for f in cited
                   if not f.scope_is_universal]
        if partial:
            problems.append({
                "code": "SCOPE_OVERREACH",
                "reason": f"phrasing generalizes to all units ({', '.join(universal)}) "
                          f"but the citation(s) cover only part of scope: "
                          f"{', '.join(partial)}",
                "remedy": "state the actual scope, e.g. 'in the N of M units "
                          "reviewed', or cite a finding established across full scope",
            })

    allowed = _supported_numbers(cited)
    used = set(_NUMBER.findall(statement.text))
    unsupported = sorted(used - allowed)
    if unsupported:
        problems.append({
            "code": "UNSUPPORTED_NUMBER",
            "reason": f"figure(s) {', '.join(unsupported)} appear in the statement but "
                      f"in none of its citations",
            "remedy": "use the figure exactly as the finding records it, or remove it",
        })

    individual = evaluates_an_individual(statement.text)
    if individual:
        problems.append({
            "code": "INDIVIDUAL_ATTRIBUTION",
            "reason": f"language evaluates a person rather than a workflow or system: "
                      f"{', '.join(individual)}",
            "remedy": "restate as an observation about the process, the system or the "
                      "unit; individual performance is out of scope for this engagement",
        })

    return (not problems), problems


def compile_summary(document, store):
    """Compile a draft into an accepted set, a rejection set and a coverage report."""
    statements = {s.statement_id: s for s in document["statements"]}
    accepted, rejected = {}, []

    for statement_id in sorted(statements):
        statement = statements[statement_id]
        ok, problems = check_statement(statement, store)
        if ok:
            cited = [store.get(fid) for fid in statement.cites]
            supported = "SETTLED"
            for finding in cited:
                supported = at_most(supported, finding.max_strength)
            accepted[statement_id] = {
                "statement": statement,
                "supported_strength": supported,
                "claimed_strength": claimed_strength(statement.text),
                "findings": cited,
            }
        else:
            rejected.append({"statement_id": statement_id, "text": statement.text,
                             "cites": list(statement.cites), "problems": problems})

    cited_ids = {finding.finding_id
                 for entry in accepted.values() for finding in entry["findings"]}
    uncited = [finding for finding in store.all()
               if finding.finding_id not in cited_ids]

    # Sections keep only their accepted statements, in the author's declared order.
    sections = []
    for section in document["sections"]:
        kept = [sid for sid in section["statement_ids"] if sid in accepted]
        dropped = [sid for sid in section["statement_ids"] if sid not in accepted]
        sections.append({"section_id": section["section_id"],
                         "heading": section["heading"],
                         "statement_ids": kept, "dropped_statement_ids": dropped})

    unresolved = []
    for finding in store.all():
        for item in finding.unresolved:
            unresolved.append({"finding_id": finding.finding_id,
                               "area": finding.area, "item": item})

    return {
        "source_label": store.source_label,
        "title": document.get("title", "Executive summary"),
        "sections": sections,
        "accepted": accepted,
        "rejected": rejected,
        "uncited_findings": uncited,
        "uncited_significant": [f for f in uncited
                                if f.severity in ("SIGNIFICANT", "CRITICAL")],
        "unresolved": unresolved,
        "stats": {
            "statements_submitted": len(statements),
            "statements_accepted": len(accepted),
            "statements_rejected": len(rejected),
            "findings_total": len(store),
            "findings_cited": len(cited_ids),
            "findings_uncited": len(uncited),
        },
    }


def load_document(path):
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    statements = [Statement(statement_id=record["statement_id"],
                            text=record["text"],
                            cites=tuple(record.get("cites", [])))
                  for record in payload["statements"]]
    return {"title": payload.get("title", "Executive summary"),
            "sections": payload["sections"],
            "statements": statements,
            "_meta": payload}
