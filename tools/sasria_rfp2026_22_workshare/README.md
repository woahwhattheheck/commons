# Sasria RFP2026/22 — TJLabs workshare acceptance package

**State:** internal readiness only. `PROPOSED_NOT_ACCEPTED`. Fee intentionally `TO_BE_AGREED`.

This package records a public-source, self-attested workshare proposal without asserting that Netcampus is bidding, that it accepted TJLabs, or that TJLabs may contact Sasria, submit a bid, certify compliance, or mutate a training environment.

## Live public source receipt

Observed from Sasria's public eTender detail page on 2026-09-17 at 00:56:02 EDT / 06:56:02 SAST:

- issuer: Sasria SOC Ltd
- RFP: `2026/22`
- title: `Appointment of Service Provider for Artificial Intelligence Training`
- portal state: `Published`
- portal close: `2026-09-17 10:00 AM` (encoded as `+02:00` in `scope.json`)
- queries deadline: `2026-09-13 10:00 PM`
- public detail: <https://procurement.sasria.co.za/tender-details/246>
- four tender filenames were visible; their bodies were not readable through the current connector and are **not represented as reviewed**.

The prior fleet assumption of a 12:00 SAST close is deliberately rejected by tests.

## Proposed specialist boundary

TJLabs' nonexclusive proposed workshare is limited to:

1. Responsible-AI control/evidence mapping tied to prime-approved curriculum.
2. Six role-pathway acceptance-criteria slots.
3. Hands-on lab QA matrix.
4. Deterministic pre/post assessment pack.
5. Versioned evidence and exception pack.
6. Governance/evidence handoff.

Netcampus, if it elects to pursue and contract, remains prime and owns all South African procurement/compliance documents, accreditation/certification evidence, facilitators/references, platform access, bid pricing, signatory authority and submission authority. TJLabs needs no learner PII beyond opaque identifiers and makes no independent legal/compliance certification.

## Self-attested generation boundary

This v1 package is deliberately **not a locally upgradable release contract**. It can validate only the frozen public-source snapshot:

```bash
python tools/sasria_rfp2026_22_workshare/validate_scope.py tools/sasria_rfp2026_22_workshare/scope.json
python tools/sasria_rfp2026_22_workshare/validate_scope.py --release tools/sasria_rfp2026_22_workshare/scope.json
```

The first command validates the self-attested snapshot. The second must **always HOLD**. Editing local booleans, document-read flags, counterparty state, release status, or pathway text can never convert this generation into prime-backed readiness.

A future prime-backed transition requires a separate successor generation that retains evidence identities/digests and provenance for the controlling tender bodies, prime assertions, role criteria and authorization. Those facts are intentionally not accepted as free text in this schema.

## Input and data-minimization boundary

The CLI rejects duplicate JSON keys and non-finite numbers. Every object has an exact key contract. Current free-text receipt content is frozen to the public-source observation, and role acceptance criteria must remain empty in this generation. Extra fields, contact data, secret-shaped strings or locally authored "prime approved" criteria therefore cannot be smuggled into the retained package.

Even a future evidence-bound package would not automatically grant outbound-email or bid-submission authority; those remain separate Muse/provider/prime actions.
