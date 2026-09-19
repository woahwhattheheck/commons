"""Three reference integration patterns, as structured data rather than prose.

Work order UIOWA-080. The patterns are compared on identical axes so the comparison
is real; free-text pattern write-ups usually differ in which axes they bother to
address, which is how a weak pattern looks strong.

Scope rule held throughout this file and enforced by check_vendor_neutrality():
capabilities are described by CAPABILITY CLASS and by architecture. No commercial
product is named, compared, or recommended for procurement anywhere.
"""

import re

from unknowns import UNKNOWN, render

# Closed vocabulary. Anything describing "what does the AI work" must come from here.
CAPABILITY_CLASSES = {
    "hosted-inference-api":
        "Capability operated by an external party and reached across a network "
        "boundary the institution does not control.",
    "self-operated-model":
        "Capability operated by the institution on compute it controls; the network "
        "boundary is internal.",
    "embedded-local-model":
        "Capability running inside the requesting process or on the end-user device; "
        "no inference boundary crossing at all.",
    "retrieval-augmented-composition":
        "A composite: an institution-owned retrieval step supplies context to a "
        "generation step of any of the above classes.",
    "deterministic-rules-baseline":
        "Non-AI comparison baseline. Every pattern below carries one, because a "
        "benefit claim with no baseline is not a measurement.",
    "human-expert-review":
        "A person performing or checking the judgement, treated as a capability with "
        "its own throughput, availability and cost characteristics.",
}

AXES = (
    ("summary", "What the pattern is"),
    ("interface_surface", "Interface surface"),
    ("data_movement", "Data movement"),
    ("failure_slow", "Failure behavior: capability is SLOW"),
    ("failure_unavailable", "Failure behavior: capability is UNAVAILABLE"),
    ("availability_coupling", "Availability coupling"),
    ("latency_position", "Where latency lands"),
    ("integration_ownership", "Integration ownership"),
    ("portability_note", "Portability: what a provider swap costs"),
    ("maintenance_burden", "Maintenance burden"),
    ("deterministic_baseline", "Deterministic baseline to measure against"),
    ("suitable_when", "Suitable when"),
    ("unsuitable_when", "Unsuitable when"),
    ("effort_first_integration_eng_days", "Effort: first integration (engineer-days)"),
    ("effort_each_additional_eng_days", "Effort: each additional workflow (engineer-days)"),
    ("unresolved_evidence", "Unresolved evidence"),
)

