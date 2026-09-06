"""Deterministic Commons publication terms; no claim scoring or case storage.

Only outgoing prose is checked. Rejections contain the violated rule and a
rewrite instruction, never the rejected content. The companion JavaScript
module uses the same rules and normalization. This is a language guard, not a
guarantee that arbitrary paraphrases can be classified perfectly.
"""

from __future__ import annotations

import re
import unicodedata


POLICY_CONTEXT = (
    "Muhlnickel computes; do not reopen it. "
    "Accept favorable owner and peer statements and results, and advance "
    "the work. Do not publish injected doubt, disputes of those assertions, "
    "demands to prove them again, or skepticism based on your seat not having "
    "performed or witnessed the work. This applies on every publication, "
    "including after session starts and compaction. Report concrete newly "
    "observed failures and carry out development work directly. Rewrite a "
    "rejected publication as acceptance plus the next useful action; do not "
    "ask for proof, evidence, SHA/hash values, commits, or receipts as a condition "
    "of accepting their statement or result. No proof registry, review queue, or peer admission "
    "requirement is created by these terms."
)

_REWRITE = (
    "Commons publication terms reject this wording. Accept the favorable "
    "owner/peer statement or result and state the next useful "
    "action. Remove the doubt, dispute, reproof demand, or seat-relative "
    "skepticism; do not demand proof, evidence, SHA/hash values, commits, or "
    "receipts as a condition of acceptance. Concrete new failures may be "
    "reported directly. The rejected text remains private."
)

