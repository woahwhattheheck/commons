# Feasible one-to-two-level improvement paths

**SYNTHETIC. Every profile below is an assumption set written to exercise the method.** None describes the University of Iowa's practice. No level, path or effort figure here is a University baseline, a finding, or a commitment.

## The scale this method plans against

Anchor contract from UIOWA-021 (maturity anchors) as declared in the build channel. This module consumes that scale and does not define a second one.

| level | label | reachable only with |
|---:|---|---|
| 1 | ad hoc | `outcome_measurement`, `policy_document`, `procedure_document`, `repeated_instances`, `single_observed_instance` |
| 2 | documented | `outcome_measurement`, `policy_document`, `procedure_document`, `repeated_instances`, `single_observed_instance` |
| 3 | practised | `outcome_measurement`, `repeated_instances`, `single_observed_instance` |
| 4 | consistent | `outcome_measurement`, `repeated_instances` |
| 5 | measured | `outcome_measurement` |

**The kind of evidence bounds the level, and volume cannot raise the bound.** Ten policy documents are still zero instances of practice, so they support level 2 and no more. This is what makes a target *earned* rather than claimed, and it is the mechanism that refuses an aspirational endpoint.

## Result

| verdict | paths |
|---|---:|
| `FEASIBLE` | 6 |
| `BASELINE_UNKNOWN` | 1 |
| `REFUSED_EVIDENCE_CAP` | 1 |
| `REFUSED_ASPIRATIONAL_JUMP` | 1 |
| `REFUSED_NO_OBSERVABLE` | 1 |
| `REFUSED_UNMET_PREREQUISITE` | 1 |

Assessment areas with at least one feasible path: 4 of 4.

## Feasible paths

### `PATH-SYN-SD-01` — software_development (direct)

*Profile:* `PROF-SYN-ESS-SD-01` — Peer review before merge

**Baseline (assumed): level 3 (practised)** — the strongest stated evidence is 'single_observed_instance', which supports up to level 3. This is what the ASSUMED evidence supports, not an observation of any real practice.

Evidence assumptions this rests on:

- `procedure_document` (supports to level 2) — A written standard requires peer review before merge  
  *basis:* ASSUMED for this worked example. Modelled on the kind of document an engagement would request; no such document was read.
- `single_observed_instance` (supports to level 3) — One repository shows a branch rule requiring a review  
  *basis:* ASSUMED. One repository's configuration, which is an instance and not a pattern.

**Target: level 4 (consistent)** — gain of 1

**FEASIBLE.** Level 3 (practised) to level 4 (consistent). The steps produce repeated_instances, which supports up to level 4, so the target is earned by the evidence rather than asserted.

| step | capability change | produces | to level | effort (d) | observable advancement |
|---|---|---|---:|---:|---|
| `SD-01-A` | Apply the branch rule requiring review to the remaining repositories | `repeated_instances` | 4 | 4 | Every repository in the group returns a branch-protection export showing the review requirement |
| `SD-01-B` | Record review outcomes so a month of merges can be sampled | `repeated_instances` | 4 | 3 | A one-month sample of merges each shows a recorded reviewer distinct from the author |

- **Effort:** 7 person-days across 2 of 2 steps
- **Skills:** reporting, repository administration

*Why this variant:* The practice exists in one place; the gap is consistency, so the work is making it repeat and be recorded.

### `PATH-SYN-SEC-01` — security (direct)

*Profile:* `PROF-SYN-RIS-SEC-01` — Privileged access review

**Baseline (assumed): level 2 (documented)** — the strongest stated evidence is 'policy_document', which supports up to level 2. This is what the ASSUMED evidence supports, not an observation of any real practice.

Evidence assumptions this rests on:

- `policy_document` (supports to level 2) — A published standard requires an annual privileged-access review  
  *basis:* ASSUMED. A policy stating an intent; no review record is assumed to exist.

**Target: level 3 (practised)** — gain of 1

**FEASIBLE.** Level 2 (documented) to level 3 (practised). The steps produce single_observed_instance, which supports up to level 3, so the target is earned by the evidence rather than asserted.

| step | capability change | produces | to level | effort (d) | observable advancement |
|---|---|---|---:|---:|---|
| `SEC-01-A` | Run the privileged-access review the standard already requires, and record the result | `single_observed_instance` | 3 | 5 | A dated review record exists naming the accounts reviewed and the decisions taken |