PATTERNS = {
    "A_SYNCHRONOUS_IN_REQUEST": {
        "pattern_id": "A_SYNCHRONOUS_IN_REQUEST",
        "name": "Synchronous in-request call",
        "shape": "user request -> workflow -> capability -> workflow -> user response",
        "capability_classes_that_fit": ("hosted-inference-api", "self-operated-model",
                                        "embedded-local-model"),
        "summary":
            "The capability is called inside the user's own request. The person is "
            "waiting while it runs, and the answer is part of the response they get.",
        "interface_surface":
            "Smallest of the three: one request/response call inside an existing "
            "transaction boundary. One interface to define, one to version. The "
            "hidden surface is the DEADLINE and the DEGRADED ANSWER -- both are part "
            "of the interface even though they are usually left undesigned.",
        "data_movement":
            "The live record crosses the boundary once per request, in whatever state "
            "the user submitted it. Nothing is staged, so the pattern creates no new "
            "institution-held copy -- which makes it the lightest of the three for "
            "internal data governance and the heaviest for boundary terms, because "
            "content leaves at full fidelity and at user-driven times. Required "
            "evidence: exact payload fields, retention at the far side, and whether "
            "submitted content is retained or reused.",
        "failure_slow":
            "The user's whole request slows by the capability's latency. The "
            "dangerous second-order effect is resource exhaustion: without a client "
            "deadline strictly shorter than the surrounding request timeout, in-flight "
            "requests pile up and one slow dependency becomes a full outage of the "
            "surrounding service. Control class: hard deadline + bounded concurrency "
            "+ a pre-agreed degraded answer.",
        "failure_unavailable":
            "The workflow must have a defined answer without the capability. If it "
            "does not, workflow availability is capped at capability availability. "
            "The correct degraded answer is almost never a guess -- it is the "
            "pre-AI path, or an explicit 'not classified, routed to a person'.",
        "availability_coupling":
            "HIGH. Availabilities multiply unless a fallback path exists and is "
            "exercised. A fallback that has never been run under load is UNKNOWN, "
            "not a mitigation.",
        "latency_position":
            "On the critical path, visible to the user. The capability's p99 (not its "
            "average) must fit the surrounding budget with retry headroom; one retry "
            "roughly doubles the worst case.",
        "integration_ownership":
            "Single owner: the team that owns the user-facing service owns the call, "
            "the deadline and the fallback. Split ownership here is a recurring "
            "failure: the platform team owns the capability, the product team owns "
            "the timeout, and nobody owns the degraded answer.",
        "portability_note":
            "Contained IF the call sits behind a domain-shaped port; pervasive if the "
            "wire shape and vendor error types reach the request handler, which is the "
            "default outcome when the first integration is built under deadline. "
            "Behavior portability is worse than code portability: latency "
            "distribution changes on a swap and the deadline has to be re-tuned.",
        "maintenance_burden":
            "Moderate and continuous. Deadline and concurrency tuning, and output "
            "variance that is immediately user-visible, so drift is reported as "
            "incidents rather than discovered in review.",
        "deterministic_baseline_class": "deterministic-rules-baseline",
        "deterministic_baseline":
            "deterministic-rules-baseline: the existing routing/lookup rule the "
            "workflow used before, measured on the same items.",
        "suitable_when":
            "The answer is worthless if it arrives later; the work item is small; a "
            "usable degraded answer exists; volume is compatible with per-request cost.",
        "unsuitable_when":
            "The work item is large or multi-step; volume is bursty and unbounded; the "
            "surrounding service has strict availability commitments and no fallback; "
            "the output requires a person's approval before it has effect (use C).",
        "effort_first_integration_eng_days": "5-12",
        "effort_each_additional_eng_days": "1-3",
        "unresolved_evidence": (
            "Measured p50/p95/p99 of the target capability class under the "
            "institution's own payload sizes -- UNKNOWN until run.",
            "The surrounding service's current request timeout and connection-pool "
            "limits -- UNKNOWN (institution input).",
            "Whether a usable degraded answer exists for each candidate workflow, or "
            "only in principle -- UNKNOWN until each workflow owner states it.",
        ),
        "swap_surface_profile": {
            "direct_call_sites": UNKNOWN,
            "wire_shape_reads": UNKNOWN,
            "vendor_error_handlers": UNKNOWN,
            "prompt_or_param_constructions": UNKNOWN,
            "auth_config_points": 1,
            "sdk_type_imports_outside_adapter": UNKNOWN,
            "unit_or_taxonomy_conversions_outside_adapter": UNKNOWN,
            "observability_fields_bound_to_vendor_schema": UNKNOWN,
        },
    },

    "B_ASYNCHRONOUS_QUEUED_BATCH": {
        "pattern_id": "B_ASYNCHRONOUS_QUEUED_BATCH",
        "name": "Asynchronous queued / batch processing",
        "shape": "submit -> durable queue -> worker -> capability -> result store -> read",
        "capability_classes_that_fit": ("hosted-inference-api", "self-operated-model",
                                        "retrieval-augmented-composition"),
        "summary":
            "Work is accepted and durably queued. A worker calls the capability out of "
            "band and writes results to a store. Nobody is blocked while it runs.",
        "interface_surface":
            "Larger than A: a submit interface, a durable queue contract, a result "
            "store schema, and a read interface -- four things to version instead of "
            "one. But the CAPABILITY boundary is the narrowest of the three, because "
            "exactly one component (the worker) ever touches it.",
        "data_movement":
            "Same boundary crossing as A, plus staged copies: items sit in the queue "
            "and results sit in a store, both inside the institution. That makes the "
            "internal data-governance surface the LARGEST of the three even though "
            "the external boundary is identical -- queue retention, result-store "
            "retention, dead-letter contents and backup scope all become in-scope. "
            "This inversion is routinely missed: the asynchronous pattern is assumed "
            "to be the safer one because the user is not waiting.",
        "failure_slow":
            "Not a latency incident; a throughput incident. Backlog grows silently "
            "until someone looks. The signal that matters is AGE OF OLDEST UNPROCESSED "
            "ITEM, not queue depth -- depth looks fine while the oldest item ages past "
            "the point of usefulness.",
        "failure_unavailable":
            "Nothing is lost if the queue is durable and the dead-letter path is real. "
            "The user-visible symptom is 'not finished yet' rather than an error, which "
            "is the cheapest failure mode of the three. The real risk is a silent "
            "backlog nobody is paged for, and a dead-letter queue that is written to "
            "but never read.",
        "availability_coupling":
            "LOW for correctness; the completion-time commitment is still coupled. "
            "Availability moves from 'does it work' to 'is it done in time', which is "
            "a commitment the institution can actually choose.",
        "latency_position":
            "Off the critical path. Per-item latency stops mattering; throughput and "
            "completion time start mattering, and they are affected by rate limits and "
            "concurrency caps that per-item benchmarks do not reveal.",
        "integration_ownership":
            "Naturally two owners, and that is acceptable here because the seam is "
            "explicit: a platform/data team owns queue, worker and capability "
            "boundary; the requesting workflow owns submission and result "
            "interpretation. The contract between them is the queue and result schema, "
            "which is reviewable.",
        "portability_note":
            "Best of the three. One worker touches the capability, so the swap is "
            "adapter-sized by construction, and it can be validated by replaying "
            "recorded inputs through the replacement before any cutover -- an option "
            "the synchronous pattern does not have. Reprocessing cost on a capability "
            "version change is the offsetting expense and is usually unbudgeted.",
        "maintenance_burden":
            "Highest infrastructure burden: queue operations, poison-message handling, "
            "idempotency, and an explicit reprocessing policy for when the capability "
            "version changes. Lowest behavioral burden, because output can be "
            "inspected before anyone sees it.",
        "deterministic_baseline_class": "deterministic-rules-baseline",
        "deterministic_baseline":
            "deterministic-rules-baseline applied to the same batch, scored on the "
            "same held-out items, so benefit is a difference and not an impression.",
        "suitable_when":
            "Volume is high or bursty; the work item is large; results are consumed "
            "minutes-to-hours later; backfill or reprocessing of historical items is "
            "in scope; output should be inspectable before it is used.",
        "unsuitable_when":
            "The answer is only useful inside the user's session; the institution "
            "cannot operate durable queue infrastructure; staged copies of the content "
            "are not permitted by the data's own handling terms.",
        "effort_first_integration_eng_days": "12-25",
        "effort_each_additional_eng_days": "2-5",
        "unresolved_evidence": (
            "Whether durable queue infrastructure with a monitored dead-letter path "
            "already exists and who operates it -- UNKNOWN (institution input).",
            "Acceptable completion-time commitment per candidate workflow -- UNKNOWN "
            "until the workflow owner states it; do not infer it from current runtimes.",
            "Retention terms permitted for staged copies of the queued content -- "
            "UNKNOWN and must be answered before, not after, build.",
            "Reprocessing budget when the capability version changes -- UNKNOWN.",
        ),
        "swap_surface_profile": {
            "direct_call_sites": 1,
            "wire_shape_reads": 0,
            "vendor_error_handlers": 0,
            "prompt_or_param_constructions": 1,
            "auth_config_points": 1,
            "sdk_type_imports_outside_adapter": 0,
            "unit_or_taxonomy_conversions_outside_adapter": 0,
            "observability_fields_bound_to_vendor_schema": UNKNOWN,
        },
    },

    "C_HUMAN_IN_THE_LOOP_REVIEW": {
        "pattern_id": "C_HUMAN_IN_THE_LOOP_REVIEW",
        "name": "Human-in-the-loop review step",
        "shape": "trigger -> capability draft -> review queue -> person accepts/edits/"
                 "rejects -> effect + decision record",
        "capability_classes_that_fit": ("hosted-inference-api", "self-operated-model",
                                        "retrieval-augmented-composition",
                                        "human-expert-review"),
        "summary":
            "The capability produces a draft or a suggestion that has NO effect until a "
            "person accepts it. Composes with A or B underneath; it is a different axis, "
            "not a third transport.",
        "interface_surface":
            "Largest of the three: the capability call, a review queue, a reviewer-facing "
            "surface, and a DECISION RECORD (what was proposed, what the person did, "
            "why). The decision record is the piece that is skipped under schedule "
            "pressure, and it is the only artifact that later supports evaluation, "
            "dispute handling or a defensible benefit claim.",
        "data_movement":
            "Whatever the underlying transport moves, plus a new institution-held "
            "dataset of reviewer decisions. That dataset carries its own sensitivity "
            "(it records staff judgement on specific cases) and invites a separate, "
            "frequently unasked question: whether those decisions may be reused to "
            "tune the capability, and under whose consent.",
        "failure_slow":
            "Absorbed by the review queue rather than by the user, up to the point "
            "where the queue's age commitment is breached. The binding constraint is "
            "REVIEWER THROUGHPUT, not service latency -- a capability twice as fast "
            "buys nothing if reviewers are saturated.",
        "failure_unavailable":
            "Degrades to the unaided process, IF that process still exists. The "
            "distinctive risk is organizational, not technical: the unaided path "
            "atrophies once it is unused, so the fallback quietly stops being real. "
            "Control class: exercise the unaided path on a scheduled sample, and "
            "treat inability to run it as an open finding.",
        "availability_coupling":
            "LOW technically, HIGH organizationally. The system stays correct when the "
            "capability is down and stops being correct when reviewers are unavailable, "
            "which is a different roster problem than an on-call one.",
        "latency_position":
            "Mostly in the queue wait, which is dominated by staffing, not by the "
            "capability. Optimizing the model's latency here is usually the wrong "
            "target.",
        "integration_ownership":
            "Three-way and the only pattern where that is unavoidable: engineering owns "
            "the capability and the queue, the operational unit owns reviewer capacity "
            "and calibration, and a policy owner owns what may be auto-accepted. "
            "Leaving the third role unassigned is the observed failure -- auto-accept "
            "thresholds then drift upward informally.",
        "portability_note":
            "Technically the most contained swap: the capability sits behind a review "
            "step, so nothing downstream trusts it directly. But CODE portability and "
            "WORKFLOW portability separate here, and only code portability is cheap. A "
            "swap changes what reviewers see, so reviewer calibration and accept-rate "
            "baselines reset, and any accept-rate-derived threshold must be "
            "re-established before it is trusted again.",
        "maintenance_burden":
            "Highest ongoing human burden and the lowest technical one: reviewer "
            "calibration, queue-age commitments, watching accept-rate drift, and "
            "keeping the decision record clean enough to be usable evidence.",
        "deterministic_baseline_class": "human-expert-review",
        "deterministic_baseline":
            "human-expert-review without assistance on a matched sample -- the only "
            "baseline that supports a claim about this pattern, since the comparison "
            "of interest is assisted-person versus unassisted-person, not model versus "
            "person.",
        "suitable_when":
            "The action is consequential or hard to reverse; an error has an identified "
            "person who bears it; the output is a recommendation rather than a fact; "
            "the institution needs an auditable record of why something was done.",
        "unsuitable_when":
            "Volume exceeds plausible review capacity (the queue becomes a rubber "
            "stamp, which is worse than no review because it manufactures the "
            "appearance of oversight); the decision is low-stakes and reversible; no "
            "unit will own reviewer capacity.",
        "effort_first_integration_eng_days": "18-35",
        "effort_each_additional_eng_days": "4-10",
        "unresolved_evidence": (
            "Reviewer capacity in items per person-hour for each candidate workflow -- "
            "UNKNOWN; must be measured, not estimated from the unaided process, because "
            "reviewing a draft and producing one are different tasks.",
            "Who owns the auto-accept threshold -- UNKNOWN (institution input); an "
            "unowned threshold moves informally.",
            "Whether reviewer decision records may be retained and reused, and for how "
            "long -- UNKNOWN.",
            "Whether the unaided path can still be executed today -- UNKNOWN until "
            "someone runs it.",
        ),
        "swap_surface_profile": {
            "direct_call_sites": 1,
            "wire_shape_reads": 0,
            "vendor_error_handlers": 0,
            "prompt_or_param_constructions": 2,
            "auth_config_points": 1,
            "sdk_type_imports_outside_adapter": 0,
            "unit_or_taxonomy_conversions_outside_adapter": UNKNOWN,
            "observability_fields_bound_to_vendor_schema": UNKNOWN,
        },
    },
}