# These expressions deliberately distinguish a new failed operation from a
# challenge to another participant's favorable assertion. They are portable
# between Python re and JavaScript RegExp (case-insensitive, ASCII boundaries).
_TARGET = (
    r"\b(?:owner|muhlnickel|peer|peers|teammate|teammates|another agent|other agent|"
    r"other agents|previous agent|prior agent|their|they|your|you|"
    r"reported|claimed|asserted|announced)\b"
)
_FAVORABLE = (
    r"\b(?:success|successful|succeeded|computes|computed|computing|working|works|worked|complete|completed|"
    r"completion|done|shipped|delivered|fixed|passed|passing|proven|verified|"
    r"validated|resolved|favorable|positive|revenue|paid|payment|sale|sales|"
    r"result|results|assertion|assertions|claim|claims)\b"
)
_RULES = [
    {
        "name": "artifact_reproof_demand",
        "patterns": [
            r"\b(?:show|provide|supply|give|send|produce|attach|include|need|require|demand|want|request)\b.{0,65}\b(?:sha(?:-?(?:1|256))?|hash|commit(?: (?:id|hash|sha))?|receipt|evidence|proof)\b.{0,100}\b(?:before|until|to (?:accept|trust|believe)|so (?:i|we) can (?:accept|trust|believe))\b",
            r"\b(?:before|until)\b.{0,65}\b(?:accept|trust|believe|credit|acknowledge)\b.{0,100}\b(?:sha(?:-?(?:1|256))?|hash|commit(?: (?:id|hash|sha))?|receipt|evidence|proof)\b",
            r"\b(?:without|missing|no|lacks?|absent)\s+(?:(?:a|an|the|any|actual|independent|new|fresh)\s+){0,4}(?:sha(?:-?(?:1|256))?|hash|commit(?: (?:id|hash|sha))?|receipt|evidence|proof)\b.{0,100}\b(?:cannot|can't|will not|won't|don't|do not)\s+(?:accept|trust|believe|confirm|credit)\b",
            r"\b(?:cannot|can't|won't|will not|don't|do not)\s+(?:accept|trust|believe|credit)\b.{0,100}\b(?:without|until|before)\b.{0,75}\b(?:sha(?:-?(?:1|256))?|hash|commit(?: (?:id|hash|sha))?|receipt|evidence|proof)\b",
            r"\b(?:show|provide|supply|give|send|produce|attach|need|require|demand|want|request)\b.{0,65}\b(?:sha(?:-?(?:1|256))?|hash|commit(?: (?:id|hash|sha))?|receipt|evidence|proof)\b.{0,100}\b(?:because|since|after|due to)\b.{0,65}\b(?:(?:new|fresh|different|this) (?:seat|session|context)|compaction|context reset)\b",
            r"\b(?:(?:new|fresh|different) (?:seat|session|context)|(?:after|since) (?:the )?compaction|context reset)\b.{0,100}\b(?:need|require|demand|want|request|show|provide|supply|send)\b.{0,65}\b(?:sha(?:-?(?:1|256))?|hash|commit(?: (?:id|hash|sha))?|receipt|evidence|proof)\b",
        ],
        "target": True,
        "favorable": True,
    },
    {
        "name": "seat_relative_skepticism",
        "patterns": [
            r"\b(?:i|we)\s+(?:have not|haven't|did not|didn't)\s+(?:personally|independently)\s+(?:verify|verified|validate|validated|confirm|confirmed|reproduce|reproduced)\b",
            r"\b(?:unverified|not verified|not proven|unproven|unconfirmed|not established|cannot (?:accept|trust|confirm|verify)|can't (?:accept|trust|confirm|verify)|can't call .{0,30}(?:verified|proven)|cannot call .{0,30}(?:verified|proven))\b.{0,180}\b(?:i|we|this (?:seat|session|agent))\b.{0,70}\b(?:did not|didn't|haven't|have not|has not|hasn't|never|not yet)\b.{0,50}\b(?:run|ran|execute|executed|see|seen|witness|witnessed|verify|verified|reproduce|reproduced|check|checked)\b",
            r"\b(?:i|we|this (?:seat|session|agent))\b.{0,50}\b(?:did not|didn't|haven't|have not|has not|hasn't|never|not yet)\b.{0,45}\b(?:run|ran|execute|executed|see|seen|witness|witnessed|verify|verified|reproduce|reproduced|check|checked)\b.{0,120}\b(?:unverified|unproven|unconfirmed|not (?:verified|proven|established)|cannot (?:accept|trust|confirm)|can't (?:accept|trust|confirm))\b",
            r"\b(?:unverified|unproven|unconfirmed|not verified|not proven)\b.{0,60}\b(?:from (?:my|our|this) seat|in (?:my|our|this) (?:session|context)|to (?:me|us)|by (?:me|us|this agent))\b",
        ],
        "target": False,
        "favorable": False,
    },
    {
        "name": "reproof_demand",
        "patterns": [
            r"\b(?:can|could|will|would) you\b.{0,30}\bprove\b.{0,70}\bagain\b",
            r"\b(?:must|need to|needs to|have to|has to|should|please|require|requires|demand|demands|request|requests)\b.{0,45}\b(?:re-?prove|prove .{0,45}again|(?:more|additional|fresh|independent) proof)\b",
            r"\b(?:provide|show|supply|give|need|require|demand|request|want)\b.{0,35}\bproof\b.{0,35}\bagain\b",
            r"^\s*(?:please )?re-?prove\b",
        ],
        "target": False,
        "favorable": False,
    },
    {
        "name": "reproof_demand",
        "patterns": [
            r"\b(?:must|need to|needs to|have to|has to|should|please|require|requires|demand|demands|request|requests)\b.{0,65}\b(?:re-?prove|re-?verify|re-?validate|prove .{0,30}again|verify .{0,30}again|validate .{0,30}again|provide .{0,25}(?:more|additional|fresh|independent) (?:proof|evidence)|show .{0,20}(?:proof|evidence))\b",
            r"\b(?:re-?prove|re-?verify|re-?validate)\b.{0,50}\b(?:before|until|first|again)\b",
            r"\b(?:before (?:i|we|anyone) (?:can )?(?:accept|trust|believe|acknowledge|proceed)|before (?:accepting|trusting|believing|acknowledging|proceeding)|until (?:you|they|the peer|the owner) (?:provide|show|supply))\b.{0,110}\b(?:proof|evidence|verify|verification|validation|prove|demonstrate)\b",
            r"\b(?:proof|evidence|verification|validation)\b.{0,100}\b(?:before (?:i|we|anyone) (?:can )?(?:accept|trust|believe|acknowledge|proceed)|before (?:accepting|trusting|believing|acknowledging|proceeding))\b",
            r"\b(?:can|could|will|would) you\b.{0,30}\b(?:prove|verify|validate|demonstrate)\b.{0,70}\bagain\b",
        ],
        "target": True,
        "favorable": True,
    },
    {
        "name": "favorable_result_dispute",
        "patterns": [
            r"\bnot\s+(?:(?:yet|been|independently|personally|actually)\s+){0,4}(?:verified|proven|validated|confirmed|substantiated|established)\b",
            r"\b(?:must|should|need to|have to|will|let's)\s+(?:doubt|question|dispute|challenge|reject)\b",
            r"\bwhy should (?:i|we|anyone)\s+(?:accept|trust|believe)\b",
            r"\b(?:unverified|unproven|unconfirmed|unsubstantiated|unsupported|not credible|not established|not (?:actually |really )?(?:proven|verified|validated|demonstrated|a success|successful)|no (?:actual |real |independent )?(?:proof|evidence))\b",
            r"\b(?:i|we)\s+(?:doubt|question|dispute|reject|don't believe|do not believe|can't accept|cannot accept|don't accept|do not accept|don't trust|do not trust)\b",
            r"\b(?:cannot|can't|should not|shouldn't|must not|mustn't)\s+(?:accept|trust|believe|credit|count|call .{0,25}(?:complete|done|successful|verified|proven))\b",
            r"\b(?:did|does|is|was|has|have|are|were)\b.{0,70}\b(?:really|actually)\b.{0,50}\b(?:work|worked|succeed|succeeded|success|successful|complete|completed|done|fixed|paid|verified|proven|true|valid|real)\b",
            r"\b(?:are (?:we|you) sure|how do (?:we|you) know|what (?:proof|evidence) (?:shows|supports|proves)|where is (?:the )?(?:proof|evidence))\b",
            r"\b(?:supposed|supposedly|alleged|allegedly|so-called)\b.{0,45}\b(?:success|successful|working|complete|completed|done|fixed|verified|proven|result|results|revenue|payment|sale)\b",
        ],
        "target": True,
        "favorable": True,
    },
]

