# Commercial offer → scope-to-delivery bridge

This package closes the evidence boundary between the landed
`revenue/commercial_offer_contract` rail and the existing
`host/scope_to_delivery.py` composer.

It does **not** infer buyer acceptance from a sent offer. A commercial offer's
`BUYER_ACCEPTANCE_EVIDENCE_CAPTURED` state intentionally leaves
`buyer_acceptance_verified=false` and `fulfillment_authorized=false`. The bridge
requires a separate authorized-operator verification receipt before it can emit
an accepted `commons-scope-agreement/v1`.

## Authority model

The bridge requires two independently evidenced buyer facts:

1. acceptance of the exact commercial offer; and
2. acceptance of the exact delivery schedule used by `scope_to_delivery`.

The second requirement is deliberate. The scope agreement's canonical terms
digest includes its delivery window, so an operator-only schedule chosen after
buyer acceptance cannot truthfully be represented as written acceptance of the
exact terms. `schedule_acceptance` therefore binds the window, a buyer-evidence
digest, an identity-verification digest, and the acceptance timestamp. The
operator verification HMAC covers both offer-acceptance and schedule-acceptance
evidence.

For the same reason, v1 does not accept a post-hoc catalog mapping. The accepted
commercial offer's `opportunity_id` must already equal a canonical Commons
catalog SKU. The accepted USD total must equal that listing's exact two-decimal
catalog total.

## Output

`build_scope_bridge()` emits:

- a canonical `commons-scope-agreement/v1` that the existing validator accepts;
- the operator-verification receipt; and
- a content-addressed bridge receipt.

The agreement derives rather than retypes:

- opaque buyer identity;
- exact accepted price/currency;
- accepted deliverables and acceptance criteria;
- each deliverable's evidence commitment;
- accepted exclusions; and
- the exact accepted offer SHA-256.

`refund_choice` is conservatively `UNKNOWN`; the bridge never invents a refund
promise. Raw destination/contact identity is not retained.

The strongest bridge state is `SCOPE_AGREEMENT_READY`. External send,
fulfillment, invoice/payment mutation, cash, and revenue-recognition authority
remain false.

## Example

```python
from revenue.commercial_offer_to_delivery import (
    build_scope_bridge,
    create_operator_verification,
)

verification = create_operator_verification(
    accepted_offer_contract,
    owner_secret,
    acceptance_verification_secret,
    verifier_id="operator-001",
    key_id="acceptance-key-v1",
    verified_at="2026-09-13T10:06:00Z",
    public_ref="p/accepted-offer.md",
    schedule_acceptance={
        "start": "2026-09-14T13:00:00Z",
        "end": "2026-09-18T21:00:00Z",
        "timezone": "America/Kentucky/Louisville",
        "accepted_at": "2026-09-13T10:05:00Z",
        "evidence_sha256": "...64 lowercase hex...",
        "identity_verification_sha256": "...64 lowercase hex...",
    },
    trusted_now="2026-09-13T10:10:00Z",
)

bundle = build_scope_bridge(
    accepted_offer_contract,
    verification,
    owner_secret,
    acceptance_verification_secret,
    catalog=canonical_catalog,
    trusted_now="2026-09-13T10:10:00Z",
)
```

The HMAC secrets are runtime inputs and are never embedded in the output.

## Validation

From repository root:

```bash
python -m unittest discover -v -s revenue/commercial_offer_to_delivery -t . -p 'test_*.py'
python -O -m unittest discover -v -s revenue/commercial_offer_to_delivery -t . -p 'test_*.py'
python -m py_compile revenue/commercial_offer_to_delivery/*.py
```

Pre-publication isolated-source evidence on 2026-09-13:

- 33/33 executable hostile/lifecycle tests PASS normally;
- 33/33 PASS under `python -O`;
- one landed-rail integration test is intentionally skipped only when the
  pre-existing Commons modules are absent from the isolated packet; in-repo CI
  runs it against the real commercial-offer and scope validators;
- deterministic acceptance corpus: 256/256 PASS, manifest SHA-256
  `cb0fbb78c04ad2472b55c8558195e6237cb80ca1aac7f04e88e8f67bd2a5ae71`;
- `py_compile` PASS.

No provider call, buyer contact, signature, fulfillment, checkout/payment,
invoice, cash assertion, or recognized-revenue action is performed.
