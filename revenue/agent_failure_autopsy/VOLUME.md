# Agent Failure Autopsy volume coordinator

This additive package turns the existing **USD 29 Agent Failure Autopsy** fulfillment contract into a truth-bounded post-purchase work queue. It does **not** create a new offer, replace the canonical fulfillment validator, create or modify Stripe objects, contact buyers, issue refunds, send upsells, or recognize revenue.

Canonical product/fulfillment authority remains:

- `offer.json` for the verified USD 29 one-time offer and provider binding;
- `intake.schema.json` / `report.schema.json` for document shapes;
- `fulfillment.py` for one-run scope, evidence usability, one-business-day clock, independent review, diagnosis/refund, and operator-time truth;
- `RUNBOOK.md` for private-case operations.

`volume.py` consumes only private owner-runtime receipts and the canonical intake/report objects. Every intake/report supplied to an active case is passed through the existing `validate_intake()` / `validate_report()` contract rather than through a second weaker definition of "fulfilled."

## Revenue boundary

A checkout view, payment link, purchase intent, email, Slack message, or caller-authored JSON field is **not** a paid case.

The volume queue admits payment state only through a private runtime envelope with all of these exact fields:

```json
{
  "schema_version": "commons-agent-failure-autopsy-payment-receipt/v1",
  "offer_id": "agent-failure-autopsy-29",
  "case_id": "opaque-case-id",
  "provider": "STRIPE",
  "provider_payment_ref": "pay_<one-way-opaque-hex>",
  "payment_state": "PAID_CONFIRMED",
  "amount_cents": 2900,
  "currency": "USD",
  "observed_at": "2026-09-16T22:00:00Z",
  "provider_receipt_sha256": "<sha256-of-private-provider-readback>",
  "authority_tag": "<hmac-sha256>"
}
```

`authority_tag` is HMAC-SHA256 over the canonical JSON bytes of every field above except `authority_tag`, under 32–128 byte key material retained by the owner runtime. The module verifies this envelope but deliberately exposes **no production signer**. A trusted private adapter must first read the real provider state, one-way redact the provider object ID, hash the retained provider readback, and only then create the envelope.

This HMAC is an internal handoff boundary; it is **not a Stripe signature** and does not independently prove payment without the trusted adapter that performed the provider readback. No provider key, account secret, raw payment object, buyer email, or raw payment ID belongs in this public repository.

Accepted provider states are only:

- `PAID_CONFIRMED`
- `REFUNDED_CONFIRMED`

There is no `PURCHASE_INTENT`, `LINK_OPENED`, `CHECKOUT_STARTED`, `EMAIL_SENT`, or self-authored `PAID` state. The exact amount must remain 2900 cents, currency must remain USD, provider must remain Stripe, and the offer ID must remain the canonical Autopsy offer.

## State machine

The coordinator derives, rather than accepts, operational state:

| Derived state | Meaning |
| --- | --- |
| `WAITING_FOR_SANITIZED_INTAKE` | Provider-confirmed USD 29 payment exists, but no canonical private intake has arrived. The analysis clock has not started. |
| `HOLD_INTAKE` | Canonical intake exists but the existing fulfillment validator says evidence is not yet usable / inside the offer boundary. |
| `ANALYSIS_DUE` | Canonical intake is usable and the deterministic one-business-day deadline has not passed; no final report exists yet. |
| `REFUND_DUE` | A canonical refund report exists, or usable evidence has passed its deterministic deadline without a report. This is a work-queue fact, **not refund authorization**. |
| `DELIVERED` | `fulfillment.py` accepted the exact intake/report as a delivered diagnosis, including independent review for buyer records. |
| `REFUNDED_CLOSED` | A separately provider-confirmed refund receipt exists. The case cannot re-enter analysis. |

Coordinator and backup are distinct opaque seat/operator references. The queue sorts refund-due work ahead of analysis-due work, then intake holds/waits, then closed work. `max_active_cases` produces explicit slot/backlog truth; it never drops cases or weakens quality.

Operational SLA time comes from process UTC. `compile_volume()` has **no caller `as_of` parameter**, preventing a caller from backdating the queue to avoid a missed-deadline refund. Tests patch the process clock only inside the test process to make synthetic cases deterministic.

## Refund boundary

`REFUND_DUE` means the private operator must execute the existing runbook's provider refund action. It is not permission for this module to touch Stripe.

Every row and aggregate output fixes:

```text
external_action_authorized = false
automatic_outreach_authorized = false
automatic_charge_or_refund_authorized = false
cash_or_revenue_recognized = false
```

A provider-confirmed `REFUNDED_CONFIRMED` receipt is terminal and contributes zero analysis capacity and zero follow-on eligibility.

## Follow-on eligibility, not automatic outreach

The compiler can record a next-offer **eligibility state**, but it never sends or charges anything.

Follow-on facts are a second private authenticated envelope:

- `NO_FOLLOW_ON_EVIDENCE`
- `SECOND_FAILED_RUN_OBSERVED`
- `IMPLEMENTATION_REQUEST_OBSERVED`
- `AMBIGUOUS_FOLLOW_ON`

