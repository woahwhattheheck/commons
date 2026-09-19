"""Precise uncertainty language for assessment answers.

This module is the heart of the kit. Everything else routes questions; this
decides what an answer is *allowed to say*.

The distinction this exists to enforce
-------------------------------------
    "We found no evidence of X."      <- a statement about OUR SEARCH
    "X does not happen."              <- a claim about the UNIVERSITY

The first is supportable from an assessment. The second never is. An assessment
looks at the material it was given, in the time it had, through the people who
answered. Absence in that material is evidence about the material. Turning it
into a fact about the organisation is the single most common way an honest
assessment becomes a dishonest one, and it happens in the *wording*, long after
the analysis was correct.

So absence is not one state here. It is three, and they are not
interchangeable:

    OBSERVED_PRESENT        we looked, we found it
    ABSENT_IN_SEARCHED      we looked in a NAMED scope, we did not find it
    NOT_ASSESSED           we did not look

Collapsing NOT_ASSESSED into ABSENT_IN_SEARCHED is the second most common
failure: "no evidence of disaster-recovery testing" reads identically whether
we reviewed every runbook and found none, or never asked. The kit refuses to
let those share a sentence shape. ABSENT_IN_SEARCHED *must* name what was
searched; NOT_ASSESSED is forbidden from claiming a search happened.

CONTESTED is kept separate again, because evidence that disagrees with itself
is not a weak version of either side -- flattening it to the majority view
destroys the most useful thing in the packet.

Enforcement is two-sided on purpose. A structural check (does the record carry
the fields its claim type requires) catches the author who forgot. A phrasing
check (does the prose actually read as that claim type) catches the author who
filled the fields in correctly and then wrote the sentence anyway. Only the
second one catches the failure that actually ships, because the structured
fields are not what gets read aloud in the room -- the sentence is.
"""

import re

# ---------------------------------------------------------------------------
# Claim types
# ---------------------------------------------------------------------------

OBSERVED_PRESENT = "OBSERVED_PRESENT"
ABSENT_IN_SEARCHED = "ABSENT_IN_SEARCHED"
NOT_ASSESSED = "NOT_ASSESSED"
CONTESTED = "CONTESTED"

CLAIM_TYPES = (OBSERVED_PRESENT, ABSENT_IN_SEARCHED, NOT_ASSESSED, CONTESTED)

CLAIM_TYPE_MEANING = {
    OBSERVED_PRESENT: (
        "We looked and we found it. Cites the evidence that shows it."
    ),
    ABSENT_IN_SEARCHED: (
        "We looked in a named scope and did not find it. A statement about "
        "the material reviewed, NOT about whether the practice exists."
    ),
    NOT_ASSESSED: (
        "We did not look. No search was performed, so nothing at all is "
        "established in either direction."
    ),
    CONTESTED: (
        "Evidence disagrees with itself. Both sides are retained; neither "
        "is presented as the finding."
    ),
}

# ---------------------------------------------------------------------------
# Phrasing rules
# ---------------------------------------------------------------------------

# Constructions that assert something about the WORLD rather than about our
# search. Banned in an ABSENT_IN_SEARCHED or NOT_ASSESSED claim. These are the
# phrasings an assessor reaches for without noticing the promotion.
_REALITY_CLAIM_PATTERNS = [
    (r"\bdoes not (?:exist|happen|occur|take place)\b", "does not exist/happen"),
    (r"\bdo not (?:exist|happen|occur|take place)\b", "do not exist/happen"),
    (r"\bnever (?:happens|occurs|test|tested|run|do|does)\b", "never ..."),
    (r"\bthere (?:is|are) no\b", "there is/are no ..."),
    (r"\bthey (?:do not|don't|never)\b", "they do not ..."),
    (r"\bis not (?:done|performed|practised|practiced|carried out)\b",
     "is not done/performed"),
    (r"\bare not (?:done|performed|practised|practiced|carried out)\b",
     "are not done/performed"),
    (r"\bhas no\b", "has no ..."),
    (r"\bhave no\b", "have no ..."),
    (r"\blacks?\b", "lacks ..."),
    (r"\bno (?:such )?(?:process|procedure|practice|testing|review|backup)\b",
     "no <thing> (as a bare fact)"),
]

# A scope qualifier is what turns an absence sentence back into a statement
# about the search. At least one must appear in an ABSENT_IN_SEARCHED claim.
_SCOPE_QUALIFIERS = [
    r"\bwe found no (?:evidence|record|records|trace|mention|documentation)\b",
    r"\bno (?:evidence|record|records) (?:was|were) (?:supplied|provided|found|identified)\b",
    r"\bin the (?:material|materials|documents|evidence|records) (?:supplied|provided|reviewed|examined)\b",
    r"\bin the (?:supplied|provided|reviewed) (?:material|materials|documents|evidence|records)\b",
    r"\bwithin the scope of this assessment\b",
    r"\bnone of the (?:material|materials|documents|evidence|records) (?:supplied|provided|reviewed|examined)\b",
    r"\bthe (?:material|materials|documents|evidence|records) (?:we )?reviewed (?:do|does|did) not\b",
]

