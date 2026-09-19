#!/usr/bin/env python3
"""Build the consistent report bundle and the deliberate-mismatch examples (UIOWA-117).

SYNTHETIC - NOT A UNIVERSITY FINDING. Every identifier, status and figure below
is fiction. The finding and recommendation IDs deliberately match the synthetic
corpus in `revenue/uiowa_rfq_18649_report_structure/` so the two lanes tell one
coherent fictional story; both are labeled fiction and neither describes the
University of Iowa.

Why the mismatch examples are generated, not hand-written
---------------------------------------------------------
The work order completes when "actual regenerated examples agree after
correction". A hand-written broken file can demonstrate that a checker fires. It
cannot demonstrate that the bundle was consistent before the defect, or that it
returns to consistent after correction - the two facts that make the checker
worth trusting.

So there is exactly one consistent bundle, and each defect is an injection into a
copy of it. Every mismatch example is one edit away from a known-good state, and
the tests assert the round trip.
"""

from __future__ import annotations

import argparse
import copy
import os
from typing import Callable

from output_agreement import Bundle, save_bundle


def consistent_bundle() -> Bundle:
    """One internally consistent delivery: matrix, register, summary, deck."""
    matrix = [
        dict(finding_id="FND-SYN-ESS-SD-001", group="ESS", area="SD", status="SUPPORTED",
             confidence="MODERATE",
             statement="Merges to the two sampled ESS repositories require a passing check and an approving review."),
        dict(finding_id="FND-SYN-ESS-SEC-001", group="ESS", area="SEC", status="PARTIAL",
             confidence="LOW",
             statement="A dependency-scanning step runs; no record of how findings are triaged was observed."),
        dict(finding_id="FND-SYN-ESS-DEP-001", group="ESS", area="DEP", status="SUPPORTED",
             confidence="MODERATE",
             statement="Production deployments in the sampled window carry a change reference and an approver."),
        dict(finding_id="FND-SYN-ESS-AI-001", group="ESS", area="AI", status="PARTIAL",
             confidence="LOW",
             statement="Assisted coding tools are in informal use; no group-level review guidance was observed."),
        dict(finding_id="FND-SYN-RIS-SD-001", group="RIS", area="SD", status="PARTIAL",
             confidence="LOW",
             statement="A documented intake-to-release path exists; the one traced change reviewed after deployment."),
        dict(finding_id="FND-SYN-RIS-SEC-001", group="RIS", area="SEC", status="PARTIAL",
             confidence="LOW",
             statement="A standard requires annual privileged-access review; no completed record was observed."),
        dict(finding_id="FND-SYN-RIS-DEP-001", group="RIS", area="DEP", status="SUPPORTED",
             confidence="MODERATE",
             statement="Scheduled maintenance is announced in advance and tracked to a close-out note."),
        dict(finding_id="FND-SYN-IAM-SD-001", group="IAM", area="SD", status="SUPPORTED",
             confidence="MODERATE",
             statement="Connector changes are developed in version control with peer review recorded."),
        dict(finding_id="FND-SYN-IAM-SEC-001", group="IAM", area="SEC", status="SUPPORTED",
             confidence="HIGH",
             statement="All 14 accounts in the enumerated privileged population had a second factor at capture time."),
        dict(finding_id="FND-SYN-IAM-DEP-001", group="IAM", area="DEP", status="CONFLICT",
             confidence="UNRESOLVED",
             statement="Interviews and the change export disagree on emergency-change records; 3 of 14 lack one."),
        dict(finding_id="FND-SYN-IAM-AI-001", group="IAM", area="AI", status="UNKNOWN",
             confidence="NOT_EVIDENCED",
             statement="Not assessed. No evidence was supplied for AI readiness in IAM."),
    ]

    register = [
        dict(recommendation_id="REC-SYN-ESS-SD-001", group="ESS", area="SD",
             finding_refs="FND-SYN-ESS-SD-001", horizon="0-90",
             statement="Produce an authoritative inventory of in-scope ESS repositories and their settings.",
             resource_note="One analyst, estimated under a week."),
        dict(recommendation_id="REC-SYN-IAM-DEP-001", group="IAM", area="DEP",
             finding_refs="FND-SYN-IAM-DEP-001", horizon="0-90",
             statement="Identify the system of record for emergency identity changes; investigate before changing anything.",
             resource_note="Half a day of IAM operations time."),
        dict(recommendation_id="REC-SYN-CROSS-SEC-001", group="CROSS", area="SEC",
             finding_refs="FND-SYN-RIS-SEC-001;FND-SYN-IAM-SEC-001", horizon="0-90",
             statement="Record which enumerated population each access-review requirement applies to.",
             resource_note="Estimated two days across the security and identity groups."),
        dict(recommendation_id="REC-SYN-RIS-SEC-001", group="RIS", area="SEC",
             finding_refs="FND-SYN-RIS-SEC-001", horizon="90-180",
             statement="Establish where completed privileged-access reviews are retained for research systems.",
             resource_note="UNKNOWN - depends on whether a system of record already exists."),
        dict(recommendation_id="REC-SYN-ESS-AI-001", group="ESS", area="AI",
             finding_refs="FND-SYN-ESS-AI-001", horizon="90-180",
             statement="Decide and write down how generated code is reviewed before it reaches a production branch.",
             resource_note="Guidance drafting only."),
        dict(recommendation_id="REC-SYN-IAM-AI-001", group="IAM", area="AI",
             finding_refs="FND-SYN-IAM-AI-001", horizon="UNKNOWN",
             statement="Hold the AI-readiness session the engagement window did not accommodate.",
             resource_note="UNKNOWN - cannot be estimated before the cell is assessed."),
    ]

    summary = {
        "artifact": "executive_summary",
        "status": "SYNTHETIC - NOT A UNIVERSITY FINDING",
        "claims": [
            {"claim_id": "ES-01",
             "text": "Ten of the twelve group-by-area cells were assessed within the engagement window.",
             "asserted_count": {"of": "assessed_cells", "value": 10}},
            {"claim_id": "ES-02",
             "text": "Five cells are partial or carry conflicting evidence and are the focus of this report.",
             "asserted_count": {"of": "priority_findings", "value": 5}},
            {"claim_id": "ES-03",
             "text": "Privileged access to the identity platform is the strongest evidenced control in the engagement.",
             "cites": ["FND-SYN-IAM-SEC-001"],
             "asserted_state": {"finding_id": "FND-SYN-IAM-SEC-001", "status": "SUPPORTED"}},
            {"claim_id": "ES-04",
             "text": "The repository inventory is proposed for the first 90 days.",
             "cites": ["REC-SYN-ESS-SD-001"],
             "asserted_horizon": {"recommendation_id": "REC-SYN-ESS-SD-001", "horizon": "0-90"}},
            {"claim_id": "ES-05",
             "text": "Two conditions - an unresolved change-record conflict and an access review with no retained record - account for most of the proposed near-term work.",
             "cites": ["FND-SYN-IAM-DEP-001", "FND-SYN-RIS-SEC-001"]},
            {"claim_id": "ES-06",
             "text": "The IAM AI-readiness session cannot be estimated until the cell is assessed.",
             "cites": ["REC-SYN-IAM-AI-001"],
             "asserted_estimate": {"recommendation_id": "REC-SYN-IAM-AI-001",
                                   "estimate": "UNKNOWN - cannot be estimated before the cell is assessed."}},
        ],
    }

    presentation = {
        "artifact": "presentation_source",
        "status": "SYNTHETIC - NOT A UNIVERSITY FINDING",
        "claims": [
            {"claim_id": "PS-01", "slide_id": "S2",
             "text": "Three recommendations are proposed for the first 90 days.",
             "asserted_count": {"of": "near_term_recommendations", "value": 3}},
            {"claim_id": "PS-02", "slide_id": "S3",
             "text": "Research-systems access review is documented but not yet demonstrated.",
             "cites": ["FND-SYN-RIS-SEC-001"],
             "asserted_state": {"finding_id": "FND-SYN-RIS-SEC-001", "status": "PARTIAL"}},
            {"claim_id": "PS-03", "slide_id": "S4",
             "text": "Establishing where completed reviews are retained sits in the 90-180 day window.",
             "cites": ["REC-SYN-RIS-SEC-001"],
             "asserted_horizon": {"recommendation_id": "REC-SYN-RIS-SEC-001", "horizon": "90-180"}},
            {"claim_id": "PS-04", "slide_id": "S5",
             "text": "The repository inventory is a short analyst task.",
             "cites": ["REC-SYN-ESS-SD-001"],
             "asserted_estimate": {"recommendation_id": "REC-SYN-ESS-SD-001",
                                   "estimate": "One analyst, estimated under a week."}},
            {"claim_id": "PS-05", "slide_id": "S6",
             "text": "AI readiness in IAM was not assessed and is carried as an open question.",
             "cites": ["FND-SYN-IAM-AI-001"],
             "asserted_state": {"finding_id": "FND-SYN-IAM-AI-001", "status": "UNKNOWN"}},
        ],
    }

    return Bundle(matrix=matrix, register=register, summary=summary, presentation=presentation)


