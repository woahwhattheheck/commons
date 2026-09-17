# Sasria RFP2026/22 — TJLabs workshare acceptance package

**State:** internal readiness only. `PROPOSED_NOT_ACCEPTED`. Fee intentionally `TO_BE_AGREED`.

This package turns the warm Netcampus teaming thread into a fail-closed acceptance contract without asserting that Netcampus is bidding, that it accepted TJLabs, or that TJLabs may contact Sasria, submit a bid, certify compliance, or mutate a training environment.

## Live public source receipt

Observed from Sasria's public eTender detail page on 2026-09-17 at 00:56:02 EDT / 06:56:02 SAST:

- issuer: Sasria SOC Ltd
- RFP: `2026/22`
- title: `Appointment of Service Provider for Artificial Intelligence Training`
- portal state: `Published`
- portal close: `2026-09-17 10:00 AM` (encoded as `+02:00` in `scope.json` because Sasria is in South Africa)
- queries deadline: `2026-09-13 10:00 PM`
- public detail: <https://procurement.sasria.co.za/tender-details/246>
- four tender filenames were visible; their bodies were not readable through the current connector and therefore **are not represented as reviewed**.

The prior fleet assumption of a 12:00 SAST close is deliberately rejected by tests.

## Proposed specialist boundary

TJLabs' nonexclusive proposed workshare is limited to:

1. Responsible-AI control/evidence mapping tied to prime-approved curriculum.
2. Six role-pathway acceptance-criteria slots (empty until prime supplies the controlling pathways/requirements).
3. Hands-on lab QA matrix.
4. Deterministic pre/post assessment pack.
5. Versioned evidence and exception pack.
6. Governance/evidence handoff.

Netcampus, if it elects to pursue and contract, remains prime and owns all South African procurement/compliance documents, accreditation/certification evidence, facilitators/references, platform access, bid pricing, signatory authority and submission authority. TJLabs needs no learner PII beyond opaque identifiers and makes no independent legal/compliance certification.

## Fail-closed release contract

`validate_scope.py` has two modes:

```bash
python tools/sasria_rfp2026_22_workshare/validate_scope.py tools/sasria_rfp2026_22_workshare/scope.json
python tools/sasria_rfp2026_22_workshare/validate_scope.py --release tools/sasria_rfp2026_22_workshare/scope.json
```

The first validates the current internal package. The second must remain HOLD until the controlling tender bodies are actually read, the prime confirms every gate, and all six role pathways have prime-approved acceptance criteria.

Even a release-ready package **never grants outbound-email or bid-submission authority**. Those remain separate Muse/provider/prime actions.
