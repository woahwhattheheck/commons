"""One ordinal maturity scale, with evidence-kind caps (UIOWA-021).

PROPOSED FRAMEWORK. These anchors are ours, drafted for RFQ 18649 preparation.
They are not a University finding, not an industry standard, and not a
certification scale.

The problem this is built against: a maturity scale scored by counting evidence
rewards whoever has the most documents. A team with ten written policies and no
practice outscores a team that does the work and writes little down, which is
the opposite of the truth. So the scale is bounded by the KIND of evidence, not
its volume:

    policy documents only          -> cannot exceed level 2
    a single observed instance     -> cannot exceed level 3
    repeated instances             -> level 4 available
    outcome measurement            -> level 5 available

Volume never buys a cap. Ten policies are still zero instances of practice, and
the evaluator says so by name, returning the cap that bound the result and the
specific evidence that would lift it.

Four states are kept apart, because the order requires it and because they mean
different things:

    repeatable practice   the practice runs and keeps running
    policy-only claim     it is written down; nothing shows it happening
    isolated success      it happened once; nothing shows it repeating
    missing evidence      we have nothing, which is not the same as a low level

`maturity_rank` is None for unassessed and not-applicable, so nothing can sort
them onto the bottom of the scale. Emits the field names UIOWA-022's rating
model declares as its inputs.

Python 3 standard library only.
"""

from __future__ import annotations

import json

# --------------------------------------------------------------------------
# The scale
# --------------------------------------------------------------------------
LEVELS = (
    {
        "rank": 1,
        "key": "ABSENT",
        "label": "Absent",
        "measures": "Whether the practice happens at all.",
        "observable_anchors": (
            "No procedure, written or understood, governs how this is done.",
            "People describe what they personally do; descriptions do not agree.",
            "No record exists that the activity took place.",
        ),
        "to_reach_next": "A description of the intended practice that more than one person "
                         "recognises, written or not.",
    },
    {
        "rank": 2,
        "key": "DEFINED_ON_PAPER",
        "label": "Defined on paper",
        "measures": "Whether an intended practice exists and is stated. NOT whether it happens.",
        "observable_anchors": (
            "A procedure exists and can be produced on request.",
            "People can say what the procedure requires.",
            "No evidence yet shows the procedure being followed in real work.",
        ),
        "to_reach_next": "At least one real instance of the practice being followed, with a "
                         "record that is not the procedure document itself.",
    },
    {
        "rank": 3,
        "key": "PRACTISED",
        "label": "Practised",
        "measures": "Whether the practice has actually been carried out.",
        "observable_anchors": (
            "At least one real instance is evidenced by a record of the work, not by the "
            "procedure that asks for it.",
            "The instance can be followed from request to completion.",
            "Nothing yet shows the practice holding across time, people or services.",
        ),
        "to_reach_next": "Repeated instances across a stated window, covering more than one "
                         "person or service, with exceptions visible rather than absent.",
    },
    {
        "rank": 4,
        "key": "REPEATABLE",
        "label": "Repeatable",
        "measures": "Whether the practice holds up when the particular people change.",
        "observable_anchors": (
            "Multiple instances across a stated observation window.",
            "More than one person or service is covered, so the practice is not one "
            "individual's habit.",
            "Departures from the procedure are recorded as exceptions rather than being "
            "invisible.",
        ),
        "to_reach_next": "A measure of whether the practice achieves what it is for, with its "
                         "definition, period and denominator stated.",
    },
    {
        "rank": 5,
        "key": "MEASURED",
        "label": "Measured and adjusted",
        "measures": "Whether the practice is known to work, and is changed when it does not.",
        "observable_anchors": (
            "An outcome measure exists with a stated definition, period and denominator.",
            "The measure has been reviewed, and at least one change followed from what it "
            "showed.",
            "The change itself is evidenced, not only proposed.",
        ),
        "to_reach_next": "This is the top of the scale. It is not a destination every practice "
                         "should reach; cost has to justify it.",
    },
)

LEVEL_BY_RANK = {level["rank"]: level for level in LEVELS}
LEVEL_BY_KEY = {level["key"]: level for level in LEVELS}
MAX_RANK = max(level["rank"] for level in LEVELS)