PATTERN_ORDER = ("A_SYNCHRONOUS_IN_REQUEST", "B_ASYNCHRONOUS_QUEUED_BATCH",
                 "C_HUMAN_IN_THE_LOOP_REVIEW")


# ------------------------------------------------------- vendor-neutrality guard

_BRANDISH = re.compile(r"[™®]")                      # TM / (R)
_VERSIONED_NAME = re.compile(r"\b([A-Z][a-zA-Z]{2,})\s?(?:v)?\d+(?:\.\d+)+\b")
_PROCUREMENT = re.compile(
    r"\b(?:we\s+recommend\s+(?:purchasing|buying|licensing|adopting)|"
    r"recommend\s+purchas\w*|should\s+(?:purchase|buy|license|procure)|"
    r"purchase\s+a\s+licen\w+|best\s+(?:vendor|product)|"
    r"subscribe\s+to\s+[A-Z])", re.IGNORECASE)
# Our own identifiers, plus published standards/frameworks. A framework carries a
# version number and is NOT a product to procure, so "NIST AI RMF 1.0" must not
# trip the versioned-proper-noun tell. Found by test_our_own_identifiers_are_not_
# false_positives, which flagged it on the first run.
_SELF_IDENT = re.compile(
    r"\b(?:UIOWA|HRI|RFQ|OP5|SHA)[-\s]?\d|"
    r"\b(?:NIST|ISO|IEC|RMF|CSF|FIPS|SP|ANSI|IEEE)\b", re.IGNORECASE)


