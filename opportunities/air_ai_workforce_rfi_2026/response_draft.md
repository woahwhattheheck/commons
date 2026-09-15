# Prompt-aligned AIR RFI response draft

This is an owner-review draft, not a submission. Bracketed fields require private evidence. The default route is **partner-led** until a track-record-bearing workforce delivery relationship is evidenced.

## 1. Project Title

**Evidence-Bound AI Career Navigation & Readiness Lab**

## 2. Contact Information

`[OWNER PRIVATE INPUT: name, title, organization, email, phone]`

Do not commit personal contact details to this repository.

## 3. Organizational Background — max 200 words

`[OWNER: insert supportable legal/public organization background.]`

Suggested bounded positioning: the technology contributor builds auditable AI/agent workflows and evaluation infrastructure emphasizing reproducibility, evidence provenance, human review, and fail-closed handling of conflicting or stale evidence. **Do not** describe that engineering record as an established workforce-development delivery history unless direct evidence exists.

For the recommended partner route, add: `[PARTNER: actual workforce organization, served populations, years/contexts of delivery, and evidence references.]`

## 4. Overview of AI-Enabled Workforce Innovation — max 300 words

We propose an **Evidence-Bound AI Career Navigation & Readiness Lab** operated with an experienced workforce-delivery partner. The intervention would add human-supervised AI assistance to bounded career-navigation and readiness tasks—for example translating a worker's stated goals into an action plan, identifying relevant training or job-search steps, rehearsing interviews, and surfacing evidence-linked labor-market or program information.

The differentiator is not “AI gives advice.” The system is instrumented as an evaluation surface. Each material model/prompt/configuration version is recorded; recommendations can carry provenance and uncertainty; replay/conflict checks make changed outputs observable; human staff can accept, revise, or reject suggestions; and evaluator-facing logs separate model behavior from staff and participant decisions.

The workforce partner would own recruitment, service delivery, participant relationships, and any high-stakes decision. The technology layer would not autonomously apply for jobs, rank applicants, determine eligibility, or make benefit/employment decisions. AIR could study where the tool helps, where staff override it, how effects vary across populations, and which implementation conditions make AI support useful rather than burdensome.

`[OWNER/PARTNER: bind the exact 2027–2028 setting and maturity level before use.]`

## 5. Workforce Challenge — max 200 words

Career-navigation and readiness services often require staff and workers to synthesize fragmented information, convert goals into practical next steps, and revisit plans as circumstances change. Generative AI may reduce some search/drafting burden, but unmeasured use can introduce inaccurate guidance, uneven quality across groups, opaque model changes, and extra verification work for staff.

The proposed project asks a narrower question: **can a human-supervised, auditable AI layer improve the timeliness and usefulness of career-navigation/readiness support without increasing material error or inequity?**

`[PARTNER: add the concrete service bottleneck, current workflow, population, and baseline only from evidence.]`

## 6. Key Learning Questions — max 200 words

1. Does the intervention improve completion and quality of bounded career-readiness/navigation tasks relative to the partner's existing service approach?
2. Does it change staff time, rework, escalation, or override rates?
3. Where do factual error, unsupported recommendation, or uncertainty rates differ by task and participant subgroup?
4. Which worker/staff interaction patterns predict helpful versus rejected AI support?
5. Do near-term improvements translate into downstream outcomes the partner already lawfully measures, such as training progression, verified referrals, placement, time-to-placement, or retention?
6. Which model, prompt, data, and human-oversight changes materially alter those results?

The confirmatory outcome set and comparison design should be finalized with AIR before analysis.

## 7. Population(s) of Focus — max 100 words

`[PARTNER REQUIRED: name the specific youth/adult population, geography/service context, eligibility or service definition, and expected 2027–2028 participant count. Do not infer a population from market size.]`

## 8. Technical Approach, Models, and Data — max 300 words

The proposed technology contribution is model-agnostic and evaluation-first. A bounded orchestration layer records the model/version/configuration used for each evaluated interaction, links outputs to the evidence available at the time, captures human accept/revise/reject actions, and creates reproducible event receipts for analysis. Candidate models can be compared behind the same task contract rather than silently switching behavior.

The default data posture is minimization: use opaque participant identifiers in the evaluation layer; keep direct identity/contact fields in the workforce partner's existing systems; collect only features justified by pre-specified learning questions; and separate operational data from fairness-analysis variables where practical. Model inputs should exclude sensitive fields unless they are necessary, lawful, consented, and explicitly governed.

The project would predefine failure categories such as factual error, unsupported resource claim, unsafe or discriminatory recommendation, privacy leak, overconfident uncertainty, and staff-override requirement. Human staff remain responsible for service decisions.

`[OWNER/PARTNER: identify actual models/data sources only when selected; identify any participant data and legal basis before collection.]`

## 9. Maturity Level

Default claim from repository evidence: **Concept** for this specific workforce intervention.

Upgrade to Prototype/Pilot/Deployed solution only when exact evidence supports that maturity for this workforce use case, not because component technology exists elsewhere.

## 10. Early Results or Evidence — max 200 words

**No workforce-impact results are claimed by default.** Existing engineering work supports the feasibility of deterministic receipts, replay/conflict detection, human-review states, provenance capture, and rigorous software/evaluation testing. Those are enabling capabilities, not evidence of improved worker outcomes.

`[OWNER/PARTNER: replace or extend only with supportable pilot/deployment evidence, including population, dates, comparator/baseline, sample size, outcome definition, and evidence reference.]`

## 11. Responsible AI and Safeguards — max 200 words

Safeguards are designed around bounded authority and measurement. Human staff retain all consequential service decisions. The system should log model/configuration identity, evidence provenance, uncertainty and staff override; minimize participant data; isolate direct identifiers from evaluation records; prohibit autonomous job application/ranking/eligibility decisions; test factuality and harmful-recommendation failure modes; and monitor subgroup error/helpfulness patterns.

Model or prompt changes are treated as intervention changes, not silently pooled. Worker voice is incorporated through consented feedback and qualitative inquiry, with the ability to decline AI-assisted support where operationally feasible. Escalation paths should exist for uncertain, sensitive, or contradictory outputs.

AIR and the delivery partner should jointly define the final fairness metrics, sensitive-variable handling, consent language, retention, and incident procedures before real participant data is used.

## 12. Opportunities for Partnership with AIR — max 150 words

AIR could serve as the independent evidence partner: refine the theory of change and pre-specified learning questions; select a feasible comparison design; validate measures; advise on worker-voice and responsible-AI protocols; audit implementation fidelity and model/version changes; analyze heterogeneity and failure modes; and translate findings into timely decisions for the workforce partner and broader field.

A particularly useful role would be separating product telemetry from outcome evidence so that engagement with the tool is never mistaken for impact. AIR could also help determine which findings are strong enough to generalize, which remain implementation-specific, and what evidence would justify a later scaled study.

`[PARTNER: confirm actual delivery/evaluation roles before submission.]`