# Not positions on the scale. Different questions, no rank.
NON_RANK_STATUSES = {
    "unassessed": "Outside the agreed scope for this criterion. Not a level.",
    "not_applicable": "This practice does not apply to how the group operates. Nothing is "
                      "missing.",
    "insufficient_evidence": "We looked; what was supplied does not support any level.",
}

ASSESSMENT_STATUSES = ("assessed",) + tuple(NON_RANK_STATUSES)

AREAS = ("development", "security", "deployment", "ai_readiness")

# --------------------------------------------------------------------------
# Evidence kinds, and the cap each one implies
# --------------------------------------------------------------------------
EVIDENCE_KINDS = {
    "policy_document": {
        "label": "Policy or procedure document",
        "caps_at": 2,
        "why": "A document states an intention. It is not evidence that anything happened, "
               "and a second document is not evidence either.",
    },
    "single_instance": {
        "label": "Record of one instance of the work",
        "caps_at": 3,
        "why": "One instance shows the practice can happen. It does not show it repeating.",
    },
    "repeated_instances": {
        "label": "Records of repeated instances across a window",
        "caps_at": 4,
        "why": "Repetition across people or services shows the practice survives the "
               "particular individuals doing it.",
    },
    "outcome_measure": {
        "label": "Outcome measure with definition, period and denominator",
        "caps_at": 5,
        "why": "Knowing the practice runs is not knowing it works.",
    },
    "interview_statement": {
        "label": "Interview statement",
        "caps_at": 2,
        "why": "What people say the practice is tells us the intended practice. On its own it "
               "is a description, not a record of the work. It counts toward level 2 only when "
               "corroborated -- one person's account is a claim, and two accounts that "
               "disagree are evidence that no practice is defined.",
    },
}


class AnchorError(ValueError):
    """Bad input. Never silently repaired."""


def _require(mapping, key, where):
    if not isinstance(mapping, dict):
        raise AnchorError(f"{where}: expected an object, got {type(mapping).__name__}")
    if key not in mapping or mapping[key] is None:
        raise AnchorError(f"{where}: missing required field {key!r}")
    value = mapping[key]
    if isinstance(value, str) and not value.strip():
        raise AnchorError(f"{where}: {key!r} is blank. An absent input stays UNKNOWN.")
    return value


class Evidence:
    __slots__ = ("kind", "locator", "note", "instances", "covers_multiple_actors",
                 "exceptions_recorded", "measure_defined", "change_evidenced",
                 "states_intended_practice")

    def __init__(self, raw, where):
        self.kind = str(_require(raw, "kind", where))
        if self.kind not in EVIDENCE_KINDS:
            raise AnchorError(
                f"{where}: unknown evidence kind {self.kind!r}. Known kinds: "
                f"{', '.join(sorted(EVIDENCE_KINDS))}. A new kind needs a declared cap before "
                f"it can raise a level.")
        self.locator = str(_require(raw, "locator", where))
        self.note = raw.get("note", "")
        instances = raw.get("instances", 1)
        if isinstance(instances, bool) or not isinstance(instances, int) or instances < 1:
            raise AnchorError(f"{where}: 'instances' must be a whole number of 1 or more")
        self.instances = instances
        self.covers_multiple_actors = bool(raw.get("covers_multiple_actors", False))
        self.exceptions_recorded = bool(raw.get("exceptions_recorded", False))
        self.measure_defined = bool(raw.get("measure_defined", False))
        self.change_evidenced = bool(raw.get("change_evidenced", False))
        # Level 2's anchor is that an intended practice is stated and recognised.
        # A document states one by existing. Interview statements only do so when
        # they agree with each other -- two people describing different practices
        # is evidence that no practice is defined, not that one is.
        self.states_intended_practice = bool(
            raw.get("states_intended_practice",
                    self.kind in ("policy_document", "repeated_instances",
                                  "single_instance", "outcome_measure")))

    @property
    def caps_at(self) -> int:
        return EVIDENCE_KINDS[self.kind]["caps_at"]