# NOT_ASSESSED must not imply a search happened. "We found no evidence"
# asserts a search; if we never looked, that sentence is false.
_IMPLIES_SEARCH_PATTERNS = [
    (r"\bwe found no\b", "we found no ... (implies a search occurred)"),
    (r"\bno evidence was found\b", "no evidence was found (implies a search)"),
    (r"\bwe did not find\b", "we did not find (implies a search)"),
    (r"\bnone (?:was|were) found\b", "none was found (implies a search)"),
    (r"\bour review found\b", "our review found (implies a search)"),
]

# NOT_ASSESSED should positively say so.
_NOT_ASSESSED_MARKERS = [
    r"\bnot assessed\b",
    r"\bwas not (?:examined|reviewed|in scope|within scope|covered)\b",
    r"\bwere not (?:examined|reviewed|in scope|within scope|covered)\b",
    r"\bno (?:review|assessment|examination) (?:of this|was) \b",
    r"\bout of scope\b",
    r"\bwe did not (?:look|examine|review|assess)\b",
]

# Totalising words that overclaim a positive finding unless the cited evidence
# is explicitly complete-coverage.
_UNIVERSAL_PATTERNS = [
    (r"\balways\b", "always"),
    (r"\bevery\b", "every"),
    (r"\ball (?:teams|services|groups|changes|deployments)\b", "all <things>"),
    (r"\bfully\b", "fully"),
    (r"\bconsistently across\b", "consistently across"),
    (r"\bnever fails?\b", "never fails"),
]

# Wording that turns an assessment into a verdict it has no standing to issue.
_VERDICT_PATTERNS = [
    (r"\bcompliant\b", "compliant"),
    (r"\bnon-?compliant\b", "non-compliant"),
    (r"\bcertif(?:y|ied|ication)\b", "certify/certified"),
    (r"\bpasses? (?:the )?audit\b", "passes audit"),
    (r"\bmeets? (?:all )?requirements\b", "meets requirements"),
    (r"\bpercentile\b", "percentile"),
    (r"\branked? (?:against|versus|vs)\b", "ranked against"),
    (r"\bbest[- ]in[- ]class\b", "best-in-class"),
    (r"\bworst\b", "worst"),
    (r"\bbetter than (?:peer|other institution)", "better than peers"),
]


class LanguageViolation:
    """One specific thing wrong with how an answer is worded."""

    def __init__(self, code, detail, offending):
        self.code = code
        self.detail = detail
        self.offending = offending

    def __repr__(self):  # pragma: no cover - debugging aid
        return "LanguageViolation(%s, %r)" % (self.code, self.offending)

    def as_dict(self):
        return {"code": self.code, "detail": self.detail,
                "offending": self.offending}

    def __str__(self):
        return "%s: %s [%s]" % (self.code, self.detail, self.offending)


def _find(patterns, text):
    hits = []
    low = text.lower()
    for pattern, label in patterns:
        if re.search(pattern, low):
            hits.append(label)
    return hits


def _any(patterns, text):
    low = text.lower()
    return any(re.search(p, low) for p in patterns)