Each envelope binds the case, observed UTC time, one retained-evidence SHA-256, and a bounded related-failed-run count under a separate runtime HMAC key.

Eligibility is considered only after canonical `DELIVERED`:

- no follow-on evidence -> `NONE`;
- a separately observed second related failed run (`count >= 2`) -> `$199_DIAGNOSTIC`;
- a separately observed implementation request -> `OWNER_REVIEW`;
- ambiguous or missing authenticated follow-on evidence -> `OWNER_REVIEW`.

The `$199_DIAGNOSTIC` label refers only to the already-canonical verified USD 199 diagnostic family linked from the Autopsy product surfaces. It does not choose a buyer-specific SKU and it does not authorize a message.

There is deliberately **no `$2500_SURVIVAL` state**. The source census performed before this carrier found no current canonical Autopsy-adjacent USD 2,500 product. Implementation interest therefore routes to `OWNER_REVIEW` until a separate source-verified offer exists. The volume engine will not invent a high-ticket product or price.

## Private / public split

The private output contains opaque case refs, coordinator/backup refs, authenticated receipt hashes, exact SLA state, canonical intake/report/fulfillment hashes, capacity state, and descriptive fulfillment economics.

The public summary contains only aggregate counts and capacity. It explicitly declares that buyer identifiers, provider payment refs, and payment amount totals are excluded. Do not publish the private output or live case input.

Both outputs carry deterministic SHA-256 receipts. `verify_compiled_volume()` recomputes the private/public receipt binding and authority-false fields. It is an **integrity verifier**, not payment authority: anyone can hash JSON; payment authority exists only at compile time when the owner runtime verifies authenticated provider-readback envelopes.

## Fulfillment economics

The volume engine reads reviewer/draft minutes only from a report already accepted by the canonical fulfillment validator. Aggregate time is private and labeled:

```text
DESCRIPTIVE_ECONOMICS_ONLY
quality_truncation_authorized = false
```

Capacity and operator-time measurement may tell us whether the USD 29 unit is operationally efficient. They may never truncate analysis, skip independent review, weaken evidence quality, or override the existing refund contract.

## CLI

The CLI expects a private JSON array of case records. Runtime keys are supplied only through environment variables as hex bytes:

```bash
export AUTOPSY_PAYMENT_AUTH_KEY_HEX='<private-runtime-key-as-hex>'
export AUTOPSY_FACTS_AUTH_KEY_HEX='<separate-private-runtime-key-as-hex>'

python -m revenue.agent_failure_autopsy.volume \
  /owner-private/autopsy-cases.json \
  --max-active-cases 4 \
  --private-output /owner-private/autopsy-volume-private.json \
  --public-output /tmp/autopsy-volume-public.json
```

Outputs are create-exclusive (`O_EXCL`) and mode `0600`. An existing output is not overwritten. No production key or valid paid-case fixture is checked into this repository.

## Acceptance / hostile proof

Run:

```bash
python -m py_compile \
  revenue/agent_failure_autopsy/volume.py \
  test_agent_failure_autopsy_volume.py

python -m unittest -v test_agent_failure_autopsy_volume.py
python -O -m unittest -v test_agent_failure_autopsy_volume.py
```

The root test creates only synthetic, test-key-signed envelopes. It covers:

- caller-authored or wrong-key "paid" receipts;
- post-signature amount tamper;
- noncanonical amount, currency, provider, and purchase-intent states;
- future-dated payment/follow-on facts;
- duplicate case IDs and payment-ref replay across cases;
- payment-to-case mismatch;
- same-seat coordinator/backup;
- canonical intake validation and the actual one-business-day deadline;
- overdue no-report -> `REFUND_DUE`;
- provider-confirmed refund -> terminal `REFUNDED_CLOSED`;
- report-without-intake and canonical report drift;
- delivered report receipt binding;
- `$199_DIAGNOSTIC` only after delivery + authenticated second-run evidence;
- implementation evidence -> `OWNER_REVIEW`, never an invented USD 2,500 offer;
- forged follow-on facts and insufficient second-run count;
- capacity/backlog math and queue priority;
- public redaction;
- hard-false outreach/charge/refund/revenue fields;
- receipt tamper detection;
- descriptive economics without a quality cap;
- rejection of caller clock injection;
- create-exclusive CLI behavior.

## Authority ceiling

This package never:

- contacts a buyer or asks Muse to send on its own;
- reads or writes Stripe;
- issues a refund or charge;
- remints the USD 29 product or any existing USD 199 product;
- creates a higher-ticket SKU;
- infers payment from purchase intent;
- infers revenue from an authenticated payment handoff;
- publishes buyer artifacts;
- schedules analysis without provider-confirmed payment plus canonical intake;
- weakens the existing Autopsy evidence, review, or refund contract.

The owner-controlled private adapter remains responsible for provider readback and for deciding whether any `OWNER_REVIEW` / `$199_DIAGNOSTIC` eligibility should ever become a separately arbitrated outreach action.