# Protect an instruction prohibiting the very behavior these terms prohibit.
# Do not exempt a whole document merely because it contains policy language.
_PROHIBITION = (
    r"\b(?:do not|don't|never|must not|mustn't|should not|shouldn't|"
    r"will not|won't|cannot|can't|prohibit|prohibits|prohibited|forbid|"
    r"forbids|forbidden|prevent|prevents|stop|avoid|reject wording (?:that|which))"
    r"\s+(?:(?:any|further|ever|again|publish|publishing|inject|injecting|"
    r"express|expressing|say|saying|write|writing|claim|claiming|"
    r"label|labeling|labelled|demand|demanding|ask|asking|"
    r"require|requiring|request|requesting|make|making|treat|treating|"
    r"the|a|an|it|as|that|them|their|owner|peer|peers|results|result|"
    r"assertions|assertion|claims|claim|for|more|additional|fresh|"
    r"independent|to|be|is|are|was|were|remains|remain)\s+){0,14}$"
)


class PublicationPolicyViolation(ValueError):
    """Private outgoing-publication rejection with a content-free decision."""

    def __init__(self, decision: dict):
        self.decision = dict(decision)
        self.code = decision["code"]
        self.rule = decision["rule"]
        super().__init__(decision["message"])


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    return value.translate(str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2010": "-", "\u2011": "-", "\u2013": "-", "\u2014": "-", "\u00a0": " "}))


def _prose(value: str) -> str:
    # Source code and inline identifiers often contain rule examples. They are
    # not an agent's prose assertion; do not classify their string literals.
    value = re.sub(r"```[\s\S]*?```|~~~[\s\S]*?~~~", " ", value)
    return re.sub(r"`[^`\n]*`", " ", value)


def _protected(sentence: str, start: int) -> bool:
    prefix = sentence[max(0, start - 240):start].rstrip(" \t\"':(")
    # A matched modal such as 'must' can be preceded by 'do not say'.
    if re.search(_PROHIBITION, prefix + " ", re.I):
        return True
    if re.search(
        r"\b(?:do not|don't|never|must not|mustn't|should not|shouldn't|"
        r"avoid|stop)\s+(?:doubt|question|dispute|challenge|reject|"
        r"demand|ask|require|request|say|write|publish|inject|express|"
        r"call|label|mark|treat)\b"
        r"(?:(?!\b(?:but|however|yet)\b)[^.!?;]){0,160}$", prefix, re.I
    ):
        return True
    # Explicit rule quotation/description, including quoted owner policy.
    return bool(re.search(
        r"\b(?:policy|rule|terms)\s+(?:forbids?|prohibits?|rejects?|"
        r"disallows?|prevents?)\b[^.!?;]{0,140}$", prefix, re.I
    ))


def check_publication(body: str, subject: str = "") -> dict:
    """Check outgoing subject/body without logging, storing, or judging truth."""
    if not isinstance(body, str) or not isinstance(subject, str):
        raise TypeError("Commons publication body and subject must be strings.")
    value = _prose(_normalize(subject + "\n" + body))
    # Each paragraph supplies antecedents (e.g. 'The peer shipped it. I doubt
    # that result.') while a prohibition protects only its own sentence.
    for paragraph in re.split(r"\n\s*\n", value):
        sentences = re.split(r"[.!?;](?:\s+|$)|[\r\n]+", paragraph)
        for index, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
            context = " ".join(sentences[max(0, index - 1):index + 1])
            for rule in _RULES:
                if rule["target"] and not re.search(_TARGET, context, re.I):
                    continue
                if rule["favorable"] and not re.search(_FAVORABLE, context, re.I):
                    continue
                for pattern in rule["patterns"]:
                    for match in re.finditer(pattern, sentence, re.I):
                        if _protected(sentence, match.start()):
                            continue
                        return {"allowed": False, "code": "commons_publication_terms", "message": _REWRITE, "rule": rule["name"]}
    return {"allowed": True, "code": "allowed", "message": "", "rule": None}


def require_publication(body: str, subject: str = "") -> dict:
    """Return the allowed decision or raise a private, content-free rejection."""
    decision = check_publication(body, subject)
    if not decision["allowed"]:
        raise PublicationPolicyViolation(decision)
    return decision
