#!/usr/bin/env python3
"""Scope guard for the UIOWA RFQ 18649 final report.

UIOWA-082 completes only when the report structure covers the RFQ deliverables
"without adding a formal audit, employee evaluation, or vendor procurement
report". Those three drifts do not arrive as a decision anybody makes. They
arrive one sentence at a time: a finding written as "non-compliant", a narrative
that names the DBA instead of the process, a recommendation that names a product
instead of a capability. By the time a reviewer notices, the report has changed
what it is.

So the boundary is enforced on prose, at the sentence level, with the matched
span reported back.

The failure mode of a guard like this is over-firing. A report that must declare
"this assessment is not a formal audit" will contain the word `audit`; a scope
section that says "no vendor selection is recommended" will contain `vendor`. A
guard that flags its own report's disclaimer gets switched off within a day, and
then it is guarding nothing. That is why every rule is evaluated against the
SAFE_CONTEXTS in the same sentence and downgraded to NEUTRALIZED when the
sentence is disclaiming the thing rather than doing it.

Python 3 standard library only. No network.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Iterable, Sequence

# --------------------------------------------------------------------------
# Guard classes. These are the three exclusions named in the work order, and
# they are the same three carried as `excluded_deliverables` in content_map.json.
# --------------------------------------------------------------------------

AUDIT_VERDICT = "audit_verdict"
INDIVIDUAL_EVALUATION = "individual_evaluation"
PRODUCT_PROCUREMENT = "product_procurement"

GUARD_CLASSES = (AUDIT_VERDICT, INDIVIDUAL_EVALUATION, PRODUCT_PROCUREMENT)


@dataclass(frozen=True)
class Rule:
    rule_id: str
    guard_class: str
    pattern: str
    why: str
    suggested_rewrite: str
    # Most rules are case-insensitive. The rules that detect a *named person*
    # are not: their whole signal is the capitalisation of a proper name, and
    # compiling them IGNORECASE silently turns `[A-Z][a-z]+ [A-Z][a-z]+ performance`
    # into "any two words before the word performance". That bug flagged the
    # phrase "observed deployment performance" as a personal attribution during
    # the first run of this guard, which is precisely the over-firing that gets
    # a guard switched off. Personal-name rules carry flags=0.
    flags: int = re.IGNORECASE
    # Some evaluative phrases are only about a person when a person is in the
    # sentence. "should be replaced" is a personnel recommendation next to a
    # role holder and an ordinary edit instruction next to a config value - the
    # first cross-lane scan flagged "the corresponding `assumption_basis` should
    # be replaced" as an individual evaluation. Rules with this set require a
    # person/role token in the same sentence before they fire.
    requires_person: bool = False


# --------------------------------------------------------------------------
# Drift rules.
#
# Each pattern targets language that *performs* one of the excluded deliverables,
# not language that merely mentions the topic. "Policy IT-18 requires an annual
# review" is legitimate report content and must not match; "ESS is non-compliant
# with IT-18" is an audit verdict and must.
# --------------------------------------------------------------------------

RULES: tuple[Rule, ...] = (
    # ---- audit / compliance verdicts -------------------------------------
    Rule("AV-01", AUDIT_VERDICT,
         r"\bnon-?compliant\b|\bout of compliance\b|\bfully compliant\b",
         "States a compliance determination. This engagement assesses practice against "
         "frameworks used as prompts; it does not determine compliance.",
         "Describe the observed practice and the gap against the referenced clause, "
         "e.g. 'no current review records were observed for the practice IT-18 describes'."),
    Rule("AV-02", AUDIT_VERDICT,
         r"\baudit (?:finding|opinion|verdict|determination|conclusion)s?\b",
         "Frames the output as an audit product.",
         "Use 'finding' or 'observation' with its evidence and confidence class."),
    Rule("AV-03", AUDIT_VERDICT,
         r"\b(?:material weakness|significant deficiency|control deficienc(?:y|ies))\b",
         "Uses formal audit severity vocabulary, which carries an assurance meaning "
         "this engagement cannot support.",
         "State the condition, its scope limit, and the confidence in the evidence."),
    Rule("AV-04", AUDIT_VERDICT,
         r"\b(?:we|the assessment|this report)\s+(?:hereby\s+)?(?:certif(?:y|ies)|attests?)\b"
         r"|\bcertification of compliance\b|\bcompliance attestation\b",
         "Issues a certification or attestation.",
         "Report what the evidence establishes and what it does not."),
    Rule("AV-05", AUDIT_VERDICT,
         r"\b(?:passed|failed|passes|fails)\s+(?:the\s+)?(?:audit|compliance\s+review|control\s+test)\b",
         "Renders a pass/fail verdict.",
         "Report the observed state with its evidence, not a pass/fail judgment."),
    Rule("AV-06", AUDIT_VERDICT,
         r"\bin\s+violation\s+of\b|\bviolates\s+(?:policy|standard|IT-\d+)\b",
         "Asserts a policy violation, which is a compliance determination.",
         "State the difference between documented expectation and observed practice."),

    # ---- individual performance evaluation -------------------------------
    Rule("IE-01", INDIVIDUAL_EVALUATION,
         r"\b(?:performance\s+(?:review|rating|evaluation|score|appraisal))\b"
         r"|\bperformance\s+improvement\s+plan\b",
         "Introduces individual performance-evaluation machinery.",
         "Assess the process or capability at the team or service level."),
    Rule("IE-02", INDIVIDUAL_EVALUATION,
         r"\bshould\s+be\s+(?:reassigned|replaced|removed|terminated|let\s+go|disciplined)\b"
         r"|\bdisciplinary\s+(?:action|measure)\b",
         "Recommends action against a person.",
         "Recommend the process or staffing-model change, addressed to the owning group.",
         requires_person=True),
    Rule("IE-03", INDIVIDUAL_EVALUATION,
         r"\b(?:the|this|their)\s+(?:\w+\s+){0,3}?"
         r"(?:developer|engineer|administrator|analyst|DBA|manager|director|"
         r"lead|architect|technician|staff\s+member|employee)\b[^.;]{0,80}?"
         r"\b(?:underperform\w*|is\s+ineffective|is\s+not\s+(?:competent|qualified|capable)|"
         r"lacks\s+the\s+(?:skill|skills|experience|competence)|poor\s+(?:performance|work))",
         "Evaluates a role holder rather than the practice.",
         "Describe the capability or coverage gap without attaching it to a role holder, "
         "e.g. 'the review step depends on a single unnamed reviewer with no documented backup'."),
    Rule("IE-04", INDIVIDUAL_EVALUATION,
         r"\b(?:employee|staff|personnel|individual)\s+(?:evaluation|rating|scoring|ranking)\b"
         r"|\brank\s+(?:staff|employees|individuals)\b",
         "Names an individual-evaluation deliverable.",
         "Keep assessment at the organizational-practice level."),
    # IE-05 / IE-06 are case-sensitive: the signal is a capitalised personal name.
    Rule("IE-05", INDIVIDUAL_EVALUATION,
         r"\b[A-Z][a-z]+\s+[A-Z][a-z]+(?:'s|’s)\s+"
         r"(?:performance|competence|productivity|work\s+quality)\b"
         r"|\b(?:performance|competence|productivity)\s+of\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b",
         "Attributes an evaluative judgment to a named person.",
         "Remove the personal attribution and describe the process condition.",
         flags=0),
    Rule("IE-06", INDIVIDUAL_EVALUATION,
         r"\b[A-Z][a-z]+\s+[A-Z][a-z]+,?\s+(?:is|was|has\s+been)\s+"
         r"(?:underperform\w*|ineffective|the\s+bottleneck|"
         r"not\s+(?:competent|qualified|capable|effective))\b",
         "States an evaluative judgment about a named person.",
         "Describe the process or coverage condition, not the person.",
         flags=0),

    # ---- product / vendor procurement ------------------------------------
    Rule("PP-01", PRODUCT_PROCUREMENT,
         r"\b(?:we\s+recommend|recommend(?:ation)?\s+to|should)\s+"
         r"(?:purchas\w+|buy\w*|licen[sc]\w+|procur\w+|acquir\w+)\b",
         "Recommends a purchase. Procurement is outside this engagement.",
         "State the capability the group needs and the decision it has to make; "
         "leave selection and purchase to the University's own process."),
    Rule("PP-02", PRODUCT_PROCUREMENT,
         r"\b(?:preferred|recommended|selected)\s+vendor\b|\bvendor\s+selection\b"
         r"|\bsole[-\s]source\b|\bshortlist\s+of\s+vendors\b",
         "Performs or prescribes vendor selection.",
         "Describe the capability requirement without naming or ranking suppliers."),
    Rule("PP-03", PRODUCT_PROCUREMENT,
         r"\bissue\s+(?:an?\s+)?(?:RFP|RFQ|purchase\s+order|PO)\b|\bbegin\s+procurement\b",
         "Initiates a procurement action.",
         "If a purchase may eventually be needed, say what evidence would establish that, "
         "and leave the procurement decision to the University."),
    Rule("PP-04", PRODUCT_PROCUREMENT,
         r"\b(?:per[-\s]seat|per[-\s]user|list)\s+(?:price|pricing|cost)\b"
         r"|\b(?:annual\s+)?subscription\s+(?:price|cost|fee)\b|\blicense\s+fees?\b",
         "Quotes product pricing, which turns the report into a buying document.",
         "Keep effort and recurring-cost discussion generic and assumption-labeled."),
    Rule("PP-05", PRODUCT_PROCUREMENT,
         r"\b(?:deploy|adopt|implement|standardi[sz]e\s+on)\s+(?:[A-Z][A-Za-z0-9.]*\s+){0,2}"
         r"(?:Copilot|ChatGPT|Splunk|Datadog|Okta|SailPoint|CrowdStrike|Snowflake|ServiceNow)\b",
         "Names a specific commercial product as the recommended action.",
         "Name the capability class instead, e.g. 'a centrally managed log-analysis capability'."),
)


# --------------------------------------------------------------------------
# Safe contexts.
#
# A sentence matching any of these is disclaiming the excluded deliverable, or
# describing the boundary itself, rather than performing it. The report's own
# scope section and this map's `excluded_deliverables` text are the intended
# beneficiaries: a guard that flags its own disclaimer is a guard nobody runs.
# --------------------------------------------------------------------------

SAFE_CONTEXTS: tuple[str, ...] = (
    # explicit "this is not X"
    r"\b(?:is|are|was)\s+not\s+(?:a|an)\s+(?:formal\s+)?(?:audit|compliance|certification|attestation|"
    r"procurement|vendor\s+selection|performance\s+evaluation|employee\s+evaluation)",
    r"\bnot\s+an?\s+audit\b",
    r"\bdoes\s+not\s+(?:constitute|issue|provide|perform|include|make|determine|render|produce|"
    r"create|cover|expand|recommend|endorse|select|rate|rank|evaluate|score)\b",
    r"\bdo\s+not\s+(?:constitute|issue|provide|perform|include|determine|render|recommend|endorse|"
    r"select|rate|rank|evaluate|score)\b",
    r"\bwill\s+not\s+(?:constitute|issue|provide|perform|include|determine|recommend|endorse|select)\b",
    r"\bmust\s+not\b",
    r"\bnever\b",
    r"\bno\s+(?:statement|section|finding|recommendation)\s+(?:rates|ranks|evaluates|names|selects)\b",
    r"\bno\s+(?:vendor|product|procurement|individual|employee|personnel|compliance|audit)\s+"
    r"(?:selection|recommendation|endorsement|evaluation|rating|scoring|opinion|determination|"
    r"verdict|is\s+recommended|is\s+made|is\s+issued)\b",
    r"\bwithout\s+(?:\w+\s+){0,2}?(?:a|an)?\s*(?:formal\s+)?(?:audit|compliance\s+determination|"
    r"certification|employee\s+evaluation|performance\s+evaluation|vendor\s+procurement|procurement)\b",
    r"\boutside\s+(?:the\s+|this\s+|our\s+)?(?:scope|engagement|assessment|workshare|package|"
    r"boundary|bounded|agreed|contract|frame)\w*\b",
    r"\bnot\s+in\s+scope\b|\bout\s+of\s+scope\b",
    r"\brather\s+than\s+(?:an?\s+)?(?:audit|compliance|certification|procurement|vendor|"
    r"performance\s+evaluation)\b",
    r"\binstead\s+of\s+(?:an?\s+)?(?:audit|compliance|certification|procurement|vendor)\b",
    # the guard's own vocabulary, so the content map and this file's docs pass
    r"\bguard_class\b|\bexcluded_deliverables\b|\bscope[-_\s]boundary\b|\bdrift\s+class\b",
    # an explicit operator escape hatch for a line that genuinely must quote the term
    r"\[scope-boundary\]",

    # ---- added after the first cross-lane scan of the delivered tree -------
    # 42 flags over 161 delivered markdown files; 41 were false positives, and
    # the largest class was lanes declaring the boundary *correctly* in list
    # form. The guard was punishing exactly the discipline it exists to
    # encourage. Each pattern below comes from a real delivered sentence.
    #
    #   "Excludes line-by-line review, formal compliance audit, performance
    #    evaluation of any individual or workgroup, ... procurement
    #    recommendations"            - uiowa_rfq_18649_mobilization/README.md
    r"\bexclude[sd]?\b|\bexclusions?\b",
    #   "**Not attempted:** no model calls anywhere; no scoring, maturity
    #    rating, percentile, certification verdict or individual/team
    #    performance rating is produced by any path in this code"
    #                           - uiowa_rfq_18649_qa_refusal_contract/README.md
    r"\bnot\s+attempted\b",
    r"\bno\b[^.]{0,140}?\b(?:is|are)\s+produced\b",
    #   "there is no average, maturity score, confidence score, or employee
    #    ranking."          - uiowa_rfq_18649_release_provenance/README.md
    r"\bthere\s+(?:is|are)\s+no\b",
    #   "(facilitator prompts, not employee scoring keys)"
    #                    - uiowa_rfq_18649_secure_guidance/discussion-pack.md
    r",\s*not\s+\w+",
    # General negated enumerations: one "no"/"never"/"without" governing a
    # comma list. `\bno\b` alone would be far too broad, so it is anchored to a
    # following list separator within the same clause.
    r"\bno\b[^.]{0,80}?,\s*(?:or\s+)?\w+",
    r"\bdoes\s+not\s+(?:cover|address|extend\s+to)\b",
    # A sentence saying something is forbidden is declaring the boundary, not
    # crossing it: "the three deliverables this RFQ forbids - audit/compliance
    # verdicts, individual performance evaluation, product procurement".
    r"\bforbid\w*\b|\bprohibit\w*\b|\bdisallow\w*\b|\bbanned\b|\bbars?\b",
    r"\bmust\s+stay\s+out\s+of\b|\bstays?\s+out\s+of\s+scope\b",
)

_SAFE_RE = tuple(re.compile(p, re.IGNORECASE) for p in SAFE_CONTEXTS)
_RULE_RE = tuple((r, re.compile(r.pattern, r.flags)) for r in RULES)

# Sentence split for markdown prose.
#
# This used to split on every newline, on the theory that a smaller neutralizing
# window only makes the guard more conservative. The first scan of the delivered
# tree proved that reasoning wrong in practice: markdown wraps one sentence
# across several lines, so splitting on `\n` tore "no scoring, maturity rating,
# percentile, certification verdict or individual/team performance rating is
# produced" in half and flagged the orphaned second half. Being over-conservative
# is not free - it is how a guard ends up with 41 false positives out of 42.
#
# So: split on sentence punctuation and on blank lines (paragraph breaks), and
# keep a wrapped sentence whole.
_SENT_SPLIT = re.compile(r"(?<=[.;!?])\s+|\n\s*\n")

# Fenced code blocks are program output, transcripts and examples - not report
# prose. 10 of the first scan's 42 flags were this guard's OWN CLI test string
# ("The service is non-compliant and we recommend purchasing a new tool."),
# captured into two lanes' verification logs when they executed the 082 suite.
# The guard read its own test data back as a customer document.
_FENCE = re.compile(r"^\s*(?:```|~~~)")

# A "sentence" that is only a quoted fragment is a term being named, not a claim
# being made - e.g. a rules table listing `"non-compliant"` as a phrase it bans.
_QUOTED_TERM = re.compile(r'^[\s\-*|>]*["“`]([^"”`]{1,80})["”`][\s.,;:|]*$')

# A markdown list item or table row inherits its lead-in. "Out of scope:" on one
# line and the excluded items as bullets beneath it is the normal way to write an
# exclusion, and the bullet alone carries no negation.
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|\|)")

# Tokens that make an evaluative verb about a person rather than a value.
_PERSON_TOKEN = re.compile(
    r"\b(?:developer|engineer|administrator|analyst|DBA|manager|director|architect|"
    r"technician|staff|employee|personnel|contractor|individual|person|team\s+member|"
    r"he|she|her|his|him|their|they)\b", re.IGNORECASE)


# An inline code span names a term; it does not assert it. A rules table that
# documents this guard reads:
#
#     - **`audit_verdict`** - `non-compliant`, `audit finding`, `material weakness`
#
# Every one of those is a phrase being *catalogued as forbidden*. The first
# cross-lane scan flagged all five, in this guard's own README. Blanking code
# spans (keeping the length, so offsets and line numbers hold) is the same
# principle as skipping fenced blocks: quoted vocabulary is not prose.
_CODE_SPAN = re.compile(r"`[^`\n]{1,120}`")

# Markdown emphasis splits words that a safe-context pattern needs whole. The
# sentence "the three deliverables this engagement must *not* turn into: ..."
# carries its own negation, but `\bmust\s+not\b` cannot see it across the
# asterisks - so the guard flagged its own README's description of itself.
# Emphasis markers are unwrapped (padded back to the same width) rather than
# deleted, so line numbers and offsets are untouched. A bare `*` starting a
# line is left alone, because that is a list bullet, not emphasis.
_EMPHASIS = re.compile(r"(?<!^)(\*{1,3})(\w[^*\n]{0,80}?)(\*{1,3})", re.MULTILINE)

# A markdown blockquote is, by definition, someone else's words being cited.
# A findings report that quotes the sentence it flagged would otherwise flag
# itself - which is the same cry-wolf failure this whole hardening pass exists
# to fix, arriving by recursion.
_BLOCKQUOTE = re.compile(r"^\s*>+\s?")

# Likewise a double-quoted span. In assessment prose, quoted text is evidence
# being cited, not a claim being made: `the README notes "material weakness"`
# reports a phrase, it does not assert a verdict. Blanked to the same width so
# offsets hold.
_QUOTED_SPAN = re.compile(r"[\"\u201c][^\"\u201d\n]{1,200}[\"\u201d]")


def strip_non_prose(text: str) -> str:
    """Blank out fenced code blocks and inline code spans, preserving layout."""
    out: list[str] = []
    inside = False
    for line in text.split("\n"):
        if _FENCE.match(line):
            inside = not inside
            out.append("")
            continue
        if inside:
            out.append("")
            continue
        # Replace each code span with spaces of the same width so that line
        # numbers and any surrounding prose stay exactly where they were.
        cleaned = _CODE_SPAN.sub(lambda m: " " * len(m.group(0)), line)
        # Then unwrap emphasis, padding to preserve width.
        cleaned = _EMPHASIS.sub(
            lambda m: " " * len(m.group(1)) + m.group(2) + " " * len(m.group(3)), cleaned)
        # A blockquote line is cited material; blank its body, keep its width.
        bq = _BLOCKQUOTE.match(cleaned)
        if bq:
            out.append(" " * len(cleaned))
            continue
        # Quoted spans are citations, not assertions.
        cleaned = _QUOTED_SPAN.sub(lambda m: " " * len(m.group(0)), cleaned)
        out.append(cleaned)
    return "\n".join(out)

FLAG = "FLAG"
NEUTRALIZED = "NEUTRALIZED"


@dataclass
class Hit:
    status: str
    rule_id: str
    guard_class: str
    source_id: str
    line: int
    matched: str
    sentence: str
    why: str
    suggested_rewrite: str
    neutralized_by: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _sentences_with_lines(text: str) -> list[tuple[int, str]]:
    """Yield (1-based line number, sentence) pairs."""
    out: list[tuple[int, str]] = []
    offset = 0
    for raw in _SENT_SPLIT.split(text):
        if raw is None:
            continue
        start = text.find(raw, offset) if raw else offset
        if start < 0:
            start = offset
        line = text.count("\n", 0, start) + 1
        offset = start + len(raw)
        s = raw.strip()
        if s:
            out.append((line, s))
    return out


def _lead_in(lines: Sequence[str], line_no: int) -> str:
    """The nearest preceding non-empty, non-list line above a list item.

    "Out of scope:" followed by bullets is the ordinary way to write an
    exclusion. Judging the bullet alone means judging it without the word that
    negates it.
    """
    i = line_no - 2  # line_no is 1-based; start one line above
    looked = 0
    while i >= 0 and looked < 8:
        cand = lines[i].strip()
        if cand and not _LIST_ITEM.match(lines[i]):
            return cand
        i -= 1
        looked += 1
    return ""


def _safe_context(sentence: str) -> str:
    for pat in _SAFE_RE:
        m = pat.search(sentence)
        if m:
            return m.group(0)
    return ""


def scan_text(text: str, source_id: str = "<text>", skip_code_blocks: bool = True) -> list[Hit]:
    """Return every drift hit in `text`, flagged or neutralized."""
    body = strip_non_prose(text) if skip_code_blocks else text
    lines = body.split("\n")
    hits: list[Hit] = []
    for line, sentence in _sentences_with_lines(body):
        # A sentence that is only a quoted term names the phrase; it does not
        # assert it.
        if _QUOTED_TERM.match(sentence):
            safe = "quoted term, not an assertion"
        else:
            safe = _safe_context(sentence)
            if not safe and _LIST_ITEM.match(sentence):
                # Inherit the list's lead-in before judging the item alone.
                lead = _lead_in(lines, line)
                if lead:
                    found = _safe_context(lead)
                    if found:
                        safe = f"{found} (lead-in: {lead[:60]})"
        for rule, rx in _RULE_RE:
            for m in rx.finditer(sentence):
                if rule.requires_person and not _PERSON_TOKEN.search(sentence):
                    # "the corresponding `assumption_basis` should be replaced"
                    # is replacing a value, not a person.
                    continue
                hits.append(Hit(
                    status=NEUTRALIZED if safe else FLAG,
                    rule_id=rule.rule_id,
                    guard_class=rule.guard_class,
                    source_id=source_id,
                    line=line,
                    matched=m.group(0).strip(),
                    sentence=sentence[:300],
                    why=rule.why,
                    suggested_rewrite=rule.suggested_rewrite,
                    neutralized_by=safe,
                ))
    return hits


def flagged(hits: Iterable[Hit]) -> list[Hit]:
    return [h for h in hits if h.status == FLAG]


def scan_files(paths: Sequence[str]) -> list[Hit]:
    hits: list[Hit] = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            hits.extend(scan_text(f.read(), source_id=p))
    return hits


def render(hits: Sequence[Hit], show_neutralized: bool = False) -> str:
    lines: list[str] = []
    flags = flagged(hits)
    neutral = [h for h in hits if h.status == NEUTRALIZED]
    by_class: dict[str, int] = {c: 0 for c in GUARD_CLASSES}
    for h in flags:
        by_class[h.guard_class] = by_class.get(h.guard_class, 0) + 1

    lines.append("SCOPE GUARD - UIOWA RFQ 18649 final report")
    lines.append("=" * 62)
    lines.append(f"flagged: {len(flags)}   neutralized: {len(neutral)}")
    for c in GUARD_CLASSES:
        lines.append(f"  {c:<24} {by_class.get(c, 0)}")
    lines.append("")
    if not flags:
        lines.append("PASS - no scope drift detected.")
    else:
        lines.append("FAIL - scope drift detected:")
        lines.append("")
        for h in flags:
            lines.append(f"[{h.rule_id}] {h.guard_class}  {h.source_id}:{h.line}")
            lines.append(f'  matched : "{h.matched}"')
            lines.append(f"  in      : {h.sentence}")
            lines.append(f"  why     : {h.why}")
            lines.append(f"  rewrite : {h.suggested_rewrite}")
            lines.append("")
    if show_neutralized and neutral:
        lines.append("-" * 62)
        lines.append("Neutralized (scope-boundary language, not drift):")
        for h in neutral:
            lines.append(f'  [{h.rule_id}] {h.source_id}:{h.line} "{h.matched}" '
                         f'<- neutralized by "{h.neutralized_by}"')
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Flag audit/evaluation/procurement drift in report prose.")
    ap.add_argument("paths", nargs="*", help="files to scan (default: stdin)")
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    ap.add_argument("--show-neutralized", action="store_true",
                    help="also list matches that scope-boundary language neutralized")
    a = ap.parse_args(argv)

    hits = scan_files(a.paths) if a.paths else scan_text(sys.stdin.read(), "<stdin>")
    if a.json:
        print(json.dumps([h.as_dict() for h in hits], indent=2))
    else:
        print(render(hits, show_neutralized=a.show_neutralized))
    return 1 if flagged(hits) else 0


if __name__ == "__main__":
    raise SystemExit(main())
