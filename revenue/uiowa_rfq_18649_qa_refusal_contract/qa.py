"""The resolver: a question in, an answer or an explicit refusal out.

Resolution order, and why it is this order
------------------------------------------
1. TRIGGER BOUNDARY Questions this instrument structurally cannot answer -- a
                    peer percentile, a team ranking, a compliance verdict.
                    These run first because they would otherwise route to
                    whatever evidence happens to share vocabulary with them,
                    and produce a confident answer to a question that has no
                    answer here.
2. ANSWER RECORD    An authored answer, bound to named evidence. Routed by
                    score AND coverage, then *support-verified* before it is
                    allowed out.
3. BOUNDARY AGAIN   By similarity, for a boundary question phrased without
                    any trigger word. Deliberately AFTER the answer router: a
                    question with a real supported answer must get the answer,
                    not a lecture about what we cannot do.
4. DECLARED GAP     A known hole. Returns NOT_SUPPORTED plus the specific
                    evidence request that would fill it.
5. FALLTHROUGH      Unrecognised. Still NOT_SUPPORTED -- never a guess.

Nothing in this module composes prose from retrieved text. Every sentence a
reader sees was written by a person against specific evidence IDs, and is
re-verified against that evidence on every single lookup. If the verification
fails the answer is withheld and a KIT_DEFECT is returned instead, because a
kit that quietly degrades is worse than one that stops.

`assessment_scope` is the ceiling on all of it: what this engagement actually
looked at. Absence claims are checked against it, so an answer cannot report
"we found no evidence of X" about an area the engagement never entered -- that
is NOT_ASSESSED, and it is a different sentence.
"""

import json
import os

import uncertainty as unc
from index import Document, KeywordIndex, content_terms

ANSWERED = "ANSWERED"
OUT_OF_SCOPE = "OUT_OF_SCOPE"
NOT_SUPPORTED = "NOT_SUPPORTED"
KIT_DEFECT = "KIT_DEFECT"

# Routing gates. Both must pass. See index.py for why coverage carries the
# weight here. These are deliberately exposed and printed in every trace:
# a threshold nobody can see is a threshold nobody can argue with.
MIN_SCORE = 0.12
MIN_COVERAGE = 0.45
BOUNDARY_MIN_COVERAGE = 0.30

# Below this, a routed answer is served with an explicit note naming the parts
# of the question it does not address. See _authored_answer.
FULL_COVERAGE = 0.75

# A boundary also fires on a single distinctive trigger term, because a
# question class is identifiable from one word ("percentile", "auditor",
# "worst") in a way that a subject is not. That only holds while the trigger
# terms stay distinctive: put a common word like "review" or "pass" in the list
# and every legitimate question starts hitting a boundary and getting a lecture
# instead of an answer. `audit()` enforces this so the list cannot rot: a
# trigger term may not appear in any answer record's question variants, and may
# not appear in more than this fraction of the packet's records.
TRIGGER_MAX_DOC_FRACTION = 0.20


class PacketError(Exception):
    pass


# ---------------------------------------------------------------------------
# Packet
# ---------------------------------------------------------------------------

class Packet:
    """Evidence + authored answers + declared boundaries + declared gaps."""

    def __init__(self, data):
        self.label = data.get("label", "")
        self.synthetic = bool(data.get("synthetic", False))
        self.assessment_scope = data.get("assessment_scope", {})
        self.evidence = {}
        for item in data.get("evidence", []):
            if item["id"] in self.evidence:
                raise PacketError("duplicate evidence id %s" % item["id"])
            self.evidence[item["id"]] = item
        self.answers = data.get("answers", [])
        self.boundaries = data.get("boundaries", [])
        self.gaps = data.get("gaps", [])
        self._validate()
        self.index = self._build_index()

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as handle:
            return cls(json.load(handle))

    def _validate(self):
        ids = set()
        for group, key in ((self.answers, "answer"), (self.boundaries, "boundary"),
                           (self.gaps, "gap")):
            for rec in group:
                if rec["id"] in ids:
                    raise PacketError("duplicate record id %s" % rec["id"])
                ids.add(rec["id"])
                if not rec.get("question_variants"):
                    raise PacketError(
                        "%s %s has no question_variants" % (key, rec["id"]))

    def _build_index(self):
        idx = KeywordIndex()
        for rec in self.answers:
            text = " ".join(rec["question_variants"]) + " " + " ".join(
                c.get("text", "") for c in rec.get("claims", []))
            idx.add(Document(rec["id"], "answer", text, rec))
        for rec in self.boundaries:
            text = " ".join(rec["question_variants"]) + " " + " ".join(
                rec.get("trigger_terms", []))
            idx.add(Document(rec["id"], "boundary", text, rec))
        for rec in self.gaps:
            text = " ".join(rec["question_variants"]) + " " + rec.get(
                "what_is_missing", "")
            idx.add(Document(rec["id"], "gap", text, rec))
        return idx.build()

    def area_was_assessed(self, area_key):
        """True only if the engagement actually entered this area."""
        return area_key in set(self.assessment_scope.get("areas_examined", []))


