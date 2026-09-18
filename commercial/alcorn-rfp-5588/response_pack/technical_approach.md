# Alcorn State RFP #5588 — internal technical approach draft

**Draft boundary:** this is an internal response component derived from the source-bound qualification carrier. It is not a representation that Token Junkie Labs is an NVIDIA partner, hardware supplier, prime contractor, accepted subcontractor, or authorized submitter. Any named partner/OEM capability must come from separately bound evidence and commitment.

## 1. Design objective

Prepare two AI proficiency labs around the buyer's NVIDIA Spark environment while preserving a clean line between (a) buyer minimum specifications, (b) a real NVIDIA-authorized hardware/infrastructure party's obligations, and (c) a bounded TJLabs specialist workshare. The final proposal architecture must trace every promised component to an entity that can actually supply, warrant, deploy, train, and support it.

The buyer-source floor currently normalized in `../qualification_spec.json` includes the NVIDIA-partner gate, AI-infrastructure rollout history, DGX Spark lab design, training, acceptance/facility training, one-year hardware/software warranty, first-year onsite support in cost, and a callable reference-site obligation. Those are gates, not assumptions.

## 2. Proposed architecture workstream

### 2.1 Lab discovery and bill-of-materials freeze

Before commercial release, the responsible NVIDIA/OEM party should reconcile the buyer packet against the final room, power, cooling, network, cabling, workstation, monitor, peripheral, and Spark-station quantities. Every bill-of-materials line should carry supplier, manufacturer part/reference, minimum-spec mapping, warranty owner, lead time, and substitution rule.

The buyer packet was normalized as requiring a DGX Spark environment. Earlier source review recorded station minimums including GB10 Grace Blackwell, 128 GB unified memory, 4 TB NVMe, ConnectX-7, DGX OS and the CUDA/cuDNN/TensorRT/PyTorch/RAPIDS software environment. These details remain buyer-source notes to verify against the bound packet before external release; this draft does not upgrade them into an independently certified configuration.

### 2.2 Network and service plane

Design the lab service plane so installation, image/bootstrap, software-package provenance, web-access surfaces, data movement, and instructional resets are repeatable. A release candidate should include:

- physical/network topology and addressing responsibility;
- installation/image checklist with version capture;
- GPU/accelerator and software-stack acceptance checks;
- controlled account/access handoff;
- reproducible lab reset or recovery procedure;
- inventory/serial/warranty evidence capture;
- documented exception and substitution handling.

No security, privacy, hosting, availability, or compliance certification is claimed by this draft unless the final packet expressly sources it.

## 3. Deployment sequence

1. **Source and requirement freeze.** Reconcile the final buyer packet/addenda and all missing buyer-controlled forms before promising a configuration.
2. **Authority and supplier freeze.** Bind a current NVIDIA-authorized party and its exact Spark-lab scope; bind supplier/warranty obligations.
3. **Site readiness.** Confirm space, power, network/cabling, receiving, staging, access, and installation constraints with the parties authorized to do so.
4. **Staging.** Inventory equipment, capture serials/versions, validate firmware/software prerequisites, and build an exception ledger.
5. **Install.** Assemble two labs according to the approved bill of materials and topology.
6. **Platform validation.** Execute hardware health, network, storage, accelerator, driver/runtime, package, and web-interface checks against an approved acceptance script.
7. **Instructional validation.** Exercise training workflows, including Spark setup/playbooks, web interfaces, NVIDIA NIMs, and LLM fine-tuning topics identified in the buyer-source review.
8. **Acceptance package.** Deliver equipment inventory, configuration/version record, test evidence, documentation, exception disposition, and facility-crew training evidence for owner review.
9. **Support transition.** Hand off warranty/support contacts, escalation paths, response expectations, runbooks, and any onsite-support schedule actually committed by the responsible party.

## 4. Acceptance model

The internal acceptance model is evidence-first rather than assertion-first. For each promised line item, the response should ultimately record:

- buyer requirement/source coordinate;
- responsible delivery entity;
- committed item/service;
- evidence expected before install;
- verification method;
- acceptance result;
- exception and cure owner;
- warranty/support owner;
- final owner acknowledgement where the contract requires it.

Buyer-source review recorded acceptance around contracted equipment, owner final check, documentation, and facility-crew training. The final acceptance procedure must be reconciled to the controlling RFP/contract, not inferred from this draft.

## 5. Training architecture

Training should be split into administrator/facility handoff and instructional-user enablement. The source-derived topic set includes Spark setup/playbooks, web interfaces, NVIDIA NIMs, and LLM fine-tuning. A release-ready training package should bind instructor identity/qualification, prerequisites, agenda, hands-on exercises, reset/recovery instructions, learner materials, sample outputs, and post-session support path.

`training_sample_ready` is currently a qualification blocker. This draft is a workplan, **not** the missing approved sample.

## 6. Support and warranty boundary

The buyer carrier records a minimum one-year hardware/software warranty and first-year onsite support included in proposal cost. The final response must identify which legal entity actually owes each obligation, the covered assets/services, start date, exclusions, service path, and escalation owner. TJLabs must not inherit or imply OEM warranty authority merely by participating in a team.

## 7. Value-add concepts that do not widen authority

Potential differentiators, only if they fit the final buyer packet and committed team, include:

- a source-linked acceptance ledger mapping every requirement to evidence;
- a deterministic lab readiness checklist usable for both labs;
- configuration/version manifests to simplify future support;
- instructor and facility handoff runbooks;
- an exception/cure ledger that separates buyer change, supplier variance, and implementation defects;
- a repeatable lab reset/recovery procedure for instruction cycles.

These are drafting concepts, not buyer-approved scope.

## 8. Release gates

This technical approach must remain internal while `../current_result.json` is `HOLD`. Before any external release, the pursuit owner must re-read the exact buyer packet/addenda and require source-bound resolution of the existing qualification blockers, the missing Section VIII/IX/Item 12 artifacts, real partner/OEM authority, references, insurance/legal/private submission evidence, pricing, signature authority, and physical delivery plan. External authority remains false even when this draft is complete.
