# Vendor-neutral target architecture

This is a response architecture and acceptance model, **not** a claim that any unnamed product already implements every component.

## Control-plane model

```text
                    +-----------------------------+
                    | IdP / Directory / RBAC      |
                    +--------------+--------------+
                                   |
                                   v
+-------------+    +---------------+----------------+    +----------------+
| Discovery   |--->| Canonical certificate inventory |<---| CMDB / owner    |
| connectors  |    +---------------+----------------+    | metadata        |
+------+------+                    |                     +----------------+
       |                            v
       |              +-------------+--------------+
       |              | Policy + workflow engine   |
       |              | profiles / approvals /     |
       |              | exceptions / renewal rules |
       |              +------+------+--------------+
       |                     |      |
       |                     |      +--------------------+
       |                     v                           v
       |              +------+---------+          +------+---------+
       |              | CA connectors  |          | Audit / events  |
       |              | public/private |          | SIEM / reporting|
       |              +------+---------+          +----------------+
       |                     |
       |                     v
       |              +------+------------------+
       +------------->| Deployment adapters     |
                      | servers/cloud/appliances|
                      +------+------------------+
                             |
                             v
                      +------+------------------+
                      | Post-deploy validation  |
                      | health / TLS / rollback |
                      +-------------------------+
```

## Design principles

1. **Inventory before automation.** Do not automate renewal for assets whose owner, endpoint or issuer is unknown. Discovery creates an exception queue until ownership is resolved.
2. **Private-key minimization.** Prefer designs where private keys remain in the workload, HSM/KMS or destination keystore. If a product must handle key material, document encryption, access, exportability, custody and audit paths explicitly.
3. **Native connector first.** For a supported target, use vendor-maintained integration before custom scripting. Use standards-based protocols next; custom automation is an exception with an owner/test plan.
4. **Separate issuance from deployment.** A CA can issue successfully while the service remains broken. Treat deploy and post-deploy validation as explicit lifecycle states.
5. **No destructive cutover before validation.** Keep the previous credential usable until the new deployment proves healthy where the platform/target supports rollback.
6. **Least privilege.** Separate platform administration, certificate policy administration, request/approval, connector service identities and read-only audit.
7. **Everything attributable.** Lifecycle events must identify actor/service identity, certificate object, target, policy decision, result and timestamp.
8. **Exportable operations.** Inventory, configuration, audit data and runbooks must be exportable enough to support University operations and future transition.

## Lifecycle state machine

```text
DISCOVERED -> OWNED -> POLICY_ASSIGNED -> ELIGIBLE
    -> ISSUING -> ISSUED -> DEPLOYING -> VALIDATING -> ACTIVE
    -> RENEWAL_DUE -> ... -> ACTIVE
    -> REVOKE_PENDING -> REVOKED -> RETIRED

Any stage may enter EXCEPTION; EXCEPTION requires owner, reason,
expiry/SLA risk, remediation action and closure evidence.
```

## Integration boundaries to validate

### Certificate authorities

Confirm actual issuers. Candidate protocol classes include vendor APIs, ACME, SCEP, EST and Microsoft/private-PKI connectors, but **do not claim support** until matched to the selected CLM platform.

### Targets

Build the real target matrix from discovery: Windows/IIS, Linux/web servers, Java keystores, reverse proxies/load balancers, network/security appliances, container/Kubernetes ingress, cloud certificate services, databases/middleware and endpoints. This list is a discovery taxonomy, not an assertion that StFX uses every target.

### Identity

Integrate with the University's confirmed identity source; map directory groups/roles to CLM roles. Connector credentials should be scoped to required endpoints/actions and rotated independently.

### Observability

Export platform health, lifecycle failures, expiration risk, discovery coverage and audit events to the buyer's confirmed monitoring/SIEM stack. Do not create an isolated operational island.

## Minimum acceptance scenarios

A credible implementation test plan should include at least:

1. discover a seeded certificate and associate it with owner/endpoint;
2. issue a new certificate from each in-scope CA class;
3. deploy through each in-scope native adapter class;
4. validate service health and presented certificate after deployment;
5. execute renewal without service interruption on a representative target;
6. demonstrate failed-deployment handling and rollback/recovery;
7. revoke a certificate and verify lifecycle/audit records;
8. enforce RBAC/approval separation, including denied unauthorized action;
9. prove expiration alerting and escalation;
10. export inventory/audit report and reconcile against a known test set;
11. exercise connector credential rotation;
12. prove backup/recovery or SaaS service-continuity controls as applicable.

Acceptance thresholds (coverage %, timing, availability, RTO/RPO, SLA) remain buyer/vendor gates until the controlling RFP is recovered.

## Security review questions

- Does the platform ever receive, generate, escrow, export or back up private keys?
- Where are secrets/keys stored and who can decrypt/export them?
- What data leaves Canada, if any, and what buyer restrictions apply?
- How are connector credentials scoped, stored and rotated?
- Can audit logs be exported and protected from privileged tampering?
- What tenant-isolation, encryption, vulnerability-management and incident-notification commitments are contractually backed?
- How are administrators authenticated and privileged sessions controlled?
- How are unsupported/deprecated integrations surfaced before they become renewal risk?
