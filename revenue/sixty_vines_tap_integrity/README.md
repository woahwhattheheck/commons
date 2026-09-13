# Sixty Vines Tap-to-Table Integrity Rail — synthetic delivery core

This package is the offline, deterministic delivery core behind the **Sixty Vines San Antonio / La Cantera Tap-to-Table Integrity Rail** offer. It turns an approved synthetic event ledger into a content-addressed reconciliation receipt. It is intentionally **not** a POS integration, guest system, inventory writer, payment processor, alcohol-service decision engine, or production deployment.

## What it proves

The core models the operating lineage that must remain attributable across 60 taps:

`approved wine/SKU -> keg/lot -> tap/line -> cleaning/status -> pour-size -> table/check -> synthetic monetary/inventory effect`

It fails closed before recording a synthetic effect when it sees:

- an unknown tap, keg, lot, or line;
- a SKU assigned to the wrong tap;
- a keg not assigned to the named tap;
- a line that is on HOLD/CLEANING or whose cleaning evidence is missing/overdue;
- insufficient keg volume;
- an exact-effect retry under a different event ID;
- a duplicate pour ID;
- a refund/void conflict or refund above the remaining reversible amount;
- a timeout/unknown-effect state that has not been explicitly reconciled.

Exact duplicate event retries are deduplicated by full canonical event bytes. Reusing an `event_id` with different bytes is a hard replay error. Input order does not matter: unique sequence numbers define the canonical ledger order, so shuffled copies of the same ledger produce the same state and receipt hashes.

## UNKNOWN_EFFECT contract

`POUR_UNKNOWN` records the intended synthetic effect but applies **no** inventory or monetary change. The same effect ID is blocked from retry while unresolved.

A later `RESOLVE_POUR` must say exactly one of:

- `APPLIED` — apply the stored intended effect once; or
- `NOT_APPLIED` — close the ambiguity without applying it.

This is the fail-closed timeout-after-commit boundary. The package never guesses.

## Acceptance generator

`rail.py acceptance` deterministically creates the full synthetic acceptance ledger:

- **20,000 unique events**
- **60 configured taps**
- periodic line-cleaning evidence
- pours across every tap
- waste events
- refund lineage
- timeout/unknown-effect events followed by explicit reconciliation
- no external calls

The locally proven receipt committed with this package reports:

- 20,000 processed / unique events
- 60/60 taps with accepted pours
- 18,294 applied synthetic effects
- 0 holds
- 0 unresolved unknown effects
- receipt SHA-256 `ee0ccafe168f4d4504f0c54cb18680558469e96bc1bd6ac5b5a72edcc00f8f41`

Those values are a **synthetic regression result**, not a buyer acceptance, production result, alcohol/inventory/payment effect, or recognized revenue.

## Run

From this directory:

```bash
python -m unittest -v test_rail.py
python -O -m unittest -v test_rail.py
python -m py_compile rail.py test_rail.py

python rail.py acceptance \
  --events 20000 \
  --taps 60 \
  --receipt acceptance_receipt.example.json \
  --require-pass

python rail.py verify-receipt acceptance_receipt.example.json
```

A passing acceptance run requires:

1. zero holds;
2. zero unresolved unknown effects; and
3. pours on every configured tap.

The offline receipt verifier checks the receipt's canonical SHA-256 binding. It is a tamper-evidence mechanism, **not** a digital signature or an identity/authentication claim.

## Test coverage

`test_rail.py` currently contains 27 hostile regression tests covering:

- valid pour inventory/money accounting;
- exact retry dedupe;
- conflicting event-ID rejection;
- duplicate effect-ID suppression;
- wrong-line, lot mismatch, unavailable-line, overdue-cleaning, and insufficient-volume holds;
- waste as inventory-only effect;
- partial refund, refund cap, void, and refund/void conflict rules;
- UNKNOWN_EFFECT apply / not-applied / retry-block behavior;
- shuffled-input deterministic replay;
- duplicate sequence rejection;
- invalid line status and duplicate line configuration;
- exact 20,000-event / 60-tap acceptance;
- generator byte determinism;
- receipt tamper detection;
- offline CLI receipt verification;
- hostile negative and boolean amount rejection.

The same 27 tests are run in normal Python and under `python -O` so safety rules do not depend on `assert`.

## Explicit boundary

This package does **not**:

- ingest guest names, contact information, ages, or other guest PII;
- verify age or authorize alcohol service;
- choose wines, pairings, menus, pricing, comps, refunds, or service decisions;
- call, write, or mutate a POS, payment processor, inventory system, reservation system, tap controller, or provider account;
- service or clean a line;
- initiate inventory movement or monetary movement;
- deploy anything;
- establish regulatory compliance, production readiness, buyer acceptance, a contract, booked revenue, or payment.

A real implementation would require buyer-approved schemas, system boundaries, roles, source-of-truth rules, cleaning/status policy, POS/inventory/provider adapters, identity/access controls, independent security/operational validation, golden fixtures, and signed human acceptance.
