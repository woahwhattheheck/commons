# RCAP CRM System Assessment — qualification and proposal-readiness packet

This package tracks the Rural Community Assistance Partnership (RCAP) **CRM System Assessment and Strategic Planning Services** RFP released September 4, 2026. It is an internal qualification and drafting aid, not a submitted proposal, contract, reference claim, insurance claim, or authorization to contact RCAP.

## First-party opportunity facts

Official source: <https://www.rcap.org/careers/rfp-assessment-strategic-planning-services/>

As revalidated on September 13, 2026, RCAP says:

- proposals are due **October 4, 2026**; questions are due **September 13, 2026**;
- the work is an **independent, vendor-neutral assessment and strategic-planning engagement**, not simply implementation or CRM replacement;
- the current custom DCS supports **six regional nonprofits plus RCAP** and has **400–500 active user accounts**;
- stated concerns include resiliency, aging components, scalability, audit logging, permissions, SQL-dependent reporting, and lack of integration with **Unanet**;
- required outputs are kickoff/work plan, stakeholder discovery, a concise System Summary/assessment with findings and next steps, and a virtual findings presentation;
- proposals must state the anticipated number/format of discovery meetings, estimated schedule, **fixed fee**, delivery model/project lead, and clearly separate optional value-added services from base price;
- examples, references, or brief descriptions of comparable work are requested **if available**;
- evaluation weights are 30% relevant comparable assessment work, 25% approach/methodology, 20% nonprofit or similar-organization experience, 15% qualifications/delivery model, and 10% cost/value;
- the desired qualifications are explicitly **not minimum pass/fail requirements unless expressly stated**;
- respondents must be U.S.-based organizations; a professional indemnity/liability insurance COI is a **condition of contract award**.

The public RFP gives a proposal due date but no submission clock time or timezone on the page currently captured here. The checked-in facts therefore require a fresh exact deadline-time revalidation before any `READY_TO_SUBMIT` result.

## Strong-fit delivery concept

The engagement can be sold as a bounded decision product rather than a speculative implementation project:

1. **Kickoff + evidence inventory** — agree success criteria, decisions to be enabled, source systems, interview map, constraints, and deliverable format.
2. **Stakeholder discovery** — structured sessions across program, operations, finance/Unanet, data/reporting, security/governance, and representative regional users. The proposal must price an explicit meeting count.
3. **Current-state architecture and risk map** — document DCS/data-flow boundaries, integration seams, operational dependencies, permission/audit controls, reporting friction, resiliency/scalability risks, and user-experience constraints.
4. **Option analysis** — compare optimize/modernize, replace, hybrid, and other viable paths on decision criteria that RCAP can inspect. Avoid steering toward a preferred vendor.
5. **Sequenced roadmap** — prerequisites, decision gates, migration/integration implications, governance/security work, near-term stabilization, and next procurement/build steps.
6. **Executive readout** — concise System Summary plus decision matrix and facilitated discussion.

This preserves the RFP's stated objective: help RCAP choose a path before committing to a replacement platform.

## Qualification posture

The checked-in `qualification.json` is deliberately **HOLD**. Unknown organization facts are not inferred from repository ownership or prior work. Before a submission can become ready, record verified evidence for:

- U.S. primary place of business;
- professional indemnity/liability COI already available or a truthful plan to obtain it before award;
- final project lead/delivery model;
- explicit discovery-meeting count and schedule;
- owner-approved fixed fee;
- exact deadline-time revalidation;
- owner authorization for external submission.

Comparable examples/references and the five desired experience dimensions materially affect win probability, but the source explicitly says those qualifications are not pass/fail. The validator therefore reports missing evidence as warnings rather than inventing a disqualifier.

## Run the gate

```bash
cd opportunities/rcap-crm-assessment-2026
python -m unittest -v test_validate_qualification.py
python -O -m unittest -v test_validate_qualification.py
python validate_qualification.py --today 2026-09-13 --expect-hold
```

The checked-in scaffold must stay `HOLD` until real owner/organization/proposal facts are supplied. A synthetic fully populated fixture in the tests proves that the gate can reach `READY_TO_SUBMIT` without converting desired qualifications into hard gates.

## External-action boundary

No question email, proposal email, pricing offer, reference outreach, confidentiality commitment, insurance representation, or contract acceptance is performed by this package. If a later operator is authorized to submit, re-read the live RCAP page first because RCAP reserves the right to amend, suspend, or cancel the RFP.