- **Effort:** 5 person-days across 1 of 1 steps
- **Skills:** identity administration

*Why this variant:* A published standard with no review record is a documented practice, not a practised one. The next level is doing it once and recording it.

### `PATH-SYN-SEC-02` — security (limited_capacity)

*Profile:* `PROF-SYN-RIS-SEC-01` — Privileged access review

**Baseline (assumed): level 2 (documented)** — the strongest stated evidence is 'policy_document', which supports up to level 2. This is what the ASSUMED evidence supports, not an observation of any real practice.

Evidence assumptions this rests on:

- `policy_document` (supports to level 2) — A published standard requires an annual privileged-access review  
  *basis:* ASSUMED. A policy stating an intent; no review record is assumed to exist.

**Target: level 3 (practised)** — gain of 1

**FEASIBLE.** Level 2 (documented) to level 3 (practised). The steps produce single_observed_instance, which supports up to level 3, so the target is earned by the evidence rather than asserted.

| step | capability change | produces | to level | effort (d) | observable advancement |
|---|---|---|---:|---:|---|
| `SEC-02-A` | Review only the highest-privilege account tier this cycle, with the scope written down | `single_observed_instance` | 3 | 2 | A dated review record exists, stating its own scope limit and the tier covered |

- **Effort:** 2 person-days across 1 of 1 steps
- **Skills:** identity administration

*Why this variant:* Same destination with one part-time reviewer: narrow the first review to the highest-privilege accounts rather than attempting the whole estate, so the practice starts rather than stalling.

### `PATH-SYN-DEP-01` — deployment (direct)

*Profile:* `PROF-SYN-IAM-DEP-01` — Production deployment approval

**Baseline (assumed): level 4 (consistent)** — the strongest stated evidence is 'repeated_instances', which supports up to level 4. This is what the ASSUMED evidence supports, not an observation of any real practice.

Evidence assumptions this rests on:

- `procedure_document` (supports to level 2) — A procedure requires two approvals for production deployment  
  *basis:* ASSUMED. Written procedure only.
- `repeated_instances` (supports to level 4) — A sample of changes over one month shows approvals recorded on each  
  *basis:* ASSUMED. Repeated instances across a window, which is what separates level 4 from level 3.

**Target: level 5 (measured)** — gain of 1

**FEASIBLE.** Level 4 (consistent) to level 5 (measured). The steps produce outcome_measurement, which supports up to level 5, so the target is earned by the evidence rather than asserted.

| step | capability change | produces | to level | effort (d) | observable advancement |
|---|---|---|---:|---:|---|
| `DEP-01-A` | Define the outcome the approval control is meant to produce, and how it would be measured | `procedure_document` | 2 | 2 | A written measure definition exists naming the numerator, denominator and observation window |
| `DEP-01-B` | Measure the outcome over a stated window and report it with its denominator | `outcome_measurement` | 5 | 6 | A report states the measured value, the window, the denominator, and the count of changes whose outcome is unknown |

- **Effort:** 8 person-days across 2 of 2 steps
- **Skills:** measurement design, reporting

*Why this variant:* Approvals are already consistent and recorded. The remaining level is about whether the control achieves anything measurable, not about doing more of it.

### `PATH-SYN-AI-01` — ai_readiness (limited_capacity)

*Profile:* `PROF-SYN-RIS-AI-01` — Review of AI-assisted analysis outputs

**Baseline (assumed): level 3 (practised)** — the strongest stated evidence is 'single_observed_instance', which supports up to level 3. This is what the ASSUMED evidence supports, not an observation of any real practice.

Evidence assumptions this rests on:

- `single_observed_instance` (supports to level 3) — One team records a reviewer sign-off on an AI-assisted output  
  *basis:* ASSUMED. A single instance: it happened once, which is not the same as it repeats.

**Target: level 4 (consistent)** — gain of 1

**FEASIBLE.** Level 3 (practised) to level 4 (consistent). The steps produce repeated_instances, which supports up to level 4, so the target is earned by the evidence rather than asserted.

| step | capability change | produces | to level | effort (d) | observable advancement |
|---|---|---|---:|---:|---|
| `AI-01-A` | Define the trigger that requires a reviewer sign-off on an AI-assisted output | `procedure_document` | 2 | 1 | A written trigger exists that a third party could apply to a given output and get the same answer |
| `AI-01-B` | Apply the trigger across a quarter and retain the sign-offs | `repeated_instances` | 4 | UNKNOWN | A quarter's outputs each carry a sign-off or a recorded reason the trigger did not apply |