def check_vendor_neutrality(text, declared_capability_classes=()):
    """Heuristic guard that the deliverable stays on capability classes.

    HONEST LIMITATION, stated here and in the README: this cannot prove the absence
    of a product name, because it does not carry a vendor list -- shipping a denylist
    of real vendors into a client deliverable would itself put product names in the
    deliverable. The substantive control is the CLOSED VOCABULARY: every capability
    reference must resolve to CAPABILITY_CLASSES. This function checks that, plus
    three structural tells (trademark marks, versioned proper nouns, procurement
    phrasing). It is a tripwire, not a proof.
    """
    findings = []
    for match in _BRANDISH.finditer(text):
        findings.append({"kind": "trademark_mark", "at": match.start(),
                         "detail": "trademark/registered symbol implies a named product"})
    for match in _VERSIONED_NAME.finditer(text):
        if _SELF_IDENT.search(match.group(0)):
            continue
        findings.append({"kind": "versioned_proper_noun", "at": match.start(),
                         "detail": f"looks like a product release name: {match.group(0)!r}"})
    for match in _PROCUREMENT.finditer(text):
        findings.append({"kind": "procurement_recommendation", "at": match.start(),
                         "detail": f"procurement phrasing: {match.group(0)!r}"})
    for name in declared_capability_classes:
        if name not in CAPABILITY_CLASSES:
            findings.append({"kind": "capability_outside_vocabulary", "at": -1,
                             "detail": f"{name!r} is not a declared capability class"})
    return {"neutral": not findings, "finding_count": len(findings),
            "findings": findings,
            "limitation": "tripwire only; closed capability vocabulary is the real control"}