# ---------------------------------------------------------------------------
# Defect injectors. Each returns a copy of the consistent bundle with exactly
# one defect, and declares the diagnostic code it must produce.
# ---------------------------------------------------------------------------

def _claim(b: Bundle, artifact_doc: dict, claim_id: str) -> dict:
    for c in artifact_doc["claims"]:
        if c["claim_id"] == claim_id:
            return c
    raise KeyError(claim_id)


def _count_mismatch(b: Bundle) -> Bundle:
    """The classic: prose says three, the matrix holds five."""
    _claim(b, b.summary, "ES-02")["asserted_count"]["value"] = 3
    _claim(b, b.summary, "ES-02")["text"] = (
        "Three cells are partial or carry conflicting evidence and are the focus of this report.")
    return b


def _dangling_id(b: Bundle) -> Bundle:
    _claim(b, b.summary, "ES-05")["cites"].append("FND-SYN-ESS-XX-999")
    return b


def _state_mismatch(b: Bundle) -> Bundle:
    """The deck upgrades a partial finding to supported."""
    _claim(b, b.presentation, "PS-02")["asserted_state"]["status"] = "SUPPORTED"
    return b


def _unassessed_result_claimed(b: Bundle) -> Bundle:
    """The deck states a result for a cell nobody assessed."""
    c = _claim(b, b.presentation, "PS-05")
    c["asserted_state"]["status"] = "SUPPORTED"
    c["text"] = "AI readiness in IAM is in good shape."
    return b


