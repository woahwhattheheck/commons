# Partner workstream — migration, integration verification, and release evidence

## Positioning

This workstream is designed to be sold to a qualified Dynamics 365 prime as a separately acceptable engineering package. It does **not** require TokenJunkieLabs to claim Dynamics solution-architecture authority, Microsoft partner status, buyer relationship ownership, or prime contractual responsibility.

Working name: **OneODA Data & Integration Evidence Plane**.

## Inputs required from prime / buyer

No execution estimate is valid until these are provided from controlling sources:

- authorized legacy source inventory and Attachment L equivalent;
- target entity/data contract and transformation rules;
- Attachment I integration inventory plus interface owners;
- cutover windows, retention rules and environment constraints;
- non-production test datasets or approved synthetic fixtures;
- security/data-handling constraints and approved execution environment;
- prime-owned Dynamics/API endpoints, schemas and authentication contract;
- agreed acceptance tolerances for row counts, financial values, identifiers, attachments and referential integrity.

## Deliverables

### D1 — Immutable source inventory

For every migration source/table/export:

- stable source identifier;
- extraction timestamp/window;
- schema fingerprint;
- source row count;
- byte count;
- content/chunk hashes where permitted;
- extraction tool/version;
- restart/resume marker;
- exception list.

**Acceptance:** every supplied source is represented once; duplicate/missing identifiers fail validation; manifest can be regenerated deterministically from the same approved export.

### D2 — Mapping and transform ledger

A versioned ledger binding source fields to target contracts with:

- source/target type;
- normalization rule;
- null/default semantics;
- code/enum translation;
- reference/master-data dependency;
- PII/sensitive classification supplied by the prime/buyer;
- owner/approver;
- test fixture IDs.

**Acceptance:** every required target field has an explicit source/rule or documented exception; no implicit defaulting.

### D3 — Reconciliation harness

Automated migration verification reports at minimum:

- source-vs-loaded record counts by entity/partition;
- rejected/quarantined records with reason codes;
- uniqueness/key collisions;
- referential-integrity breaks;
- value-domain violations;
- numeric/date aggregate comparisons for designated critical fields;
- attachment/document cardinality where applicable;
- deterministic sample trace from source record to target identity.

**Acceptance:** configured invariants pass, or every variance is enumerated in the exception ledger and explicitly dispositioned.

### D4 — Integration contract-test harness

For interfaces selected from the controlling integration inventory:

- request/response schema tests;
- idempotency and replay fixtures where applicable;
- timeout/retry/failure-path tests;
- authentication/authorization contract checks supplied by the prime;
- correlation IDs and reproducible traces;
- synthetic or approved non-production fixtures;
- dependency-version and endpoint inventory.

**Acceptance:** agreed happy/failure paths produce machine-readable evidence with no hidden manual pass/fail step.

### D5 — Cutover rehearsal and delta receipts

- rehearsal runbook;
- full-load receipt;
- incremental/delta window receipt;
- late-arriving-change reconciliation;
- rollback decision checkpoints;
- elapsed-time/capacity measurements;
- unresolved-exception gate.

**Acceptance:** the prime can answer what moved, when, from which snapshot, what failed, what changed after the snapshot, and whether rollback criteria were triggered.

### D6 — Release / acceptance evidence bundle

Machine-readable index mapping requirements supplied by the prime to:

- source manifests;
- test IDs and results;
- migration/reconciliation receipts;
- integration traces;
- unresolved exceptions;
- approval identity/time;
- artifact hashes.

**Acceptance:** a reviewer can trace each in-scope acceptance statement to evidence without relying on chat history or undocumented operator memory.

## Commercial slicing

To create a credible paid path without pretending to own the whole program, quote the workstream in bounded stages after a prime provides the actual inventories:

1. **Discovery & evidence design** — inventory ingestion, risk map, acceptance schema, proof on synthetic/sample data.
2. **Migration verification implementation** — manifests, mapping checks, reconciliation harness.
3. **Integration verification implementation** — contract-test fixtures for agreed interfaces.
4. **Cutover evidence** — rehearsal/delta/rollback receipts and acceptance bundle.
5. **Optional stabilization support** — evidence-driven defect triage during agreed window.

Each stage should have its own price, inputs, acceptance criteria and stop/go decision. Do not quote rates or totals from this capture package.

## Explicit exclusions

Unless separately contracted and backed by qualified personnel, this lane excludes:

- Dynamics 365 solution architecture/configuration/customization;
- Power Pages implementation ownership;
- licensing resale or Microsoft partner representations;
- business-process authority;
- accessibility conformance certification;
- Oregon security-control attestation;
- legal/privacy determinations;
- prime project management/OCM;
- final production go-live authority;
- buyer certifications/signatures.

## Data-safety rule

Build demonstrations from synthetic fixtures only. Do not obtain or process Oregon production/regulated data as part of pursuit. Real buyer data requires an executed agreement, approved environment, security responsibilities, retention/destruction rules and access authorization.

## Why this seam is valuable to a prime

A large migration/integration program can appear operationally complete while still lacking durable proof of what moved and what passed. This workstream turns migration/integration correctness into reproducible evidence and isolates an acceptance-risk surface that a Dynamics prime may prefer to subcontract without ceding architecture authority.