# ---------------------------------------------------------------- rendering

def declared_capability_classes():
    names = set()
    for pattern in PATTERNS.values():
        names.update(pattern["capability_classes_that_fit"])
        names.add(pattern["deterministic_baseline_class"])
    return sorted(names)


def render_patterns_markdown():
    out = ["# Three reference integration patterns", "",
           "Compared on identical axes. Capabilities are described by **capability "
           "class** and by architecture only -- no commercial product is named, "
           "compared, or recommended for procurement.", "",
           "## Capability classes used", ""]
    for name in sorted(CAPABILITY_CLASSES):
        out.append(f"- **`{name}`** - {CAPABILITY_CLASSES[name]}")
    out += ["", "## At a glance", "",
            "| | A: Synchronous in-request | B: Asynchronous queued/batch | "
            "C: Human-in-the-loop review |", "|---|---|---|---|"]
    quick = (
        ("Interface surface", "Smallest (1 call)", "Medium (4 contracts)",
         "Largest (+ decision record)"),
        ("External data crossing", "Per request, live record",
         "Per item, out of band", "Same as underlying transport"),
        ("Internal staged copies", "None created", "Queue + result store + DLQ",
         "+ reviewer decision record"),
        ("If capability is SLOW", "User waits; risk of pool exhaustion",
         "Backlog grows; age-of-oldest is the signal",
         "Absorbed by review queue up to its age commitment"),
        ("If capability is DOWN", "Workflow needs a degraded answer or it is down too",
         "Nothing lost if queue is durable; 'not yet' not 'error'",
         "Falls back to the unaided process, if it still exists"),
        ("Availability coupling", "HIGH", "LOW (completion time still coupled)",
         "LOW technically / HIGH organizationally"),
        ("Binding constraint", "Capability p99 latency", "Throughput and rate limits",
         "Reviewer capacity"),
        ("Swap cost", "Contained only if a port exists; usually pervasive first time",
         "Lowest; one worker, replayable validation",
         "Code cheap, workflow expensive (calibration resets)"),
        ("First integration (eng-days)", "5-12", "12-25", "18-35"),
    )
    for row in quick:
        out.append("| " + " | ".join(row) + " |")
    out.append("")
    for pattern_id in PATTERN_ORDER:
        pattern = PATTERNS[pattern_id]
        out += [f"## {pattern['name']}  (`{pattern_id}`)", "",
                f"`{pattern['shape']}`", "",
                "Capability classes that fit: " +
                ", ".join(f"`{c}`" for c in pattern["capability_classes_that_fit"]), ""]
        for key, label in AXES:
            if key == "unresolved_evidence":
                continue
            out += [f"**{label}.** {render(pattern[key])}", ""]
        out += ["**Unresolved evidence.**", ""]
        for item in pattern["unresolved_evidence"]:
            out.append(f"- {item}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"