class Assessment:
    """One criterion's evaluated level, with the reason it is not higher."""

    __slots__ = ("criterion_id", "area", "service", "status", "rank", "label",
                 "cap_reason", "next_level_requires", "evidence", "pattern", "notes")

    def __init__(self, criterion_id, area, service, status, rank, label, cap_reason,
                 next_level_requires, evidence, pattern, notes):
        self.criterion_id = criterion_id
        self.area = area
        self.service = service
        self.status = status
        self.rank = rank
        self.label = label
        self.cap_reason = cap_reason
        self.next_level_requires = next_level_requires
        self.evidence = evidence
        self.pattern = pattern
        self.notes = notes

    def as_rating_model_input(self) -> dict:
        """The handoff to UIOWA-022, using that model's declared field names."""
        return {
            "criterion_id": self.criterion_id,
            "area": self.area,
            "service": self.service,
            "assessment_status": self.status,
            "maturity_rank": self.rank,
            "maturity_label": self.label,
            "evidence_ids": [e.locator for e in self.evidence],
        }

    def as_dict(self) -> dict:
        out = self.as_rating_model_input()
        out.update({
            "evidence_pattern": self.pattern,
            "cap_reason": self.cap_reason,
            "next_level_requires": self.next_level_requires,
            "notes": self.notes,
        })
        return out


# --------------------------------------------------------------------------
# The evaluator
# --------------------------------------------------------------------------
def _why_not_next(wanted: int, evidence: list, capping_kind: str) -> str:
    """Name the specific missing anchor, not just 'insufficient'."""
    if wanted == 2:
        return ("no evidence states an intended practice that more than one person recognises; "
                "the descriptions supplied do not agree with each other")
    if wanted == 3:
        return (f"the intended practice is stated, but nothing records the work itself. The "
                f"strongest evidence supplied is "
                f"{EVIDENCE_KINDS[capping_kind]['label'].lower()}. "
                f"{EVIDENCE_KINDS[capping_kind]['why']}")
    if wanted == 4:
        repeated = [e for e in evidence
                    if e.kind in ("repeated_instances", "outcome_measure")]
        if not repeated:
            return ("one instance is evidenced; nothing shows the practice repeating across a "
                    "stated window")
        if not any(e.instances >= 2 and e.covers_multiple_actors for e in repeated):
            return ("repeated records exist but none covers more than one person or service, so "
                    "the practice cannot yet be distinguished from one individual's habit")
        return ("repetition is evidenced but no departures from the procedure are recorded "
                "anywhere; a process with no visible exceptions is usually one whose exceptions "
                "are not being written down")
    if wanted == 5:
        measures = [e for e in evidence if e.kind == "outcome_measure"]
        if not measures:
            return "no outcome measure is supplied; knowing the practice runs is not knowing it works"
        if not any(e.measure_defined for e in measures):
            return ("an outcome measure is cited but its definition, period or denominator is "
                    "not given, so it cannot be read")
        return ("the measure exists and is defined, but no change is evidenced as following "
                "from it; measuring is not adjusting")
    return ""



def classify_pattern(evidence: list) -> str:
    """Which of the four things the order asks us to keep apart this is."""
    if not evidence:
        return "missing_evidence"
    kinds = {e.kind for e in evidence}
    practice_kinds = {"single_instance", "repeated_instances", "outcome_measure"}
    if not (kinds & practice_kinds):
        return "policy_only_claim"
    total_instances = sum(e.instances for e in evidence if e.kind in practice_kinds)
    repeated = any(e.kind in ("repeated_instances", "outcome_measure") for e in evidence)
    if repeated or total_instances > 1:
        return "repeatable_practice"
    return "isolated_success"