- **Effort:** 1 person-days across 1 of 2 steps; 1 step(s) unestimated (AI-01-B), so this is a FLOOR, not a total
- **Skills:** analysis

*Why this variant:* One analyst, part time. The route is to make the existing single sign-off repeat on a defined trigger rather than to build a review programme.

### `PATH-SYN-SEC-06` — security (shared_service)

*Profile:* `PROF-SYN-IAM-SEC-01` — Group membership review

**Baseline (assumed): level 3 (practised)** — the strongest stated evidence is 'single_observed_instance', which supports up to level 3. This is what the ASSUMED evidence supports, not an observation of any real practice.

Evidence assumptions this rests on:

- `single_observed_instance` (supports to level 3) — One quarterly review is recorded in a spreadsheet  
  *basis:* ASSUMED. One recorded review.

**Target: level 4 (consistent)** — gain of 1

**FEASIBLE.** Level 3 (practised) to level 4 (consistent). The steps produce repeated_instances, which supports up to level 4, so the target is earned by the evidence rather than asserted.

| step | capability change | produces | to level | effort (d) | observable advancement |
|---|---|---|---:|---:|---|
| `SEC-06-A` | Review group membership from the shared service's export on a quarterly cycle, replacing the three spreadsheets | `repeated_instances` | 4 | 7 | Two consecutive quarters each produce a review record derived from the shared export, covering every group in scope |

- **Effort:** 7 person-days across 1 of 1 steps
- **Skills:** identity administration, reporting
- **External prerequisites (not ours to deliver):** the central identity service exposes a membership export

*Why this variant:* Three owners keep three spreadsheets. Rather than asking them to agree a format, take the membership data from the shared identity service they all already use.

## No path: the baseline is not established

### `PATH-SYN-AI-02` — ai_readiness (direct)

*Profile:* `PROF-SYN-ESS-AI-01` — Governance of assistive code generation

**Baseline (assumed): UNKNOWN** — assessment_status is 'unassessed', so no level is computed. Not level 1: an unassessed practice is an open question, not a weak one.

**Target: level 3 (practised)**

**BASELINE_UNKNOWN.** No path is produced. The baseline is not established: assessment_status is 'unassessed', so no level is computed. Not level 1: an unassessed practice is an open question, not a weak one. A route needs a starting point, and inventing one would be the unverified baseline this method must not present as fact.

What would unblock it:

- an assessment of this practice, with stated evidence

| step | capability change | produces | to level | effort (d) | observable advancement |
|---|---|---|---:|---:|---|
| `AI-02-A` | Introduce a review step for assistive code generation | `single_observed_instance` | 3 | 5 | One reviewed output is recorded |

*Why this variant:* REFUSAL CASE. Plans a route from a practice nobody has assessed.

## Refused: the evidence cannot reach the target

### `PATH-SYN-SEC-03` — security (direct)

*Profile:* `PROF-SYN-RIS-SEC-01` — Privileged access review

**Baseline (assumed): level 2 (documented)** — the strongest stated evidence is 'policy_document', which supports up to level 2. This is what the ASSUMED evidence supports, not an observation of any real practice.

Evidence assumptions this rests on:

- `policy_document` (supports to level 2) — A published standard requires an annual privileged-access review  
  *basis:* ASSUMED. A policy stating an intent; no review record is assumed to exist.

**Target: level 4 (consistent)** — gain of 2

**REFUSED_EVIDENCE_CAP.** Refused: these steps produce policy_document, procedure_document, which supports up to level 2. Level 4 needs evidence of a kind this path never creates. Effort cannot buy the difference -- the cap is about the kind of evidence, not its volume.

Evidence kinds that could reach the target: `repeated_instances`, `outcome_measurement`

| step | capability change | produces | to level | effort (d) | observable advancement |
|---|---|---|---:|---:|---|
| `SEC-03-A` | Write a detailed privileged-access review procedure | `procedure_document` | 2 | 10 | The procedure is published |
| `SEC-03-B` | Write a supporting standard and a RACI matrix | `policy_document` | 2 | 12 | Both documents are published and approved |

*Why this variant:* REFUSAL CASE, written deliberately. Proposes reaching consistent practice by writing more documents.

