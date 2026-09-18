# Teaming subcontract package — specialist AI / agent engineering seam

## Positioning

**Role:** specialist subcontractor to an established public-sector technology / consulting prime responding to NASPO SW1045.

**Why this seam exists:** the existing repository evidence is strongest where a prime can insert a bounded, independently testable AI/agent delivery capability. It is weakest where a NASPO prime may need public-sector reference history, cooperative-contract administration, named staff commitments, commercial certifications and nationwide account operations. The package therefore isolates the technical value instead of manufacturing the missing prime history.

## Proposed work packages

### WP1 — Emerging-technology / AI architecture

- Translate an approved public-entity SOW into bounded AI/agent workflows.
- Define principal, resource, action, evidence, model/configuration and human-approval contracts.
- Produce interface and data-flow diagrams with explicit consequential-action boundaries.
- Design for buyer-selected cloud/security/data-residency constraints once those are contractually known.

**Deliverables:** architecture decision record, workflow contract, threat/failure inventory, implementation backlog.

### WP2 — Responsible AI and governance engineering

- Human approval for consequential state changes.
- Evidence provenance, model/config revision identity and auditable policy versions.
- Explicit uncertainty/escalation and conflict handling.
- Data minimization and retention hooks.
- Failure modes covering unsupported claims, stale evidence, duplicated effects, unsafe retries and ambiguous provider outcomes.

**Deliverables:** governance/control matrix, model-change protocol, human-oversight runbook, red-team cases.

### WP3 — Implementation / integration

- Build buyer-approved connectors behind stable, buyer-neutral contracts.
- Preserve idempotency and exact resource/action scope.
- Treat timeout-after-dispatch as `UNKNOWN` until reconciled rather than assuming success/failure.
- Add provider-specific reconciliation before retry.
- Keep production credentials, buyer policies and identity under prime/customer-controlled deployment.

**Deliverables:** adapters, integration tests, deployment configuration contract, reconciliation handlers.

### WP4 — MLOps / evaluation / observability

- Bind model/provider/version/configuration to evaluated interactions.
- Record evidence/source and output digests suitable for reproducible evaluation.
- Track accept/revise/reject/escalate actions where humans review AI outputs.
- Separate product telemetry from business/public outcomes.
- Preserve intervention-version identity when prompts/models/policies change.

**Deliverables:** telemetry schema, evaluation harness, quality/failure metrics, versioned evaluation receipts.

### WP5 — Acceptance and reliability evidence

Reuse and extend the existing SW1045 agent-workflow acceptance core:

- exact authority/action digest binding;
- deterministic idempotency keys;
- timeout/unknown reconciliation;
- duplicate-effect detection;
- canonical tamper-evident receipts;
- hostile JSON/type/file-boundary tests;
- optimized-Python parity where applicable.

Buyer/SOW-specific acceptance cases are added **only after** exact requirements are available.

**Deliverables:** acceptance matrix, test corpus, reproducible receipts, known-limitations ledger.

## Prime-owned responsibilities

Unless separately evidenced and agreed, the prime remains responsible for:

- NASPO/Oklahoma portal access, communications and proposal submission;
- bidder eligibility and exact category qualification;
- public-sector past performance and references;
- named/key personnel commitment;
- cooperative-purchasing contract administration;
- insurance, financial capacity and certifications;
- pricing workbook / commercial terms;
- subcontract approval and flow-down terms;
- hosting / data residency infrastructure commitments;
- signatures, representations and contract acceptance.

## Staffing assumption

Initial specialist roles, not named-person commitments:

- AI workflow / integration engineer;
- evaluation / reliability engineer.

Additional security, cloud, UX, data science, change-management or support roles are SOW-dependent and should not be precommitted before buyer/prime requirements are known.

## Pricing boundary

No rate, discount, ceiling, minimum volume or price unit is committed here. Build the price worksheet only after the controlling pricing attachment and the prime's commercial model are captured. A draft must distinguish labor assumptions from buyer-mandated units and must never be treated as submitted pricing.

## Acceptance boundary

This package can be inserted into a prime's internal solution design after owner review. It is **not** permission to name a prime, claim a relationship, submit to NASPO, promise a person, certify compliance, or bind price.
