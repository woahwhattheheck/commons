"""The language rules, stated as data so they can be argued with.

WHY THIS IS TIERED AND NOT A WORD LIST.

A flat list of banned words is the reason nobody runs this kind of checker
twice. It fires on "comprehensive test coverage" and "a robust retry policy",
the author concludes the tool is stupid, and it gets switched off -- taking the
rules that were actually catching something with it.

So a term's severity depends on what else is in the sentence:

  TIER_A  always a defect. There is no context in which "world-class" is a
          finding. These words carry no information about the assessed subject;
          they carry information about how the author wants it perceived.

  TIER_B  a defect only when the sentence carries NO NUMBER. "Significantly
          faster" is a vibe. "Significantly faster -- 41.8 minutes per document"
          is a measurement with an adverb in front of it, and that is fine.

  TIER_C  a defect when the sentence has neither a number NOR a citation.
          "Ensures", "guarantees", "proven" are claims about reliability, and
          a reliability claim needs either evidence or a source.

Every term below is here because it either states a conclusion the evidence has
to earn, or substitutes a feeling for a figure.
"""
from __future__ import annotations

ERROR = "error"
WARN = "warning"

# Always a defect in a client-facing assessment deliverable.
TIER_A = {
    "world-class": "states a peer comparison this engagement did not make",
    "world class": "states a peer comparison this engagement did not make",
    "best-in-class": "states a peer comparison this engagement did not make",
    "best in class": "states a peer comparison this engagement did not make",
    "industry-leading": "states a peer comparison this engagement did not make",
    "industry leading": "states a peer comparison this engagement did not make",
    "gold standard": "states a peer comparison this engagement did not make",
    "cutting-edge": "characterises rather than reports",
    "cutting edge": "characterises rather than reports",
    "state-of-the-art": "characterises rather than reports",
    "state of the art": "characterises rather than reports",
    "game-changing": "characterises rather than reports",
    "revolutionary": "characterises rather than reports",
    "unparalleled": "states a comparison with no comparator",
    "seamless": "asserts an absence of friction that was not measured",
    "seamlessly": "asserts an absence of friction that was not measured",
    "effortless": "asserts an absence of effort that was not measured",
    "turnkey": "asserts an absence of integration work that was not measured",
    "best practice": "appeals to an unnamed external authority",
    "best practices": "appeals to an unnamed external authority",
    "industry best practice": "appeals to an unnamed external authority",
    "synergy": "names no mechanism and no measurement",
    "synergies": "names no mechanism and no measurement",
}

# A defect only when the sentence carries no figure.
TIER_B = {
    "dramatically": "intensifier with no magnitude",
    "drastically": "intensifier with no magnitude",
    "vastly": "intensifier with no magnitude",
    "greatly": "intensifier with no magnitude",
    "significantly": "intensifier with no magnitude",
    "substantially": "intensifier with no magnitude",
    "considerably": "intensifier with no magnitude",
    "markedly": "intensifier with no magnitude",
    "remarkable": "evaluative adjective with no magnitude",
    "remarkably": "evaluative adjective with no magnitude",
    "exceptional": "evaluative adjective with no magnitude",
    "outstanding": "evaluative adjective with no magnitude",
    "excellent": "evaluative adjective with no magnitude",
    "robust": "evaluative adjective with no magnitude",
    "powerful": "evaluative adjective with no magnitude",
    "comprehensive": "asserts completeness without stating coverage",
    "extensive": "asserts breadth without stating coverage",
    "mature": "asserts a maturity level without stating what measured it",
    "highly": "intensifier with no magnitude",
}

# A defect when the sentence has neither a figure nor a citation.
TIER_C = {
    "ensures": "asserts a guarantee; needs evidence or a source",
    "ensure": "asserts a guarantee; needs evidence or a source",
    "guarantees": "asserts a guarantee; needs evidence or a source",
    "guarantee": "asserts a guarantee; needs evidence or a source",
    "guaranteed": "asserts a guarantee; needs evidence or a source",
    "proven": "asserts prior proof without naming it",
    "eliminates": "asserts a total effect; needs evidence or a source",
    "maximises": "asserts an optimum that was not computed",
    "maximizes": "asserts an optimum that was not computed",
    "minimises": "asserts an optimum that was not computed",
    "minimizes": "asserts an optimum that was not computed",
    "optimises": "asserts an optimum that was not computed",
    "optimizes": "asserts an optimum that was not computed",
}

# Comparatives are claims about a delta. A delta with no number is an opinion.
COMPARATIVES = (
    "faster", "slower", "quicker", "better", "worse", "cheaper", "costlier",
    "stronger", "weaker", "higher", "lower", "more efficient", "less efficient",
    "more effective", "less effective", "improved", "improves", "reduced",
    "reduces", "increased", "increases", "streamlined", "accelerated",
)

# Absolutes need a source; they are the easiest statement to disprove and the
# most expensive one to have to walk back in front of a client.
ABSOLUTES = ("always", "never", "all ", "every ", "none of", "no services",
             "without exception", "entirely", "completely", "fully")

# Finding states that cannot support an asserted figure.
UNSUPPORTING_STATES = ("UNKNOWN", "NOT_ASSESSED")
CONTRADICTING_STATES = ("CONTRADICTED",)

# Words that make a sentence read as support rather than as a caveat. Used only
# to decide whether citing a CONTRADICTED finding is being done honestly.
SUPPORT_FRAMING = (
    "demonstrates", "demonstrate", "shows", "confirms", "confirm", "establishes",
    "evidences", "supports", "validated", "validates", "strength", "strong",
)
