# Prime-facing workshare catalog

## 1. Legacy Migration Evidence & Reconciliation

**Prime problem:** migrations fail quietly when counts match but semantics drift, exceptions disappear into spreadsheets, or transformed fields lose provenance.

**TJL workshare:** ingest prime/buyer-approved source extracts and mappings; generate partition/accounting controls, source→target field invariants, exception queue and repeatable replay receipt. We deliver evidence, not production migration authority.

**Acceptance:** every in-scope source partition accounted for; control totals match or carry an explicit approved exception; every transformed field maps to an explicit rule or is marked unmapped; identical inputs reproduce the same receipt.

## 2. Integration Contract Conformance

**Prime problem:** an interface can be “connected” while version, idempotency, retries, field constraints or negative paths remain unproven.

**TJL workshare:** contract-version-bound harness with positive/negative/retry/replay cases, request/response evidence locators and deterministic conformance receipts.

**Acceptance:** required fields/types/version semantics exercised; retry/idempotency/error contract explicitly tested; result binds exact contract/fixture digests; test success never becomes a production-availability claim.

## 3. UAT & Acceptance Evidence

**Prime problem:** UAT artifacts are scattered across tickets, spreadsheets, screenshots and defect logs, making bid/acceptance claims hard to audit.

**TJL workshare:** requirement→scenario→execution→defect/waiver trace matrix and a fail-closed readiness packet.

**Acceptance:** every in-scope requirement maps to execution evidence or HOLD; blocked/failed cannot render passed; waivers retain external attribution; handoff packet digest verifies.

## 4. Cutover, Rollback & Replay Evidence

**Prime problem:** go-live plans often contain irreversible steps but weak machine-checkable pre/post evidence and rollback criteria.

**TJL workshare:** ordered checkpoint/replay plan, pre/post reconciliation, rollback decision template and dry-run receipt. Prime/buyer owns every irreversible production action.

**Acceptance:** control totals explicit; rollback criteria machine-checkable where practical; dry-run evidence never becomes production evidence; production execution remains outside TJL's packet authority.
