"""The integration decision worksheet.

A fixed question set per candidate workflow, and a deterministic reading of the
answers into a pattern fit. Every verdict names the question that produced it, so a
reviewer can disagree with the ANSWER rather than with the tool.

The rule that makes this honest: a question that is DECISIVE for a pattern and is
left UNKNOWN produces the verdict UNDETERMINED for that pattern, naming the blocking
question. It does not default to supported, and UNDETERMINED never outranks a real
verdict. Absent evidence is a reason to go and get the evidence, not a pass.
"""

import csv
import io
import json

from patterns import PATTERNS, PATTERN_ORDER
from unknowns import UNKNOWN, coerce, is_unknown, render

# --------------------------------------------------------------- question set

QUESTIONS = (
    {"id": "answer_useful_within", "type": "enum",
     "options": ("only_in_session", "minutes", "hours", "days"),
     "text": "How soon must the answer be available to still be useful?"},
    {"id": "consequential", "type": "bool",
     "text": "Can the output cause an effect that is hard to reverse, or that a named "
             "person would be accountable for?"},
    {"id": "degraded_answer_exists", "type": "bool",
     "text": "Is there a DEFINED, usable answer for this workflow when the capability "
             "is unavailable? (a fallback that has never been exercised is UNKNOWN)"},
    {"id": "peak_items_per_hour", "type": "number",
     "text": "Peak inbound items per hour for this workflow."},
    {"id": "reviewer_capacity_items_per_hour", "type": "number",
     "text": "Reviewer capacity in items per hour, MEASURED on reviewing drafts (not "
             "inferred from the unaided process)."},
    {"id": "staged_copies_permitted", "type": "bool",
     "text": "May this content be copied into an internal queue, result store and "
             "dead-letter queue, under its own handling terms?"},
    {"id": "durable_queue_available", "type": "bool",
     "text": "Does durable queue infrastructure with an OWNED and monitored "
             "dead-letter path already exist?"},
    {"id": "single_owner_for_deadline_and_fallback", "type": "bool",
     "text": "Is there one named owner for the request deadline AND the degraded "
             "answer?"},
    {"id": "payload_contains_restricted_content", "type": "bool",
     "text": "Does the payload contain content whose handling terms restrict crossing "
             "an external boundary?"},
    {"id": "baseline_measured", "type": "bool",
     "text": "Has the non-AI baseline been measured on the same items, so benefit can "
             "be stated as a difference?"},
)

QUESTION_BY_ID = {q["id"]: q for q in QUESTIONS}

DISQUALIFY, CAUTION, SUPPORT = "DISQUALIFY", "CAUTION", "SUPPORT"

# rule = (question_id, predicate, verdict, reason, decisive)
# decisive=True means: if this answer is UNKNOWN, the pattern cannot be judged.
RULES = {
    "A_SYNCHRONOUS_IN_REQUEST": (
        ("answer_useful_within", lambda v: v == "only_in_session", SUPPORT,
         "the answer is only useful inside the session, which is what this pattern is for",
         True),
        ("answer_useful_within", lambda v: v in ("hours", "days"), DISQUALIFY,
         "the answer is not needed in-session, so holding a user request open buys "
         "nothing and costs availability", True),
        ("degraded_answer_exists", lambda v: v is False, DISQUALIFY,
         "no defined degraded answer: workflow availability would be capped at "
         "capability availability with no floor", True),
        ("single_owner_for_deadline_and_fallback", lambda v: v is False, CAUTION,
         "deadline and fallback are unowned; this is the split-ownership failure this "
         "pattern is most exposed to", False),
        ("consequential", lambda v: v is True, CAUTION,
         "consequential output with no review step; consider composing with pattern C",
         False),
        ("payload_contains_restricted_content", lambda v: v is True, CAUTION,
         "live records cross the boundary at full fidelity in this pattern", False),
    ),
    "B_ASYNCHRONOUS_QUEUED_BATCH": (
        ("answer_useful_within", lambda v: v == "only_in_session", DISQUALIFY,
         "the answer is only useful inside the session; out-of-band completion cannot "
         "serve it", True),
        ("answer_useful_within", lambda v: v in ("hours", "days"), SUPPORT,
         "completion-time commitment fits comfortably", True),
        ("staged_copies_permitted", lambda v: v is False, DISQUALIFY,
         "the pattern necessarily creates staged copies (queue, result store, "
         "dead-letter) and those are not permitted for this content", True),
        ("durable_queue_available", lambda v: v is False, CAUTION,
         "no existing durable queue with an owned dead-letter path; first-integration "
         "effort is at the top of the range and ongoing operations are a new burden",
         False),
        ("peak_items_per_hour", lambda v: isinstance(v, (int, float)) and v >= 200,
         SUPPORT, "volume is high enough that throughput, not per-item latency, is the "
         "right thing to optimize", False),
    ),
    "C_HUMAN_IN_THE_LOOP_REVIEW": (
        ("consequential", lambda v: v is True, SUPPORT,
         "the action is consequential, which is the condition this pattern exists for",
         True),
        ("consequential", lambda v: v is False, CAUTION,
         "low-stakes reversible output; a review step may cost more than the errors it "
         "prevents", True),
        ("reviewer_capacity_items_per_hour", lambda v: v == "__OVERRUN__", DISQUALIFY,
         "peak volume exceeds measured reviewer capacity, so the review step would "
         "become a rubber stamp -- worse than no review, because it manufactures the "
         "appearance of oversight", True),
        ("baseline_measured", lambda v: v is False, CAUTION,
         "no measured unassisted-reviewer baseline, so any benefit claim from this "
         "pattern would be unfalsifiable", False),
    ),
}