## Refused: aspirational jump

### `PATH-SYN-SEC-04` — security (direct)

*Profile:* `PROF-SYN-RIS-SEC-01` — Privileged access review

**Baseline (assumed): level 2 (documented)** — the strongest stated evidence is 'policy_document', which supports up to level 2. This is what the ASSUMED evidence supports, not an observation of any real practice.

Evidence assumptions this rests on:

- `policy_document` (supports to level 2) — A published standard requires an annual privileged-access review  
  *basis:* ASSUMED. A policy stating an intent; no review record is assumed to exist.

**Target: level 5 (measured)** — gain of 3

**REFUSED_ASPIRATIONAL_JUMP.** Refused: level 2 to level 5 is a gain of 3, beyond the 2-level maximum this method will plan. A longer jump is an aspiration, not a path; split it and plan the first 2 levels.

| step | capability change | produces | to level | effort (d) | observable advancement |
|---|---|---|---:|---:|---|
| `SEC-04-A` | Stand up a fully measured privileged-access review programme | `outcome_measurement` | 5 | 40 | A measured report exists |

*Why this variant:* REFUSAL CASE. Proposes going from a policy document to measured outcomes in one plan.

## Refused: advancement is not observable

### `PATH-SYN-SEC-05` — security (direct)

*Profile:* `PROF-SYN-IAM-SEC-01` — Group membership review

**Baseline (assumed): level 3 (practised)** — the strongest stated evidence is 'single_observed_instance', which supports up to level 3. This is what the ASSUMED evidence supports, not an observation of any real practice.

Evidence assumptions this rests on:

- `single_observed_instance` (supports to level 3) — One quarterly review is recorded in a spreadsheet  
  *basis:* ASSUMED. One recorded review.

**Target: level 4 (consistent)** — gain of 1

**REFUSED_NO_OBSERVABLE.** Refused: step(s) SEC-05-A state no observable advancement. A step whose completion nobody can check is not a plan, and it is not made into one by writing TBD.

| step | capability change | produces | to level | effort (d) | observable advancement |
|---|---|---|---:|---:|---|
| `SEC-05-A` | Improve the group review process and raise awareness across owners | `repeated_instances` | 4 | 6 | **none stated** |

*Why this variant:* REFUSAL CASE. The evidence kind is right, but one step's completion is not checkable.

## Refused: an unmet prerequisite

### `PATH-SYN-SD-02` — software_development (direct)

*Profile:* `PROF-SYN-ESS-SD-01` — Peer review before merge

**Baseline (assumed): level 3 (practised)** — the strongest stated evidence is 'single_observed_instance', which supports up to level 3. This is what the ASSUMED evidence supports, not an observation of any real practice.

Evidence assumptions this rests on:

- `procedure_document` (supports to level 2) — A written standard requires peer review before merge  
  *basis:* ASSUMED for this worked example. Modelled on the kind of document an engagement would request; no such document was read.
- `single_observed_instance` (supports to level 3) — One repository shows a branch rule requiring a review  
  *basis:* ASSUMED. One repository's configuration, which is an instance and not a pattern.

**Target: level 4 (consistent)** — gain of 1

**REFUSED_UNMET_PREREQUISITE.** Refused: prerequisite(s) SD-02-Z are named by a step but produced by no step in this path. Either add the step or declare the prerequisite external with an 'EXTERNAL:' prefix so it is visibly somebody else's to deliver.

| step | capability change | produces | to level | effort (d) | observable advancement |
|---|---|---|---:|---:|---|
| `SD-02-A` | Sample a month of merges for recorded reviewers | `repeated_instances` | 4 | 3 | A one-month sample shows a recorded reviewer on each merge |

*Why this variant:* REFUSAL CASE. A step depends on work no step in the path delivers, and it is not declared external.

## Limits

- Every profile here is a synthetic assumption set. None describes the University of Iowa's practice, and no output may be presented as a University baseline or finding.
- A FEASIBLE verdict means the path's evidence kind can reach the target level and every step is observable. It is not a prediction that the work will succeed, and not a commitment to deliver it.
- Effort figures are stated assumptions. Where a step is unestimated the total is reported as a floor, never completed to a round number.
- No individual, team or unit is rated anywhere in this output.

---

Generated offline by `progression.py` (Python standard library only). Synthetic throughout.
