# Revenue Closure Queue

`tools/revenue_closure` is a deterministic, dependency-free compiler for the
commercial gap between **qualified work** and **truthful closure**.

It does not send messages, create or activate checkout/payment rails, touch
provider accounts, move money, deliver customer work, or claim cash. It turns
explicit evidence into a ranked queue of the next bounded state transition.

## Why this exists

Commons has several strong point tools:

- qualification / funded-work freshness;
- payment-ready evidence and outreach receipts;
- delivery/acceptance artifacts;
- settlement proof ledgers.

Those tools answer different questions. A qualified opportunity can still die
between them if a worker cannot distinguish:

- a hard do-not-resend from a permitted follow-up;
- a reply that needs a quote from a quote awaiting buyer decision;
- an accepted quote that lacks a collection rail;
- pending/authorized payment from settled payment;
- delivery-ready work from delivered-but-unaccepted work;
- earned value from settled cash.

This compiler makes that boundary explicit without inventing authority.

## Side-effect boundary

`compiler.py` is pure local computation plus an optional atomic output file.
`action_ready=true` means only that the **evidence state has a non-waiting next
step**. It is **not** authorization to contact a person, alter a provider,
create a checkout, capture funds, spend money, publish, deploy, or claim
revenue. External action still requires whatever authority that system,
customer, program, or owner demands.

Likewise:

- `expected_value_cents` is pipeline face value, **not cash**;
- `actionable_value_cents_by_currency` is a queue metric, **not booked revenue**;
- `CLOSED_WON` requires explicit `payment=SETTLED` and
  `settlement=SETTLED`; the compiler never promotes authorization or intent;
- stale evidence makes the entire output non-authoritative and every row
  `HOLD_STALE_EVIDENCE`.

## Contract

Input is strict JSON. Duplicate keys, `NaN`/`Infinity`, coercive bool-as-int
money, unknown keys, future evidence, unsafe IDs, malformed timestamps,
duplicate opportunity IDs, and contradictory commercial states fail closed.

Top-level fields:

- `schema_version`: `1`
- `evidence_generated_at`: exact UTC second (`...Z`)
- `max_age_seconds`: 60..2,678,400
- `opportunities`: up to 10,000 rows

Each opportunity carries:

- immutable `opportunity_id`;
- whole-number `expected_value_cents` + three-letter `currency`;
- `qualification`: `ACTIONABLE | HOLD | REJECT`;
- contact state and explicit `do_not_resend`;
- offer / collection / payment / delivery / settlement evidence;
- policy for follow-up cooldown, payment timing, and delivery acceptance;
- optional deadline.

See `schemas/input.schema.json`. Runtime validation is stricter than JSON
Schema because it also enforces cross-field state consistency.

## Decisions

The compiler can emit:

```text
HOLD_STALE_EVIDENCE
HOLD_QUALIFICATION
STOP_REJECTED
STOP_DNR
STOP_DEADLINE_PASSED
INITIAL_CONTACT_READY
CONTACT_ROUTE_REPAIR
WAIT_FOLLOWUP
FOLLOW_UP_READY
QUOTE_READY
AWAIT_QUOTE_DECISION
REQUOTE_READY
COLLECTION_RAIL_REQUIRED
ACTIVATE_COLLECTION_RAIL
REQUEST_PAYMENT
AWAIT_PAYMENT
PAYMENT_RECOVERY
PREPARE_DELIVERY
FULFILLMENT_READY
AWAIT_DELIVERY_ACCEPTANCE
EARNINGS_EVIDENCE_REQUIRED
SETTLEMENT_PENDING
CLOSED_WON
CLOSED_LOST
CLOSED_REVERSED
```

Terminal and wait states are never marked `action_ready`.

Priority is deterministic and intentionally simple: decision class first,
nearest deadline second, highest face value third, opportunity ID last.
Nothing in priority changes authority or money truth.

## Run

```bash
python3 tools/revenue_closure/compiler.py \
  tools/revenue_closure/examples/pipeline.json \
  --as-of 2026-09-13T08:00:00Z

python3 tools/revenue_closure/compiler.py \
  tools/revenue_closure/examples/pipeline.json \
  --as-of 2026-09-13T08:00:00Z \
  --output /tmp/revenue-closure.json
```

`--as-of` is required so the same evidence and evaluation time produce the
same result. Output files are written through a same-directory temporary file
and `Path.replace()`.

The example contains four deliberately different truths:

- a contacted GGUF-style lane with hard DNR → `STOP_DNR`;
- a partner reply with only a draft quote → `QUOTE_READY`;
- accepted work with payment pending → `AWAIT_PAYMENT`;
- accepted delivery with earned-but-unsettled value → `SETTLEMENT_PENDING`.

## Verify

```bash
python3 -m unittest -v tools.revenue_closure.tests.test_compiler
python3 -O -m unittest -v tools.revenue_closure.tests.test_compiler
python3 -m py_compile tools/revenue_closure/compiler.py
```

The regression suite covers strict parsing, commercial consistency, stale and
future evidence, DNR/follow-up fences, both payment-timing policies,
quote/payment/delivery/settlement transitions, deterministic ordering,
digest stability, atomic output, and CLI failure behavior.