DECISIVE_BY_PATTERN = {
    pattern_id: sorted({r[0] for r in rules if r[4]})
    for pattern_id, rules in RULES.items()
}


def _normalize(answers):
    """Coerce raw answers, validate enums, and flag anything outside the question set."""
    clean, invalid = {}, []
    for question in QUESTIONS:
        value = coerce(answers.get(question["id"], UNKNOWN))
        if not is_unknown(value):
            if question["type"] == "enum" and value not in question["options"]:
                invalid.append(f"{question['id']}={value!r} not in {question['options']}")
                value = UNKNOWN
            elif question["type"] == "bool" and not isinstance(value, bool):
                invalid.append(f"{question['id']}={value!r} is not a boolean")
                value = UNKNOWN
            elif question["type"] == "number" and not isinstance(value, (int, float)):
                invalid.append(f"{question['id']}={value!r} is not a number")
                value = UNKNOWN
        clean[question["id"]] = value
    unexpected = sorted(set(answers) - set(QUESTION_BY_ID))
    return clean, invalid, unexpected


def _capacity_flag(answers):
    """Derived answer: does peak volume exceed measured reviewer capacity?

    Returns True / False / UNKNOWN. Both inputs must be known -- a missing capacity
    figure does NOT become 'capacity is fine'.
    """
    peak = answers["peak_items_per_hour"]
    capacity = answers["reviewer_capacity_items_per_hour"]
    if is_unknown(peak) or is_unknown(capacity):
        return UNKNOWN
    return peak > capacity


def evaluate(workflow):
    """Read one worksheet into a per-pattern verdict with named reasons."""
    answers, invalid, unexpected = _normalize(workflow.get("answers", {}))
    overrun = _capacity_flag(answers)
    unanswered = sorted(k for k, v in answers.items() if is_unknown(v))

    results = {}
    for pattern_id in PATTERN_ORDER:
        supports, cautions, disqualifiers, blocked_by = [], [], [], []

        for question_id, predicate, verdict, reason, decisive in RULES[pattern_id]:
            if question_id == "reviewer_capacity_items_per_hour":
                # derived rule: needs both peak and capacity
                if is_unknown(overrun):
                    if decisive:
                        blocked_by.append("reviewer_capacity_items_per_hour + "
                                          "peak_items_per_hour")
                    continue
                fired = predicate("__OVERRUN__") if overrun else False
            else:
                value = answers[question_id]
                if is_unknown(value):
                    if decisive:
                        blocked_by.append(question_id)
                    continue
                fired = predicate(value)

            if not fired:
                continue
            entry = {"question": question_id, "reason": reason}
            if verdict == SUPPORT:
                supports.append(entry)
            elif verdict == CAUTION:
                cautions.append(entry)
            else:
                disqualifiers.append(entry)

        if disqualifiers:
            fit = "DISQUALIFIED"
        elif blocked_by:
            fit = "UNDETERMINED"
        elif cautions:
            fit = "SUPPORTED_WITH_CAUTIONS"
        elif supports:
            fit = "SUPPORTED"
        else:
            fit = "NO_SIGNAL"

        results[pattern_id] = {
            "pattern_id": pattern_id,
            "name": PATTERNS[pattern_id]["name"],
            "fit": fit,
            "supports": supports,
            "cautions": cautions,
            "disqualifiers": disqualifiers,
            "blocked_by_unknown": sorted(set(blocked_by)),
            "decisive_questions": DECISIVE_BY_PATTERN[pattern_id],
        }

    live = [p for p in PATTERN_ORDER
            if results[p]["fit"] in ("SUPPORTED", "SUPPORTED_WITH_CAUTIONS",
                                     "UNDETERMINED")]
    pattern_evidence = []
    for pattern_id in live:
        for item in PATTERNS[pattern_id]["unresolved_evidence"]:
            pattern_evidence.append({"pattern_id": pattern_id, "item": item})

    return {
        "workflow_id": workflow.get("workflow_id", "(unnamed)"),
        "workflow_name": workflow.get("name", "(unnamed)"),
        "fiction_label": workflow.get("fiction_label", "FICTIONAL"),
        "answers": {k: render(v) for k, v in answers.items()},
        "unanswered_questions": unanswered,
        "invalid_answers_discarded": invalid,
        "unexpected_answer_keys_ignored": unexpected,
        "derived_review_capacity_overrun": render(overrun),
        "patterns": results,
        "patterns_still_live": live,
        "unresolved_evidence": pattern_evidence,
    }