def evaluate(raw: dict, where: str = "criterion") -> Assessment:
    criterion_id = str(_require(raw, "criterion_id", where))
    area = str(_require(raw, "area", where))
    if area not in AREAS:
        raise AnchorError(f"{where}: area {area!r} is not one of {', '.join(AREAS)}")
    service = str(_require(raw, "service", where))

    status = str(raw.get("assessment_status", "assessed"))
    if status not in ASSESSMENT_STATUSES:
        raise AnchorError(
            f"{where}: assessment_status {status!r} must be one of "
            f"{', '.join(ASSESSMENT_STATUSES)}")

    evidence = [Evidence(e, f"{where}.evidence[{i}]")
                for i, e in enumerate(raw.get("evidence", []) or [])]

    # Not-a-level states: no rank, and they must not carry a level.
    if status != "assessed":
        if status == "not_applicable" and not str(raw.get("applicability_reason", "")).strip():
            raise AnchorError(
                f"{where}: 'not_applicable' needs an applicability_reason. Without one it is "
                f"indistinguishable from an area nobody looked at.")
        if status == "not_applicable" and evidence:
            raise AnchorError(
                f"{where}: marked not_applicable but carries evidence. If evidence exists, the "
                f"practice applies.")
        return Assessment(criterion_id, area, service, status, None,
                          NON_RANK_STATUSES[status], "not on the scale", "",
                          evidence, status, raw.get("notes", ""))

    if not evidence:
        # Assessed with nothing behind it is not level 1; it is no level at all.
        return Assessment(criterion_id, area, service, "insufficient_evidence", None,
                          NON_RANK_STATUSES["insufficient_evidence"],
                          "no evidence was supplied, so no level is supportable",
                          "Any record of the intended practice or of the work itself.",
                          evidence, "missing_evidence", raw.get("notes", ""))

    pattern = classify_pattern(evidence)

    # Two separate questions, and conflating them was a real bug worth naming:
    #   (a) which level's anchors does the evidence actually SATISFY?
    #   (b) what ceiling does the KIND of evidence impose?
    # The answer is the lower of the two. Holding a policy document does not
    # put a team at level 2; it means they cannot be above it.
    def supports(rank_wanted: int) -> bool:
        if rank_wanted == 1:
            return True
        if rank_wanted == 2:
            return any(e.states_intended_practice for e in evidence)
        if rank_wanted == 3:
            return any(e.kind in ("single_instance", "repeated_instances", "outcome_measure")
                       for e in evidence)
        if rank_wanted == 4:
            return any(e.kind in ("repeated_instances", "outcome_measure")
                       and e.instances >= 2 and e.covers_multiple_actors
                       for e in evidence) and any(e.exceptions_recorded for e in evidence)
        if rank_wanted == 5:
            return any(e.kind == "outcome_measure" and e.measure_defined for e in evidence) \
                and any(e.change_evidenced for e in evidence)
        return False

    satisfied = 1
    for candidate in range(1, MAX_RANK + 1):
        if supports(candidate):
            satisfied = candidate
        else:
            break

    cap = max(e.caps_at for e in evidence)
    capping_kind = max(evidence, key=lambda e: e.caps_at).kind
    rank = min(satisfied, cap)

    if cap < satisfied:
        cap_reason = (f"anchors up to level {satisfied} are evidenced, but the strongest "
                      f"evidence supplied is {EVIDENCE_KINDS[capping_kind]['label'].lower()}, "
                      f"which caps this at level {cap}. "
                      f"{EVIDENCE_KINDS[capping_kind]['why']}")
    elif rank >= MAX_RANK:
        cap_reason = "top of the scale; every anchor is evidenced"
    else:
        cap_reason = _why_not_next(rank + 1, evidence, capping_kind)

    level = LEVEL_BY_RANK[rank]
    return Assessment(criterion_id, area, service, "assessed", rank, level["label"],
                      cap_reason, level["to_reach_next"], evidence, pattern,
                      raw.get("notes", ""))


def evaluate_all(raw_list, where="criteria") -> list:
    seen = set()
    out = []
    for i, raw in enumerate(raw_list):
        a = evaluate(raw, f"{where}[{i}]")
        if a.criterion_id in seen:
            raise AnchorError(f"{where}[{i}]: duplicate criterion_id {a.criterion_id!r}")
        seen.add(a.criterion_id)
        out.append(a)
    return out


def load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError as exc:
            raise AnchorError(f"{path}: not valid JSON ({exc})") from exc
