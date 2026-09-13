# Proposal carrier — CAS LLM Actuarial Benchmark RFP

**Status:** engineering draft / do not submit until named actuarial SME and qualifications are confirmed.  
**RFP:** https://www.casact.org/2026-ai-rfp  
**Proposal deadline:** September 28, 2026.  
**Questions deadline:** September 14, 2026.

## Proposed solution

Build a versioned, reproducible P&C actuarial perception benchmark whose ground truth is controlled by actuarial subject-matter review and whose execution is controlled by deterministic engineering contracts. Separate domain authority from model/provider plumbing so CAS can re-test future models without redesigning the benchmark.

### Workstream A — actuarial task design and ground truth

A **named, real actuarial SME collaborator is required before submission**. That person/team would own the actuarial taxonomy, task validity, ground-truth review, difficulty calibration, and interpretation of limitations. The engineering lead must not substitute model-generated rationale for actuarial authority.

Candidate task families from the RFP include claims triage/classification, underwriting judgments, policy segmentation, fraud/litigation flagging, rating-plan/regulatory perception, risk-management signals, reserving pattern recognition, and credibility sub-tasks.

### Workstream B — legally publishable dataset assembly

Use only material with explicit downstream publication rights. Maintain a provenance manifest for every dataset/task family and distinguish:

- existing open insurance benchmark material whose license permits CAS GitHub publication;
- project-authored simulations/synthetic cases reviewed by actuarial SMEs; and
- excluded data whose confidentiality, privacy, contract, or license does not permit public release.

Freeze ground truth before scored model runs. Dataset revisions mint a new benchmark version and digest rather than silently mutating historical results.

### Workstream C — benchmark harness

Provider-neutral model adapters feed one canonical scorer. The scorer computes objective metrics appropriate to each task, including accuracy/F1 for classification and calibrated metrics such as Brier score/log loss when model probabilities are available. Every result receipt records benchmark version/digest, scorer version, model identifier, run configuration, task count, category metrics, and aggregate metrics.

The executable demonstrator in this folder proves the digest binding, strict prediction contract, core metrics, and result-comparison invariant without any external API or proprietary data.

### Workstream D — model evaluation

Evaluate the current major commercial model families requested by CAS (OpenAI, Anthropic, Google) and at least three leading open-weight models. Keep prompts, decoding settings, tool permissions, retries, and model-version identifiers in run manifests. Re-runs should be batchable and should fail closed when a provider does not expose enough version/configuration information to make a result interpretable.

### Workstream E — public comparison platform

Publish an accessible comparison surface backed by immutable result receipts. Users should be able to compare overall and task-family performance, inspect benchmark/version provenance, and distinguish accuracy from calibration. New tasks or models create new signed/versioned data; the UI does not own benchmark truth.

### Workstream F — CAS handoff and maintenance

Deliver docs and scripts so CAS can add a model adapter, run a frozen benchmark, publish a new receipt, mint a new benchmark version, and retire/replace solved tasks without contractor involvement. Recommend a regular review cadence plus event-triggered re-testing after material frontier-model releases.

## Milestones

1. **Benchmark design + governance:** actuarial taxonomy, objective task definitions, provenance/license policy, acceptance criteria.
2. **Dataset alpha:** SME-reviewed publishable task set + provenance manifest + frozen alpha digest.
3. **Harness alpha:** provider adapters, deterministic scorer, run receipts, regression tests.
4. **Initial evaluation:** requested commercial families + at least three open-weight models; calibration and error analysis.
5. **Comparison platform:** public results browser with task-family/version transparency.
6. **Research report + replication pack:** methodology, limitations, executive summary, configs, maintenance runbook.
7. **CAS transfer:** repository handoff, reproducibility rehearsal, maintenance-cost estimate, presentation materials.

## Budget planning envelope — not submission-ready until collaborator quotes are real

The CAS RFP states that awards will most likely fall in the **$25,000–$65,000** range, with a **$75,000 maximum**, and requests labor separately from out-of-pocket costs. A credible proposal should stay inside that range unless the final team has a defensible reason not to.

Planning target: **$58,500 total**.

| Cost class | Planning amount | Boundary |
| --- | ---: | --- |
| Engineering/reproducibility labor | $34,000 | benchmark harness, adapters, result receipts, comparison platform, tests, handoff |
| Actuarial SME/domain labor | $17,000 | **placeholder allocation only; must be replaced by an accepted collaborator's real scope/rate before submission** |
| Model API / evaluation compute | $4,000 | pass-through estimate; final plan should cap and log spend |
| Publication/hosting/storage during project | $1,000 | pass-through estimate; CAS maintenance costs reported separately |
| Required CAS presentation travel | $2,500 | planning allowance; reconcile against actual venue/travel expectations |
| **Total** | **$58,500** | no overhead included |

No revenue is booked and no partner compensation is committed by this draft.

## Team qualifications boundary

Current outreach asks CAS whether an AI benchmarking/reliability technical lead may team with a named actuarial SME collaborator/subcontractor. Separate outreach asks Prof. Jan-Philipp Schmidt whether the ActuBench team is interested in teaming. **Neither outreach is an acceptance or partnership.** Do not put a collaborator name, actuarial credential, resume, institution, or prior work into the submitted team section without explicit participation and permission.

The technical proposal should cite only demonstrable engineering artifacts and repository history. The final submission needs truthful resumes/experience for every researcher and should disclose AI use as required by the RFP.

## Acceptance gates before proposal email

- [ ] CAS confirms teaming structure is acceptable, or the RFP is otherwise clearly read to permit it.
- [ ] Named actuarial SME/team accepts and supplies approved qualification text/resume.
- [ ] Dataset strategy has a publication-rights matrix.
- [ ] Technical demonstrator is merged and its tests are green.
- [ ] Final labor split/rates and API/compute budget are real, not placeholders.
- [ ] Travel assumption is reconciled.
- [ ] Proposal includes milestones and maintenance-cost estimate.
- [ ] No invented model results, client references, credentials, acceptance, award, or revenue.