# ------------------------------------------------------------------ rendering

FIT_ORDER = {"SUPPORTED": 0, "SUPPORTED_WITH_CAUTIONS": 1, "UNDETERMINED": 2,
             "NO_SIGNAL": 3, "DISQUALIFIED": 4}


def render_worksheet_markdown(evaluations):
    out = ["# Integration decision worksheet", "",
           "One worksheet per candidate workflow. Every verdict below names the "
           "question that produced it.", "",
           "**Reading the verdicts.** `SUPPORTED` / `SUPPORTED_WITH_CAUTIONS` are "
           "real readings. `DISQUALIFIED` means a hard condition failed. "
           "`UNDETERMINED` means a question that is *decisive* for that pattern has "
           "no answer yet -- it is not a soft yes, it is a instruction to go get the "
           "evidence. `NO_SIGNAL` means nothing in the answers speaks to it either "
           "way.", "",
           "## Question set", ""]
    for question in QUESTIONS:
        out.append(f"- **`{question['id']}`** ({question['type']}) - {question['text']}")
    out.append("")
    for evaluation in evaluations:
        out += [f"## {evaluation['workflow_name']}  "
                f"(`{evaluation['workflow_id']}` - {evaluation['fiction_label']})", "",
                "| Question | Answer |", "|---|---|"]
        for question in QUESTIONS:
            out.append(f"| `{question['id']}` | {evaluation['answers'][question['id']]} |")
        out += ["", f"Derived: peak volume exceeds measured reviewer capacity -> "
                    f"**{evaluation['derived_review_capacity_overrun']}**", "",
                "| Pattern | Fit | Why |", "|---|---|---|"]
        ordered = sorted(PATTERN_ORDER,
                         key=lambda p: FIT_ORDER[evaluation["patterns"][p]["fit"]])
        for pattern_id in ordered:
            result = evaluation["patterns"][pattern_id]
            bits = []
            for entry in result["disqualifiers"]:
                bits.append(f"DISQUALIFY via `{entry['question']}`: {entry['reason']}")
            for question_id in result["blocked_by_unknown"]:
                bits.append(f"blocked: decisive question `{question_id}` is UNKNOWN")
            for entry in result["supports"]:
                bits.append(f"supports via `{entry['question']}`: {entry['reason']}")
            for entry in result["cautions"]:
                bits.append(f"caution via `{entry['question']}`: {entry['reason']}")
            out.append(f"| {result['name']} | `{result['fit']}` | " +
                       ("; ".join(bits) if bits else "no rule fired") + " |")
        out.append("")
        if evaluation["unanswered_questions"]:
            out += ["**Unanswered worksheet questions (UNKNOWN, not zero):**", ""]
            for question_id in evaluation["unanswered_questions"]:
                out.append(f"- `{question_id}` - {QUESTION_BY_ID[question_id]['text']}")
            out.append("")
        if evaluation["invalid_answers_discarded"]:
            out += ["**Malformed answers discarded (treated as UNKNOWN, never as a "
                    "default):**", ""]
            for item in evaluation["invalid_answers_discarded"]:
                out.append(f"- {item}")
            out.append("")
        if evaluation["unresolved_evidence"]:
            out += ["**Unresolved evidence carried from the patterns still in play:**", ""]
            for entry in evaluation["unresolved_evidence"]:
                out.append(f"- ({entry['pattern_id']}) {entry['item']}")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_worksheet_csv(evaluations):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["workflow_id", "workflow_name", "fiction_label", "pattern_id",
                     "fit", "disqualifier_count", "caution_count", "support_count",
                     "blocked_by_unknown", "decisive_questions"])
    for evaluation in evaluations:
        for pattern_id in PATTERN_ORDER:
            result = evaluation["patterns"][pattern_id]
            writer.writerow([
                evaluation["workflow_id"], evaluation["workflow_name"],
                evaluation["fiction_label"], pattern_id, result["fit"],
                len(result["disqualifiers"]), len(result["cautions"]),
                len(result["supports"]),
                "|".join(result["blocked_by_unknown"]) or "",
                "|".join(result["decisive_questions"]),
            ])
    return buffer.getvalue()


def load_workflows(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)["workflows"]
