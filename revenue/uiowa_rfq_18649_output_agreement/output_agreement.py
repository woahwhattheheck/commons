#!/usr/bin/env python3
"""Cross-output agreement checker for the UIOWA RFQ 18649 report bundle (UIOWA-117).

STATUS: PROPOSED CONSISTENCY CHECK / NOT A UNIVERSITY FINDING.

The problem this exists for
---------------------------
A final delivery is not one artifact. It is a findings matrix, a recommendation
register, an executive summary and a presentation, and in this engagement they
are produced by different people at different times. Each one is internally
consistent. Each one's own tests pass.

Nothing checks that they agree with each other.

That is how an executive summary ends up saying "three priority findings" over a
matrix that holds four, how a deck puts a recommendation in 0-90 days while the
register says 90-180, and - worst - how an estimate that the register records as
UNKNOWN turns up in a slide as a number. None of those are caught by the lane
that produced them, because within that lane nothing is wrong.

What it checks
--------------
Four artifact classes, seven mismatch classes. Every diagnostic names **both**
conflicting artifacts and the exact field, because "the outputs disagree" is not
actionable and "executive_summary.asserted_count.value=3 conflicts with
matrix(status in PARTIAL,CONFLICT)=4" is.

The derived-value rule
----------------------
Counts, states, phase labels and estimates that appear in an executive summary or
a deck are **derived** from the matrix and the register. They are not independent
facts. So `regenerate_derived()` recomputes them from source, which is what makes
the work order's completion condition - "actual regenerated examples agree after
correction" - a thing that can be executed rather than asserted.

Python 3 standard library only. No network.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import sys
from dataclasses import dataclass, asdict, field
from typing import Any, Callable, Sequence

# Artifact class names, used in diagnostics.
MATRIX = "matrix"
REGISTER = "recommendation_register"
SUMMARY = "executive_summary"
PRESENTATION = "presentation_source"

ARTIFACTS = (MATRIX, REGISTER, SUMMARY, PRESENTATION)

UNKNOWN = "UNKNOWN"

# Statuses that mean "we could not assess this cell" rather than "we assessed it
# and it is weak". Keeping these separate is the whole point of the matrix, and a
# downstream output that states a result for one of them is a fabrication.
UNASSESSED_STATUSES = {UNKNOWN, "", "NOT_APPLICABLE"}

# Named sets a prose claim may count. The checker owns these definitions so that
# "priority findings" means the same thing in every artifact.
COUNTABLE_SETS: dict[str, str] = {
    "findings": "every row in the matrix",
    "assessed_cells": "matrix rows whose status is not UNKNOWN/NOT_APPLICABLE",
    "unassessed_cells": "matrix rows whose status is UNKNOWN or NOT_APPLICABLE",
    "priority_findings": "matrix rows with status PARTIAL or CONFLICT",
    "supported_findings": "matrix rows with status SUPPORTED",
    "recommendations": "every row in the recommendation register",
    "near_term_recommendations": "register rows with horizon 0-90",
}

ERROR = "ERROR"
WARN = "WARN"


@dataclass
class Diagnostic:
    code: str
    severity: str
    artifacts: list[str]
    field_name: str
    subject: str
    detail: str

    def __str__(self) -> str:
        return (f"[{self.severity}] {self.code}  {' <-> '.join(self.artifacts)}"
                f"  field={self.field_name}  {self.subject}: {self.detail}")

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Bundle:
    """The four outputs of one report delivery, loaded together."""
    matrix: list[dict] = field(default_factory=list)
    register: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    presentation: dict = field(default_factory=dict)

    # -- derived views -----------------------------------------------------
    def finding_ids(self) -> set[str]:
        return {r["finding_id"] for r in self.matrix if r.get("finding_id")}

    def recommendation_ids(self) -> set[str]:
        return {r["recommendation_id"] for r in self.register if r.get("recommendation_id")}

    def defined_ids(self) -> set[str]:
        return self.finding_ids() | self.recommendation_ids()

    def finding(self, fid: str) -> dict | None:
        return next((r for r in self.matrix if r.get("finding_id") == fid), None)

    def recommendation(self, rid: str) -> dict | None:
        return next((r for r in self.register if r.get("recommendation_id") == rid), None)

    def claims(self) -> list[tuple[str, dict]]:
        """(artifact_name, claim) for every claim in the prose artifacts."""
        out: list[tuple[str, dict]] = []
        for c in self.summary.get("claims", []):
            out.append((SUMMARY, c))
        for c in self.presentation.get("claims", []):
            out.append((PRESENTATION, c))
        return out

    def count_set(self, name: str) -> int | None:
        """Compute a named set's size from the source artifacts."""
        m, r = self.matrix, self.register
        if name == "findings":
            return len(m)
        if name == "assessed_cells":
            return len([x for x in m if x.get("status") not in UNASSESSED_STATUSES])
        if name == "unassessed_cells":
            return len([x for x in m if x.get("status") in UNASSESSED_STATUSES])
        if name == "priority_findings":
            return len([x for x in m if x.get("status") in ("PARTIAL", "CONFLICT")])
        if name == "supported_findings":
            return len([x for x in m if x.get("status") == "SUPPORTED"])
        if name == "recommendations":
            return len(r)
        if name == "near_term_recommendations":
            return len([x for x in r if x.get("horizon") == "0-90"])
        return None


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_bundle(path: str) -> Bundle:
    """Load a bundle directory. A missing artifact loads empty, not fatally -
    the checker's job is to report disagreement, including 'this output is
    absent', rather than to refuse to run."""
    def rows(name):
        p = os.path.join(path, name)
        if not os.path.exists(p):
            return []
        with open(p, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def doc(name):
        p = os.path.join(path, name)
        if not os.path.exists(p):
            return {}
        with open(p, encoding="utf-8") as f:
            return json.load(f)

    return Bundle(matrix=rows("matrix.csv"),
                  register=rows("recommendations.csv"),
                  summary=doc("executive_summary.json"),
                  presentation=doc("presentation.json"))


def save_bundle(b: Bundle, path: str) -> None:
    os.makedirs(path, exist_ok=True)
    if b.matrix:
        with open(os.path.join(path, "matrix.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(b.matrix[0].keys()))
            w.writeheader()
            w.writerows(b.matrix)
    if b.register:
        with open(os.path.join(path, "recommendations.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(b.register[0].keys()))
            w.writeheader()
            w.writerows(b.register)
    with open(os.path.join(path, "executive_summary.json"), "w", encoding="utf-8") as f:
        json.dump(b.summary, f, indent=2)
    with open(os.path.join(path, "presentation.json"), "w", encoding="utf-8") as f:
        json.dump(b.presentation, f, indent=2)


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------

def _claim_where(artifact: str, claim: dict) -> str:
    cid = claim.get("claim_id", "<unidentified claim>")
    slide = claim.get("slide_id")
    return f"{artifact}:{cid}" + (f" (slide {slide})" if slide else "")


def check_dangling_ids(b: Bundle) -> list[Diagnostic]:
    """An ID cited by a prose output that no source artifact defines."""
    out: list[Diagnostic] = []
    defined = b.defined_ids()
    for artifact, claim in b.claims():
        for cited in claim.get("cites", []):
            if cited not in defined:
                target = MATRIX if cited.startswith("FND") else REGISTER
                out.append(Diagnostic(
                    "DANGLING_ID", ERROR, [artifact, target], "cites",
                    _claim_where(artifact, claim),
                    f"cites '{cited}', which is not defined in the {target}. "
                    f"A reader following this citation reaches nothing."))
    # A recommendation citing a finding that does not exist is the same defect
    # one layer down, and it is worth naming separately.
    for r in b.register:
        for ref in [x for x in (r.get("finding_refs") or "").split(";") if x]:
            if ref not in b.finding_ids():
                out.append(Diagnostic(
                    "DANGLING_ID", ERROR, [REGISTER, MATRIX], "finding_refs",
                    r.get("recommendation_id", "<unidentified>"),
                    f"cites finding '{ref}', which the matrix does not define."))
    return out


def check_counts(b: Bundle) -> list[Diagnostic]:
    """A count asserted in prose against the rows that actually exist."""
    out: list[Diagnostic] = []
    for artifact, claim in b.claims():
        ac = claim.get("asserted_count")
        if not ac:
            continue
        name, value = ac.get("of"), ac.get("value")
        actual = b.count_set(name)
        if actual is None:
            out.append(Diagnostic(
                "UNKNOWN_COUNT_SET", WARN, [artifact], "asserted_count.of",
                _claim_where(artifact, claim),
                f"counts '{name}', which the checker has no definition for; "
                f"known sets: {', '.join(sorted(COUNTABLE_SETS))}"))
            continue
        if value != actual:
            source = REGISTER if "recommendation" in name else MATRIX
            out.append(Diagnostic(
                "COUNT_MISMATCH", ERROR, [artifact, source], "asserted_count.value",
                _claim_where(artifact, claim),
                f"states {value} for '{name}' ({COUNTABLE_SETS[name]}), "
                f"but the {source} holds {actual}."))
    return out


def check_states(b: Bundle) -> list[Diagnostic]:
    """A finding's state as stated downstream vs. the matrix."""
    out: list[Diagnostic] = []
    for artifact, claim in b.claims():
        st = claim.get("asserted_state")
        if not st:
            continue
        fid, stated = st.get("finding_id"), st.get("status")
        row = b.finding(fid)
        if row is None:
            out.append(Diagnostic(
                "DANGLING_ID", ERROR, [artifact, MATRIX], "asserted_state.finding_id",
                _claim_where(artifact, claim),
                f"states a status for '{fid}', which the matrix does not define."))
            continue
        actual = row.get("status")
        if actual in UNASSESSED_STATUSES and stated not in UNASSESSED_STATUSES:
            out.append(Diagnostic(
                "UNASSESSED_RESULT_CLAIMED", ERROR, [artifact, MATRIX], "status",
                _claim_where(artifact, claim),
                f"states '{fid}' is {stated}, but the matrix records it as "
                f"{actual or 'blank'} - the cell was not assessed. An unassessed "
                f"cell is a statement about the evidence, not a result."))
        elif stated != actual:
            out.append(Diagnostic(
                "STATE_MISMATCH", ERROR, [artifact, MATRIX], "status",
                _claim_where(artifact, claim),
                f"states '{fid}' is {stated}; the matrix records {actual}."))
    return out


def check_phases(b: Bundle) -> list[Diagnostic]:
    """A recommendation's phase label downstream vs. the register."""
    out: list[Diagnostic] = []
    for artifact, claim in b.claims():
        ah = claim.get("asserted_horizon")
        if not ah:
            continue
        rid, stated = ah.get("recommendation_id"), ah.get("horizon")
        row = b.recommendation(rid)
        if row is None:
            out.append(Diagnostic(
                "DANGLING_ID", ERROR, [artifact, REGISTER], "asserted_horizon.recommendation_id",
                _claim_where(artifact, claim),
                f"places '{rid}' in a phase, but the register does not define it."))
            continue
        actual = row.get("horizon")
        if actual in ("", UNKNOWN) and stated not in ("", UNKNOWN):
            out.append(Diagnostic(
                "PHASE_FABRICATED", ERROR, [artifact, REGISTER], "horizon",
                _claim_where(artifact, claim),
                f"places '{rid}' in phase {stated}, but the register records the "
                f"horizon as {actual or 'blank'}. A recommendation with no "
                f"sequencing input must stay unsequenced, not be given a phase."))
        elif stated != actual:
            out.append(Diagnostic(
                "PHASE_MISMATCH", ERROR, [artifact, REGISTER], "horizon",
                _claim_where(artifact, claim),
                f"places '{rid}' in phase {stated}; the register records {actual}."))
    return out


def check_estimates(b: Bundle) -> list[Diagnostic]:
    """The one that matters most: an estimate appearing where the source has none."""
    out: list[Diagnostic] = []
    for artifact, claim in b.claims():
        ae = claim.get("asserted_estimate")
        if not ae:
            continue
        rid, stated = ae.get("recommendation_id"), ae.get("estimate")
        row = b.recommendation(rid)
        if row is None:
            out.append(Diagnostic(
                "DANGLING_ID", ERROR, [artifact, REGISTER], "asserted_estimate.recommendation_id",
                _claim_where(artifact, claim),
                f"states an estimate for '{rid}', which the register does not define."))
            continue
        actual = (row.get("resource_note") or "").strip()
        if _is_unknown(actual) and not _is_unknown(stated):
            out.append(Diagnostic(
                "ESTIMATE_FABRICATED", ERROR, [artifact, REGISTER], "resource_note",
                _claim_where(artifact, claim),
                f"states '{stated}' for {rid}, but the register records "
                f"'{actual or 'blank'}'. A missing estimate became a number "
                f"somewhere between the register and this output."))
        elif stated != actual:
            out.append(Diagnostic(
                "ESTIMATE_MISMATCH", ERROR, [artifact, REGISTER], "resource_note",
                _claim_where(artifact, claim),
                f"states '{stated}' for {rid}; the register records '{actual}'."))
    return out


def _is_unknown(v: str | None) -> bool:
    return not v or not str(v).strip() or str(v).strip().upper().startswith(UNKNOWN)


def check_coverage(b: Bundle) -> list[Diagnostic]:
    """Structural agreement: is anything present in one output and absent everywhere else."""
    out: list[Diagnostic] = []
    for name, rows in ((MATRIX, b.matrix), (REGISTER, b.register)):
        if not rows:
            out.append(Diagnostic("ARTIFACT_EMPTY", ERROR, [name], "-", name,
                                  "artifact is empty or absent; the bundle cannot be checked "
                                  "against it, and agreement cannot be claimed."))
    for name, doc in ((SUMMARY, b.summary), (PRESENTATION, b.presentation)):
        if not doc.get("claims"):
            out.append(Diagnostic("ARTIFACT_EMPTY", ERROR, [name], "claims", name,
                                  "artifact declares no claims; nothing in it is checkable "
                                  "against the source records."))
    # A duplicate id makes every cross-output citation ambiguous.
    for label, rows, key in ((MATRIX, b.matrix, "finding_id"),
                             (REGISTER, b.register, "recommendation_id")):
        seen: set[str] = set()
        for r in rows:
            v = r.get(key)
            if v in seen:
                out.append(Diagnostic("DUPLICATE_ID", ERROR, [label], key, v or "<blank>",
                                      "appears more than once; a citation to it is ambiguous."))
            seen.add(v)
    return out


CHECKS: tuple[Callable[[Bundle], list[Diagnostic]], ...] = (
    check_coverage, check_dangling_ids, check_counts,
    check_states, check_phases, check_estimates,
)


def check_bundle(b: Bundle) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    for fn in CHECKS:
        out.extend(fn(b))
    return out


def errors(ds: Sequence[Diagnostic]) -> list[Diagnostic]:
    return [d for d in ds if d.severity == ERROR]


# ---------------------------------------------------------------------------
# Regeneration - what makes "agree after correction" executable
# ---------------------------------------------------------------------------

def regenerate_derived(b: Bundle) -> Bundle:
    """Recompute every derived value in the prose outputs from the source records.

    Counts, asserted states, phase labels and estimates are NOT independent facts
    - they are views of the matrix and the register. Correcting a disagreement
    means recomputing them from source, not editing the prose until the checker
    goes quiet. Free-text `text` is never touched: a human wrote it, and this
    function has no business rewriting it.

    A claim citing an ID that does not exist cannot be regenerated - there is no
    source to regenerate it from - so it is left alone and stays an error. That
    is correct: a dangling citation is a content defect, not a stale view.
    """
    out = copy.deepcopy(b)
    for doc in (out.summary, out.presentation):
        for claim in doc.get("claims", []):
            ac = claim.get("asserted_count")
            if ac and (actual := out.count_set(ac.get("of"))) is not None:
                ac["value"] = actual
            st = claim.get("asserted_state")
            if st and (row := out.finding(st.get("finding_id"))):
                st["status"] = row.get("status")
            ah = claim.get("asserted_horizon")
            if ah and (row := out.recommendation(ah.get("recommendation_id"))):
                ah["horizon"] = row.get("horizon")
            ae = claim.get("asserted_estimate")
            if ae and (row := out.recommendation(ae.get("recommendation_id"))):
                ae["estimate"] = (row.get("resource_note") or "").strip()
    return out


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def render(ds: Sequence[Diagnostic], bundle_name: str = "") -> str:
    errs = errors(ds)
    warns = [d for d in ds if d.severity == WARN]
    L = [f"CROSS-OUTPUT AGREEMENT{(' - ' + bundle_name) if bundle_name else ''}",
         "=" * 62,
         f"errors: {len(errs)}   warnings: {len(warns)}"]
    by_code: dict[str, int] = {}
    for d in ds:
        by_code[d.code] = by_code.get(d.code, 0) + 1
    for code in sorted(by_code):
        L.append(f"  {code:<28} {by_code[code]}")
    L.append("")
    if not errs:
        L.append("PASS - the four outputs agree.")
    else:
        L.append("FAIL - the outputs disagree:")
        L.append("")
        for d in ds:
            L.append(f"[{d.code}] {d.severity}")
            L.append(f"  conflict  : {' <-> '.join(d.artifacts)}")
            L.append(f"  field     : {d.field_name}")
            L.append(f"  subject   : {d.subject}")
            L.append(f"  detail    : {d.detail}")
            L.append("")
    return "\n".join(L)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check that a report bundle's four outputs agree.")
    ap.add_argument("bundle", help="bundle directory")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--regenerate", metavar="OUT",
                    help="recompute derived values from source and write the corrected bundle")
    a = ap.parse_args(argv)

    b = load_bundle(a.bundle)
    ds = check_bundle(b)
    if a.json:
        print(json.dumps([d.as_dict() for d in ds], indent=2))
    else:
        print(render(ds, os.path.basename(os.path.normpath(a.bundle))))

    if a.regenerate:
        fixed = regenerate_derived(b)
        save_bundle(fixed, a.regenerate)
        after = check_bundle(fixed)
        print()
        print(render(after, os.path.basename(os.path.normpath(a.regenerate)) + " (regenerated)"))
        return 1 if errors(after) else 0

    return 1 if errors(ds) else 0


if __name__ == "__main__":
    raise SystemExit(main())
