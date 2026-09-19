"""How strongly a finding may be stated, derived from what actually backs it.

Work order UIOWA-081. The requirement is that every statement in the leadership
summary is traceable to a finding. Traceability alone is not enough: a citation can
point at a finding that does not support the weight the sentence puts on it. An
executive summary fails in two directions, and only one of them is about missing
citations.

  * unsourced   -- the sentence cites nothing. Easy to catch.
  * overclaimed -- the sentence cites a real finding and then says more than that
                   finding can carry. This is the one that survives review, because
                   the citation is right there and looks like diligence.

So this module computes a MAXIMUM ASSERTABLE STRENGTH per finding from its basis,
its corroboration, and its stated confidence. summary.py then refuses any sentence
whose phrasing claims more than that.

The rule that keeps it honest: UNKNOWN confidence and NOT_ESTABLISHED basis both
collapse to NOT_ESTABLISHED. An unresolved finding cannot be asserted at all. It can
only be NAMED as an open question. Absent evidence never becomes a reassurance.
"""

# ---------------------------------------------------------------- vocabularies

BASIS = {
    "DIRECT_OBSERVATION": 4,
    "DOCUMENT_REVIEW": 3,
    "INTERVIEW_CORROBORATED": 3,
    "INTERVIEW_SINGLE_SOURCE": 2,
    "SELF_REPORTED": 1,
    "NOT_ESTABLISHED": 0,
}

CONFIDENCE = {
    "HIGH": 3,
    "MODERATE": 2,
    "LOW": 1,
    "UNKNOWN": 0,
}

# Ordered weakest -> strongest. A sentence may assert AT MOST its findings' level.
STRENGTH_ORDER = ("NOT_ESTABLISHED", "SINGLE_SOURCE", "INDICATED", "SETTLED")
STRENGTH_RANK = {name: index for index, name in enumerate(STRENGTH_ORDER)}

STRENGTH_MEANING = {
    "SETTLED": "May be stated as fact, unhedged.",
    "INDICATED": "Must be hedged and scoped: 'evidence indicates', 'in the teams "
                 "reviewed'.",
    "SINGLE_SOURCE": "Must be attributed to its source: 'one team reported'. Never "
                     "generalized.",
    "NOT_ESTABLISHED": "May NOT be asserted at all. May only be named as an open "
                       "question in the unresolved section.",
}

REMEDY = {
    "INDICATED": "rephrase with a hedge and an explicit scope, e.g. 'evidence from "
                 "the units reviewed indicates ...'",
    "SINGLE_SOURCE": "rephrase with attribution, e.g. 'one unit reported ...', and "
                     "do not generalize beyond that source",
    "NOT_ESTABLISHED": "remove the assertion; move the subject to the open-questions "
                       "section as an UNKNOWN",
}


class EvidenceError(ValueError):
    """Raised when a finding's evidence declaration is not usable as declared."""


def max_assertable_strength(basis, confidence, corroborating_sources, evidence_count):
    """How strongly may a finding with this backing be stated?

    Deliberately conservative and deliberately simple: a reviewer must be able to
    re-derive any verdict by hand from the four inputs, otherwise the tool becomes
    the authority instead of the evidence.
    """
    if basis not in BASIS:
        raise EvidenceError(f"unknown basis {basis!r}; expected one of {sorted(BASIS)}")
    if confidence not in CONFIDENCE:
        raise EvidenceError(
            f"unknown confidence {confidence!r}; expected one of {sorted(CONFIDENCE)}. "
            f"A missing confidence must be recorded as 'UNKNOWN', not omitted.")
    if not isinstance(corroborating_sources, int) or corroborating_sources < 0:
        raise EvidenceError("corroborating_sources must be a non-negative integer")
    if not isinstance(evidence_count, int) or evidence_count < 0:
        raise EvidenceError("evidence_count must be a non-negative integer")

    # Two hard floors, applied before anything else can lift the result.
    if basis == "NOT_ESTABLISHED" or confidence == "UNKNOWN":
        return "NOT_ESTABLISHED"
    if evidence_count == 0:
        # A finding with a basis and a confidence but no attached evidence item is
        # an assertion, not a finding.
        return "NOT_ESTABLISHED"

    if basis == "SELF_REPORTED":
        return "SINGLE_SOURCE" if corroborating_sources >= 1 else "NOT_ESTABLISHED"
    if basis == "INTERVIEW_SINGLE_SOURCE" or corroborating_sources < 2:
        return "SINGLE_SOURCE"

    # Corroborated from here on. Confidence decides between hedged and settled.
    if CONFIDENCE[confidence] >= 3 and BASIS[basis] >= 3 and corroborating_sources >= 2:
        return "SETTLED"
    return "INDICATED"


def at_most(strength_a, strength_b):
    """The weaker of two strengths. A statement citing several findings is capped by
    its weakest citation -- a strong finding does not launder a weak one."""
    return STRENGTH_ORDER[min(STRENGTH_RANK[strength_a], STRENGTH_RANK[strength_b])]


def is_stronger(claimed, supported):
    return STRENGTH_RANK[claimed] > STRENGTH_RANK[supported]