def check_claim_language(claim_type, text, search_scope=None,
                         evidence_coverage="partial"):
    """Return a list of LanguageViolation for one claim.

    ``search_scope`` is what was actually looked at -- required, and required
    to be non-empty, for ABSENT_IN_SEARCHED. ``evidence_coverage`` is
    ``complete`` only when the cited evidence genuinely covers the whole
    population being spoken about; anything else forbids totalising language.
    """
    violations = []

    if claim_type not in CLAIM_TYPES:
        violations.append(LanguageViolation(
            "UNKNOWN_CLAIM_TYPE",
            "claim_type must be one of %s" % (", ".join(CLAIM_TYPES),),
            str(claim_type)))
        return violations

    if claim_type == ABSENT_IN_SEARCHED:
        # Structural: an absence claim without a named scope is not an
        # absence claim, it is an assertion.
        if not search_scope or not str(search_scope).strip():
            violations.append(LanguageViolation(
                "ABSENCE_WITHOUT_SCOPE",
                "ABSENT_IN_SEARCHED requires search_scope naming what was "
                "actually examined; without it the claim is about the "
                "University rather than about the search",
                "<search_scope empty>"))
        # Phrasing: the sentence must be about the search.
        if not _any(_SCOPE_QUALIFIERS, text):
            violations.append(LanguageViolation(
                "ABSENCE_NOT_QUALIFIED",
                "an absence statement must say it is about the material "
                "reviewed (e.g. 'we found no evidence of X in the runbooks "
                "supplied'), not assert X's non-existence",
                text.strip()[:160]))
        for label in _find(_REALITY_CLAIM_PATTERNS, text):
            violations.append(LanguageViolation(
                "ABSENCE_STATED_AS_FACT",
                "'%s' states absence as a fact about the University; an "
                "assessment can only report absence from what it searched"
                % label,
                label))

    if claim_type == NOT_ASSESSED:
        for label in _find(_IMPLIES_SEARCH_PATTERNS, text):
            violations.append(LanguageViolation(
                "NOT_ASSESSED_IMPLIES_SEARCH",
                "'%s' claims a search that did not happen; NOT_ASSESSED "
                "means we did not look, which is not the same as looking "
                "and finding nothing" % label,
                label))
        for label in _find(_REALITY_CLAIM_PATTERNS, text):
            violations.append(LanguageViolation(
                "ABSENCE_STATED_AS_FACT",
                "'%s' asserts absence, but nothing was assessed here so "
                "nothing is established in either direction" % label,
                label))
        if not _any(_NOT_ASSESSED_MARKERS, text):
            violations.append(LanguageViolation(
                "NOT_ASSESSED_NOT_DECLARED",
                "a NOT_ASSESSED answer must say plainly that it was not "
                "assessed, or a reader will hear it as a negative finding",
                text.strip()[:160]))

    if claim_type == OBSERVED_PRESENT and evidence_coverage != "complete":
        for label in _find(_UNIVERSAL_PATTERNS, text):
            violations.append(LanguageViolation(
                "OVERCLAIMED_COVERAGE",
                "'%s' generalises beyond the cited evidence, whose coverage "
                "is '%s'; say what was observed, in what sample"
                % (label, evidence_coverage),
                label))

    if claim_type == CONTESTED:
        # A contested claim that reads as settled has destroyed the finding.
        if not re.search(r"\b(?:disagree|conflict|contradict|both|differ|"
                         r"inconsisten|one .* another|not reconciled)",
                         text.lower()):
            violations.append(LanguageViolation(
                "CONTESTED_READS_AS_SETTLED",
                "a CONTESTED answer must show the disagreement; presenting "
                "one side as the finding discards the most useful thing in "
                "the packet",
                text.strip()[:160]))

    # Verdict language is forbidden in every claim type. An assessment is not
    # an audit and has no peer dataset.
    for label in _find(_VERDICT_PATTERNS, text):
        violations.append(LanguageViolation(
            "VERDICT_OR_RANKING_LANGUAGE",
            "'%s' is a verdict or comparison this instrument cannot issue; "
            "state what was observed and what a verdict would require"
            % label,
            label))

    return violations


def describe_claim_types():
    """Plain-language reference, used by the CLI and the README."""
    lines = []
    for name in CLAIM_TYPES:
        lines.append("%-20s %s" % (name, CLAIM_TYPE_MEANING[name]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scope boundaries
# ---------------------------------------------------------------------------
#
# A hostile question ("where do we rank against peers?") is not a claim about
# the University, so it does not go through check_claim_language. It goes
# through here.
#
# The failure mode being guarded against is NOT that the tool answers -- it is
# that the tool *deflects*. "That's outside the scope of this engagement" is a
# non-answer that wastes the question. The person asking has a real
# information need behind it, and usually some of it IS answerable.
#
# So a boundary response is only valid when it carries all three parts:
#   cannot       what this instrument cannot produce, said plainly
#   requires     what would actually be needed to produce it
#   can_instead  at least one real claim, with real evidence, addressing the
#                need behind the question
#
# The third part is what separates an answer from a dodge, and it is checked
# structurally: an OUT_OF_SCOPE answer with zero supported claims is rejected
# by the resolver as a deflection.

_CANNOT_MARKERS = [
    r"\bcannot\b", r"\bcan(?:'|’)t\b", r"\bis not able\b",
    r"\bdoes not (?:produce|support|provide)\b", r"\bno basis\b",
    r"\bnot something this\b", r"\bout of scope\b", r"\bnot within\b",
]

_REQUIRES_MARKERS = [
    r"\bwould require\b", r"\brequires\b", r"\bwould need\b",
    r"\bto (?:produce|answer|support) (?:that|this|it)\b",
    r"\bonly an? .* could\b",
]


def check_boundary_language(cannot, requires, can_instead_count):
    """Validate a scope-boundary response.

    Deflection is the failure being caught here, not over-answering.
    """
    violations = []

    if not cannot or not _any(_CANNOT_MARKERS, cannot):
        violations.append(LanguageViolation(
            "BOUNDARY_NOT_STATED",
            "a boundary response must say plainly what this assessment "
            "cannot produce; vagueness here reads as evasion",
            (cannot or "")[:160]))

    if not requires or not _any(_REQUIRES_MARKERS, requires):
        violations.append(LanguageViolation(
            "BOUNDARY_WITHOUT_REQUIREMENT",
            "saying 'we cannot' without saying what would be required is a "
            "dodge; name the dataset, instrument or authority that would "
            "actually answer the question",
            (requires or "")[:160]))

    if can_instead_count <= 0:
        violations.append(LanguageViolation(
            "BOUNDARY_WITHOUT_SUBSTANCE",
            "a boundary response with no supported claims is a deflection; "
            "answer the information need behind the question with whatever "
            "the evidence does support",
            "can_instead=0"))

    return violations