# ---------------------------------------------------------------------------
# Support verification
# ---------------------------------------------------------------------------

def verify_claim_support(packet, claim):
    """Structural check that a claim's citations actually back it.

    Run on every lookup, not once at authoring time. An evidence record can be
    removed or re-scoped between runs; a kit that verified at build time would
    keep serving the old answer.
    """
    problems = []
    ctype = claim.get("claim_type")
    cited = list(claim.get("evidence_ids", []))
    searched = list(claim.get("searched_evidence_ids", []))

    for eid in cited + searched:
        if eid not in packet.evidence:
            problems.append("cites unknown evidence id %s" % eid)

    if ctype == unc.OBSERVED_PRESENT:
        if not cited:
            problems.append(
                "OBSERVED_PRESENT with no evidence cited; a positive finding "
                "must name what shows it")

    elif ctype == unc.ABSENT_IN_SEARCHED:
        # The support for an absence claim is the list of things we LOOKED AT
        # and did not find it in. Without that list the claim is unfalsifiable.
        if not searched:
            problems.append(
                "ABSENT_IN_SEARCHED with no searched_evidence_ids; an absence "
                "claim is supported by what was examined, not by nothing")
        if cited:
            problems.append(
                "ABSENT_IN_SEARCHED cites evidence_ids as positive support; "
                "use searched_evidence_ids for what was examined")
        area = claim.get("area")
        if area and not packet.area_was_assessed(area):
            problems.append(
                "ABSENT_IN_SEARCHED in area '%s', which is not in the "
                "engagement's areas_examined; this is NOT_ASSESSED, and "
                "reporting it as an absence overstates what was done" % area)

    elif ctype == unc.NOT_ASSESSED:
        if cited or searched:
            problems.append(
                "NOT_ASSESSED cites evidence; if anything was examined this "
                "is ABSENT_IN_SEARCHED, which is a different claim")

    elif ctype == unc.CONTESTED:
        if len(cited) < 2:
            problems.append(
                "CONTESTED must cite at least two evidence items -- the "
                "disagreement is the finding")
        else:
            sides = {packet.evidence[e].get("position")
                     for e in cited if e in packet.evidence}
            sides.discard(None)
            if len(sides) < 2:
                problems.append(
                    "CONTESTED cites evidence that does not actually "
                    "disagree (positions: %s)" % (sorted(sides) or "none",))

    return problems


def _evidence_coverage(packet, claim):
    """Weakest coverage among cited evidence governs the claim's language."""
    levels = [packet.evidence[e].get("coverage", "partial")
              for e in claim.get("evidence_ids", []) if e in packet.evidence]
    if levels and all(lv == "complete" for lv in levels):
        return "complete"
    return levels[0] if len(set(levels)) == 1 and levels else "partial"


def validate_claim(packet, claim):
    """Support problems + language violations for one claim."""
    problems = verify_claim_support(packet, claim)
    violations = unc.check_claim_language(
        claim.get("claim_type"),
        claim.get("text", ""),
        search_scope=claim.get("search_scope"),
        evidence_coverage=_evidence_coverage(packet, claim),
    )
    return problems, violations


# ---------------------------------------------------------------------------
# Answer object
# ---------------------------------------------------------------------------

class _Routed:
    """A boundary that fired on a trigger term rather than on similarity."""

    def __init__(self, doc):
        self.doc = doc
        self.score = 1.0
        self.coverage = 1.0
        self.matched = []
        self.missing = []


class Answer:
    def __init__(self, question, resolution, record_id=None, claims=None,
                 boundary=None, evidence_request=None, trace=None,
                 defects=None, uncovered_terms=None):
        self.question = question
        self.resolution = resolution
        self.record_id = record_id
        self.claims = claims or []
        self.boundary = boundary
        self.evidence_request = evidence_request
        self.trace = trace or []
        self.defects = defects or []
        # Parts of the question this answer does not speak to. Being routed is
        # not the same as being answered, and the reader is entitled to know
        # which of the two they got.
        self.uncovered_terms = uncovered_terms or []

    @property
    def evidence_ids(self):
        out = []
        for claim in self.claims:
            for eid in claim.get("evidence_ids", []):
                if eid not in out:
                    out.append(eid)
            for eid in claim.get("searched_evidence_ids", []):
                if eid not in out:
                    out.append(eid)
        return out

    def as_dict(self):
        return {
            "question": self.question,
            "resolution": self.resolution,
            "record_id": self.record_id,
            "claims": self.claims,
            "boundary": self.boundary,
            "evidence_request": self.evidence_request,
            "evidence_ids": self.evidence_ids,
            "does_not_address": self.uncovered_terms,
            "routing_trace": self.trace,
            "defects": self.defects,
        }


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

