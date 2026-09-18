# Alcorn State RFP #5588 — implementation, training, and support workplan

**Internal draft only.** This plan prepares response material; it does not establish a prime, NVIDIA/OEM authority, staffing commitment, warranty commitment, customer price, signature authority, or proposal-submission authority.

## Delivery phases

### Phase 0 — controlling-source and authority freeze

Exit only when the pursuit owner has reconciled the exact buyer packet plus all addenda, the three referenced-but-absent buyer artifacts have a source-backed disposition, and every party whose qualifications are relied upon has provided current evidence and a commitment covering its proposed role. The existing `../current_result.json` is authoritative; while it is `HOLD`, later phases are planning only.

### Phase 1 — design and site-readiness package

Produce the final two-lab design, bill of materials, room/network/cabling assumptions, receiving/staging plan, installation sequence, configuration/version plan, and acceptance script. Record every dependency as `PROVEN`, `OWNER_INPUT_REQUIRED`, `PARTNER_EVIDENCE_REQUIRED`, or `BUYER_ARTIFACT_REQUIRED`; never silently convert an unknown into a pass.

### Phase 2 — staging and provenance capture

For equipment and software that a real committed supplier provides, capture inventory identity, serial/asset information where appropriate, firmware/software versions, supplier/warranty owner, source/reference for substitutions, and any exception to the approved design. Sensitive identifiers stay in the controlled delivery record, not this public repository.

### Phase 3 — installation and validation

Use a two-pass acceptance sequence:

1. **Infrastructure pass:** physical inventory, power/network/cabling, storage, accelerator/runtime health, and approved software-stack availability.
2. **Instructional pass:** representative learner/admin workflows, web interfaces, environment reset/recovery, NVIDIA NIM and LLM fine-tuning exercises where those topics remain in the final buyer-source requirements.

Every failed check should produce a named cure owner and retest record rather than a narrative assertion that the lab is ready.

### Phase 4 — owner acceptance and documentation handoff

Assemble a buyer-facing package only after authority gates clear. Planned contents include final inventory, configuration/version manifest, acceptance results, unresolved exceptions if any, operating/runbook material, training material, warranty/support contacts, and facility-crew handoff evidence. The buyer packet's acceptance language controls over this internal plan.

### Phase 5 — first-year support transition

The source carrier records first-year onsite support in proposal cost and a minimum one-year hardware/software warranty. The final team must bind those obligations to the entity that can actually perform them. Planned operational artifacts:

- support entrypoint and escalation path;
- covered hardware/software/services;
- warranty start/end trigger and exclusions;
- onsite-response scheduling process;
- incident evidence and replacement/cure workflow;
- configuration-change record;
- recurring health / maintenance procedure only where actually contracted.

TJLabs participation cannot imply OEM replacement authority or a warranty it has not accepted.

## Training workstream

### Audiences

- facility/technical staff responsible for operating and recovering the labs;
- instructors or instructional administrators;
- learners using the approved lab exercises.

### Planned source-derived modules

1. Spark environment orientation and setup/playbook usage.
2. Web interface access and operational workflow.
3. NVIDIA NIM usage where included in the final source set.
4. LLM fine-tuning workflow where included in the final source set.
5. Lab reset/recovery and evidence capture.
6. Facility-team troubleshooting and escalation.

### Training evidence package

A release-ready training sample should include learning objectives, prerequisites, timed agenda, instructor qualification/role, hands-on exercises, expected outputs, reset/recovery steps, learner handout, and support follow-through. The current canonical result includes `training_sample_ready` as a blocker; this workplan does **not** mark that gate satisfied.

## Responsibility handoffs

The workplan depends on the separate `responsibility_matrix.md`. In particular:

- NVIDIA/OEM authority, hardware supply, warranty, and any manufacturer-specific support stay with a proven committed entity.
- TJLabs may provide only a bounded specialist workshare that is explicitly committed and does not borrow partner credentials.
- Bryce/authorized owner retains customer pricing, legal-entity/private submission data, signature, final commercial approval, and actual submission decisions.
- Buyer acceptance can only be established by the buyer/contract process.

## Milestone evidence model

Each phase should generate a deterministic milestone record containing `source_requirements`, `responsible_party`, `planned_outputs`, `evidence_ids`, `exceptions`, and `owner_approval_state`. A phase is not complete merely because a document exists; required third-party/owner evidence must be present.

## Deadline discipline

Proposal due time in the canonical source is `2026-09-21T14:00:00-05:00`. Physical sealed-delivery timing must work backward from actual carrier/hand-delivery feasibility and buyer receiving rules. This file does not claim that logistics are ready; `sealed_delivery_plan_ready` remains an explicit blocker in the current qualification result.

## No-release rule

Nothing in this workplan may be used to override a canonical `HOLD`, release an unapproved price, sign or certify on another party's behalf, claim a partner relationship, contact the buyer contrary to the pursuit owner's routing, or submit a proposal. Those authorities remain false until separately and explicitly established outside this compiler.