def _phase_mismatch(b: Bundle) -> Bundle:
    _claim(b, b.presentation, "PS-03")["asserted_horizon"]["horizon"] = "0-90"
    return b


def _phase_fabricated(b: Bundle) -> Bundle:
    """An unsequenced recommendation acquires a phase on a slide."""
    b.presentation["claims"].append({
        "claim_id": "PS-07", "slide_id": "S8",
        "text": "The IAM AI-readiness session is scheduled in the first 90 days.",
        "cites": ["REC-SYN-IAM-AI-001"],
        "asserted_horizon": {"recommendation_id": "REC-SYN-IAM-AI-001", "horizon": "0-90"}})
    return b


def _estimate_fabricated(b: Bundle) -> Bundle:
    """The one that matters most: UNKNOWN becomes a number."""
    c = _claim(b, b.summary, "ES-06")
    c["asserted_estimate"]["estimate"] = "About three days."
    c["text"] = "The IAM AI-readiness session is about three days of work."
    return b


def _estimate_mismatch(b: Bundle) -> Bundle:
    _claim(b, b.presentation, "PS-04")["asserted_estimate"]["estimate"] = "Two analysts, three weeks."
    return b


def _duplicate_id(b: Bundle) -> Bundle:
    b.matrix.append(copy.deepcopy(b.matrix[0]))
    return b


def _unknown_count_set(b: Bundle) -> Bundle:
    _claim(b, b.summary, "ES-01")["asserted_count"]["of"] = "cells_we_liked"
    return b


# name -> (expected diagnostic code, regeneration clears THAT code, injector)
#
# The second flag is a real contract, not bookkeeping. Regeneration recomputes
# derived views from source, so it clears a stale count, state, phase or
# estimate. It cannot clear a defect that has no source to recompute from: a
# citation to an ID nobody defined, a duplicated row, or a count over a set the
# checker has no definition for. Those are content defects and a human has to
# fix them. A checker that claimed to "correct" them would be hiding them.
DEFECTS: dict[str, tuple[str, bool, Callable[[Bundle], Bundle]]] = {
    "count_mismatch": ("COUNT_MISMATCH", True, _count_mismatch),
    "dangling_id": ("DANGLING_ID", False, _dangling_id),
    "state_mismatch": ("STATE_MISMATCH", True, _state_mismatch),
    "unassessed_result_claimed": ("UNASSESSED_RESULT_CLAIMED", True, _unassessed_result_claimed),
    "phase_mismatch": ("PHASE_MISMATCH", True, _phase_mismatch),
    "phase_fabricated": ("PHASE_FABRICATED", True, _phase_fabricated),
    "estimate_fabricated": ("ESTIMATE_FABRICATED", True, _estimate_fabricated),
    "estimate_mismatch": ("ESTIMATE_MISMATCH", True, _estimate_mismatch),
    "duplicate_id": ("DUPLICATE_ID", False, _duplicate_id),
    "unknown_count_set": ("UNKNOWN_COUNT_SET", False, _unknown_count_set),
}


# Legitimate cascades: a defect that genuinely breaks more than one thing.
#
# Duplicating a matrix row is the only one. It is not checker noise - the extra
# row really does change every count taken over the matrix, so the executive
# summary's "ten assessed cells" really is wrong now. Both diagnostics are true
# and both should be reported. This is declared here rather than being absorbed
# by a looser test, so that any *new* cascade shows up as a test failure and has
# to be justified the same way.
EXPECTED_CASCADE: dict[str, set[str]] = {
    "duplicate_id": {"COUNT_MISMATCH"},
}


def build_defect(name: str) -> Bundle:
    if name not in DEFECTS:
        raise KeyError(f"unknown defect '{name}'; known: {', '.join(sorted(DEFECTS))}")
    _, _, fn = DEFECTS[name]
    return fn(consistent_bundle())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Write the consistent bundle and every mismatch example.")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "fixtures"))
    a = ap.parse_args(argv)

    good = os.path.join(a.out, "consistent")
    save_bundle(consistent_bundle(), good)
    print(f"wrote {good}")
    for name in sorted(DEFECTS):
        d = os.path.join(a.out, "mismatched", name)
        save_bundle(build_defect(name), d)
        print(f"wrote {d}  (expects {DEFECTS[name][0]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
