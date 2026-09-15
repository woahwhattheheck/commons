# Requirements / compliance matrix

**Status legend:** `PUBLIC` = observed in public discovery sources; `GATE` = must be confirmed in controlling package; `EVIDENCE` = bidder/vendor proof required; `DESIGN` = proposed response architecture, not a claimed existing capability.

| # | Requirement theme | Status | Proposed response / acceptance evidence | Bid evidence still required |
|---|---|---|---|---|
| R1 | Central discovery of certificates across on-prem and cloud | PUBLIC | Agentless/network plus connector/API discovery where product supports it; reconcile discovered certs to accountable inventory. Acceptance: seeded known-cert set + scan coverage report + orphan/unknown queue. | Exact supported discovery methods, network boundaries, cloud accounts, appliances. |
| R2 | Real-time/central certificate inventory | PUBLIC | Canonical certificate record: fingerprint/serial, subject/SAN, issuer/CA, owner, environment, endpoint, expiry, key/profile metadata where safely available, lifecycle state. | Product schema/export/API evidence. |
| R3 | Expiry/anomaly monitoring and alerting | PUBLIC | Configurable thresholds, ownership routing, suppression/maintenance windows, escalation and dashboarding. | Required channels, response targets, University monitoring stack. |
| R4 | Automated issuance | PUBLIC | Policy-approved enrollment via CA connector/protocol and authenticated workload identity. | Supported CAs/protocols and enrollment constraints. |
| R5 | Automated renewal/replacement | PUBLIC | Renewal window policy → issue → deploy → validate → retire old certificate only after success. | Native integrations, non-exportable-key constraints, HSM/KMS behavior. |
| R6 | Revocation | PUBLIC | Authorized revocation workflow with reason capture, approval, CA confirmation and dependent-service validation. | CA-specific revocation support and RBAC. |
| R7 | Deployment automation | PUBLIC | Native adapters first; scoped post-push automation only for unsupported targets. Idempotent deployment with pre/post checks. | Supported OS/web server/load balancer/appliance/cloud targets. |
| R8 | Validation and rollback | PUBLIC | TLS/service validation after deployment; defined rollback or safe retention of previous credential where platform permits. | Product-native rollback semantics and buyer recovery objectives. |
| R9 | Public and private CA support | PUBLIC | Connector abstraction so policy/orchestration does not depend on one issuer. | Exact incumbent/public CAs, AD CS/private PKI, ACME/SCEP/EST availability. |
| R10 | Integrate with identity/directory | PUBLIC | Enterprise IdP/Directory authentication; groups → least-privilege roles; service identities for connectors. | Actual directory/IdP and supported authentication modes. |
| R11 | Policy workflows and RBAC | PUBLIC | Separation of request/approve/admin/audit roles; policy-scoped certificate profiles and exception workflow. | Required roles, approval model, delegated administration. |
| R12 | API/connectors | PUBLIC | Versioned API/webhook integration surface; least-privilege service accounts; retry/idempotency. | Official API docs, limits, auth method, required integrations. |
| R13 | Azure/AWS and enterprise systems | PUBLIC | Connector inventory and staged validation per environment. | Exact cloud services/accounts and product connector evidence. |
| R14 | Audit logging | PUBLIC | Actor, action, object, timestamp, policy decision, before/after where applicable; export to institutional logging/SIEM. | Retention, immutability/export requirements, SIEM target. |
| R15 | Compliance / Canadian privacy & security | PUBLIC + GATE | Data-flow/register review; minimize collected certificate/key metadata; no private-key ingestion unless architecture explicitly requires and secures it. | Controlling privacy/security/data-residency clauses; vendor attestations/certs. |
| R16 | Implementation / configuration / testing | PUBLIC | Phased discovery → pilot → waves → acceptance → handover, with rollback gates. | Buyer schedule, environments, change windows, acceptance terms. |
| R17 | Documentation and training | PUBLIC | As-built architecture, inventory taxonomy, connector runbooks, failure playbooks, admin/operator training, knowledge-transfer sessions. | Required formats, audience, training quantities. |
| R18 | Ongoing support / updates / maintenance | PUBLIC | Named support model with escalation and release/change process. | **Do not promise SLA values** until vendor/delivery owner approves. |
| R19 | Incident response/resolution SLA | PUBLIC | Severity model + contact/escalation matrix + evidence capture. | Buyer required targets and vendor-backed targets. |
| R20 | Avoid custom scripting where native integration exists | PUBLIC | Adapter decision tree: native connector first, supported protocol second, controlled automation last; maintain exception register. | Product integration catalog. |
| R21 | Pricing/currency/taxes | GATE | Use controlling pricing form only; model software, implementation, support, optional services, travel and tax separately if requested. | Bid form, currency, tax treatment, term/renewal. |
| R22 | Bidder legal/geographic eligibility | GATE | No assumption. | Buyer rules + our entity/partner evidence. |
| R23 | References/experience | GATE + EVIDENCE | Only name references approved and verifiable for the proposed prime/team member. | Required count, recency, similarity, contact permission. |
| R24 | Security certifications / insurance | GATE + EVIDENCE | Claim only exact in-force certifications/policies of bidding entity/vendor. | Required standards/limits and certificates. |
| R25 | Accessibility | GATE | Assess portal/UI/report outputs against buyer-required standard if applicable. | Required standard (if any), VPAT/accessibility evidence. |

## Mandatory response rule

No row may be changed from `GATE`/`EVIDENCE` to “compliant” because it sounds technically plausible. Closure requires a source locator in the controlling procurement package and, for vendor/bidder capability, an official product/company artifact.
