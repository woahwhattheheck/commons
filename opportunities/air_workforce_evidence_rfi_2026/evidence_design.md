# Evidence-design appendix — draft for partner/owner validation

## Researchable concept

**Evidence-Bound Career Navigation Agent Study**: pair a workforce-delivery organization with a bounded AI assistant that helps participants prepare questions, interpret labor-market/training information, plan next actions, and surface uncertainty to a human coach. The AI should not make eligibility, hiring, benefits, placement, or adverse decisions. A delivery partner owns participant recruitment, coaching/service policy, referrals, and real-world outcome evidence; the technical seam supplies controlled workflows, deterministic receipts, evaluation instrumentation, and failure/replay checks.

This is a **concept**, not a claim that such a workforce deployment already exists.

## Candidate learning questions

1. Which participant tasks benefit from AI assistance versus ordinary human coaching or static resources?
2. Does AI assistance improve completion of owner-defined career-navigation actions without increasing erroneous or unsafe recommendations?
3. Which subgroups experience different usefulness, error, escalation, or abandonment rates?
4. How do workers and coaches change their use of the tool over time, and which contextual conditions explain variation?
5. Which guardrails—source grounding, human review, abstention, structured escalation, or constrained tools—best reduce consequential errors while preserving usefulness?

## Outcomes and comparison options

A partner must select outcomes it actually measures. Candidate outcomes include completion of coaching milestones, training enrollment/completion, verified applications or interviews, job entry, time to placement, retention, wage progression, and participant-reported usefulness/trust. Do not manufacture metrics merely to satisfy the RFI.

Preferred evaluation options, in descending strength where feasible:
- randomized encouragement or participant-level assignment when ethical/operationally feasible;
- stepped-wedge rollout across sites/cohorts;
- matched comparison or interrupted time-series when randomization is infeasible;
- formative usability/safety study for an early prototype before outcome claims.

AIR or another independent evaluator should pre-specify the estimand, inclusion criteria, missing-data handling, subgroup analysis, and stopping/escalation rules before confirmatory analysis.

## Instrumentation

Log only what is required to answer agreed learning questions: opaque participant/session IDs; intervention/control assignment; model/tool version; source/evidence references; user intent category; assistant action class; human override/escalation; latency/error state; downstream milestone events supplied by the partner; and consent/withdrawal state. Bind immutable event IDs, canonical timestamps, model/policy versions, and receipt digests so retries and duplicate ingestion do not become extra observations.

Never treat model-generated text as ground truth about employment outcomes.

## Worker and coach voice

Co-design the task taxonomy, escalation rules, explanations, burden measures, and unacceptable-error classes with workers/learners and front-line coaches before the main study. Maintain structured feedback channels during the study and document which changes are made because of participant/staff feedback. Compensation, consent, accessibility, language access, and community governance are partner/owner decisions that must be resolved explicitly.

## Responsible AI

- **Fairness/bias:** pre-specify subgroup slices and error/usefulness metrics; investigate differential escalation, refusals, hallucination, and outcome patterns rather than assuming parity.
- **Transparency:** tell participants when AI is involved, what it can/cannot do, when a human reviews output, and where source information comes from.
- **Privacy:** minimize fields, separate participant identity from research telemetry, use retention limits, and prohibit free-form sensitive-data capture unless an approved protocol requires it.
- **Governance:** version models/prompts/tools/policies; retain human authority for consequential decisions; require incident review and change control.
- **Safety:** abstain/escalate on low-confidence or high-consequence requests; do not automate eligibility, hiring, benefits denial, or other adverse decisions.

## Failure modes to measure

Hallucinated job/training facts; stale labor-market data; unsafe benefit or legal guidance; proxy discrimination; accessibility failures; language-quality gaps; prompt injection/data exfiltration; overreliance/automation bias; inconsistent retry behavior; duplicate tool effects; loss of provenance; participant disengagement; coach workload transfer rather than reduction; and measurement artifacts caused by model/version changes.

## Evidence-to-action plan

Use interim safety/implementation reviews for fast operational learning while reserving outcome claims for pre-specified analyses. Publish negative and heterogeneous results, model/policy version changes, implementation failures, and boundary conditions—not only positive averages. The useful field artifact should be a reproducible study protocol, instrument/event schema, guardrail taxonomy, and transparent evidence receipt that another workforce system can inspect.