class QAKit:
    def __init__(self, packet):
        self.packet = packet

    # -- routing -----------------------------------------------------------

    def _route(self, question, kind, min_cov):
        matches = self.packet.index.search(question, kinds=(kind,), limit=3)
        trace = [m.as_dict() for m in matches]
        for m in matches:
            if m.score >= MIN_SCORE and m.coverage >= min_cov:
                return m, trace
        return None, trace

    def _trigger_boundary(self, question):
        """Fire a boundary on a curated distinctive term, or return nothing."""
        q_terms = set(content_terms(question))
        for rec in self.packet.boundaries:
            triggers = set()
            for term in rec.get("trigger_terms", []):
                triggers.update(content_terms(term))
            hit = sorted(q_terms & triggers)
            if hit:
                doc = self.packet.index.get(rec["id"])
                trace = [{"id": rec["id"], "kind": "boundary",
                          "fired_on_trigger_terms": hit}]
                return _Routed(doc), trace
        return None, []

    # -- public ------------------------------------------------------------

    def ask(self, question):
        if not content_terms(question):
            return Answer(question, NOT_SUPPORTED, evidence_request={
                "what_is_missing": "the question has no content terms",
                "requested_evidence": [],
            }, trace=[])

        # 1. Scope boundary on a distinctive trigger term. A hostile question
        #    is identifiable from one word, and this runs first so it cannot
        #    route to whatever evidence happens to share its vocabulary.
        match, btrace = self._trigger_boundary(question)
        if match is not None:
            return self._boundary_answer(question, match, btrace)

        # 2. Authored answer.
        match, atrace = self._route(question, "answer", MIN_COVERAGE)
        if match is not None:
            return self._authored_answer(question, match, btrace + atrace)

        # 3. Boundary by similarity, only now. Running this ahead of the
        #    answer router was a real defect caught in testing: "what is our
        #    strongest practice" shares the rare word "strongest" with the
        #    ranking boundary's variants and nothing else, so it cleared the
        #    coverage bar and the reader got a lecture about not ranking teams
        #    instead of the change-review evidence that answers them. A
        #    question with a real supported answer should get it; the boundary
        #    is the fallback for questions that do not.
        match, btrace2 = self._route(question, "boundary",
                                     BOUNDARY_MIN_COVERAGE)
        if match is not None:
            return self._boundary_answer(question, match, btrace + atrace + btrace2)
        btrace = btrace + btrace2

        # 4. Declared gap.
        match, gtrace = self._route(question, "gap", MIN_COVERAGE)
        if match is not None:
            rec = match.doc.payload
            return Answer(question, NOT_SUPPORTED, record_id=rec["id"],
                          evidence_request={
                              "what_is_missing": rec["what_is_missing"],
                              "why_it_cannot_be_inferred":
                                  rec.get("why_it_cannot_be_inferred", ""),
                              "requested_evidence": rec.get(
                                  "requested_evidence", []),
                          },
                          trace=btrace + atrace + gtrace)

        # 5. Fallthrough. The honest default.
        return Answer(question, NOT_SUPPORTED, evidence_request={
            "what_is_missing":
                "No authored answer in this packet covers the subject of this "
                "question, and no declared evidence gap matches it either.",
            "why_it_cannot_be_inferred":
                "The kit does not compose answers from whatever evidence "
                "happens to share vocabulary with a question. Nearby evidence "
                "is not an answer.",
            "requested_evidence": [{
                "artifact": "an authored answer record bound to evidence, or "
                            "a declared gap naming the missing input",
                "held_by": "the assessment team",
                "would_settle": "whether this question is answerable from the "
                                "supplied evidence at all",
            }],
        }, trace=btrace + atrace + gtrace)

    # -- builders ----------------------------------------------------------

    def _collect_claims(self, claim_ids_or_claims):
        """Boundaries may reference answer records for their 'can say' part."""
        claims = []
        for entry in claim_ids_or_claims:
            if isinstance(entry, dict):
                claims.append(entry)
                continue
            for rec in self.packet.answers:
                if rec["id"] == entry:
                    claims.extend(rec.get("claims", []))
                    break
        return claims

    def _verify_all(self, claims):
        defects = []
        for claim in claims:
            problems, violations = validate_claim(self.packet, claim)
            for p in problems:
                defects.append({"kind": "support", "claim": claim.get("text", "")[:90],
                                "detail": p})
            for v in violations:
                d = v.as_dict()
                d["kind"] = "language"
                d["claim"] = claim.get("text", "")[:90]
                defects.append(d)
        return defects

    def _authored_answer(self, question, match, trace):
        rec = match.doc.payload
        claims = rec.get("claims", [])
        defects = self._verify_all(claims)
        if defects:
            # Withheld on purpose. A kit that serves an answer it could not
            # verify is exactly the thing this order exists to prevent.
            return Answer(question, KIT_DEFECT, record_id=rec["id"],
                          trace=trace, defects=defects)
        uncovered = []
        if match.coverage < FULL_COVERAGE:
            uncovered = list(match.missing)
        return Answer(question, ANSWERED, record_id=rec["id"], claims=claims,
                      trace=trace, uncovered_terms=uncovered)

    def _boundary_answer(self, question, match, trace):
        rec = match.doc.payload
        claims = self._collect_claims(rec.get("can_say_instead", []))
        defects = self._verify_all(claims)
        for v in unc.check_boundary_language(
                rec.get("cannot", ""), rec.get("requires", ""), len(claims)):
            d = v.as_dict()
            d["kind"] = "boundary"
            d["claim"] = ""
            defects.append(d)
        if defects:
            return Answer(question, KIT_DEFECT, record_id=rec["id"],
                          trace=trace, defects=defects)
        return Answer(question, OUT_OF_SCOPE, record_id=rec["id"],
                      claims=claims, trace=trace, boundary={
                          "cannot": rec["cannot"],
                          "requires": rec["requires"],
                          "why_this_instrument_cannot":
                              rec.get("why_this_instrument_cannot", ""),
                      })

    # -- whole-packet audit ------------------------------------------------

    def audit(self):
        """Verify every authored record without asking a question.

        Run this in CI. It is the difference between a kit that is correct and
        a kit that is correct on the three questions someone demoed.
        """
        findings = []
        for rec in self.packet.answers:
            for d in self._verify_all(rec.get("claims", [])):
                d["record_id"] = rec["id"]
                findings.append(d)
        for rec in self.packet.boundaries:
            claims = self._collect_claims(rec.get("can_say_instead", []))
            for d in self._verify_all(claims):
                d["record_id"] = rec["id"]
                findings.append(d)
            for v in unc.check_boundary_language(
                    rec.get("cannot", ""), rec.get("requires", ""), len(claims)):
                d = v.as_dict()
                d["kind"] = "boundary"
                d["record_id"] = rec["id"]
                findings.append(d)
        # A trigger term is unsafe exactly when a question someone could
        # legitimately ask uses it. The first version of this check used an
        # absolute idf floor and silently stopped working on a smaller packet,
        # because idf is relative to corpus size. This one is not: it asks
        # whether the word appears in any ANSWERABLE question, which is the
        # harm itself rather than a proxy for it.
        answer_vocab = {}
        for rec in self.packet.answers:
            for variant in rec["question_variants"]:
                for tok in content_terms(variant):
                    answer_vocab.setdefault(tok, []).append(rec["id"])
        n_docs = max(len(self.packet.index.docs), 1)
        for rec in self.packet.boundaries:
            for term in rec.get("trigger_terms", []):
                for tok in content_terms(term):
                    if tok in answer_vocab:
                        findings.append({
                            "kind": "boundary_trigger",
                            "record_id": rec["id"],
                            "detail": "trigger term '%s' also appears in the "
                                      "question variants of %s: an ordinary "
                                      "answerable question containing this "
                                      "word would fire the boundary and be "
                                      "lectured instead of answered (idf "
                                      "%.2f)"
                                      % (tok, ", ".join(sorted(
                                          set(answer_vocab[tok]))),
                                         self.packet.index.idf(tok))})
                        continue
                    df = sum(1 for d in self.packet.index.docs
                             if tok in d.term_set)
                    if df > max(2, TRIGGER_MAX_DOC_FRACTION * n_docs):
                        findings.append({
                            "kind": "boundary_trigger",
                            "record_id": rec["id"],
                            "detail": "trigger term '%s' appears in %d of %d "
                                      "records (idf %.2f), above the %.0f%% "
                                      "ceiling: too common to identify a "
                                      "question class safely"
                                      % (tok, df, n_docs,
                                         self.packet.index.idf(tok),
                                         TRIGGER_MAX_DOC_FRACTION * 100)})
        for rec in self.packet.gaps:
            if not rec.get("requested_evidence"):
                findings.append({
                    "kind": "gap", "record_id": rec["id"],
                    "detail": "a declared gap must name the evidence that "
                              "would fill it; 'we don't know' without a "
                              "request is not actionable"})
        return findings


def load_kit(path):
    return QAKit(Packet.load(path))


def default_packet_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", "packet.json")
