# Opportunity Portfolio Live Intake

`revenue/opportunity_portfolio_intake` is the offline composition layer between normalized live swarm evidence and the already-landed `revenue/opportunity_portfolio` allocator.

It exists for one operational failure mode: multiple workers can see the same lead, bid, contest, bounty, or service lane while their views of TAKE/RELEASE/DNR/closure state differ. Hand-normalizing that state near an external action makes same-minute duplicate execution easy. This package folds one **complete, explicitly bounded snapshot** before the allocator sees the opportunity.

## What it consumes

The intake packet keeps two categories separate:

- **facts**: the allocator-native source, freshness, deadline, eligibility, exact integer value/probability evidence, capacity, static blockers, dependencies, exclusivity, and labels. Status events cannot rewrite any of these fields.
- **events**: typed evidence only — `TAKE`, `RELEASE`, `EXPIRE`, `BLOCKER_OPEN`, `BLOCKER_RESOLVED`, `DNR`, `BUYER_REOPEN`, `CLOSED`, and `SHIPPED`. Every event has a stable ID and exact source ref/digest/time.

Exact replay of the same event ID collapses. Reusing an event ID with changed bytes fails closed. Events are reduced in `(observedAt,eventId)` order, so array ordering is not authority.

`DNR` is an execution blocker, **not** an eligibility rewrite. Generic blocker-resolution events cannot clear it. Only a later typed `BUYER_REOPEN` whose origin is literally `BUYER` resolves DNR. Internal TAKE/RELEASE activity never does. `CLOSED` and `ALREADY-SHIPPED` are terminal blockers in v1.

## Custody semantics

With a complete custody snapshot:

- zero active TAKEs -> allocator owner `AVAILABLE`;
- exactly the compiling actor -> `OWNED_BY_THIS_SEAT`;
- exactly one other actor -> `OWNED_BY_OTHER`;
- more than one active actor -> `UNKNOWN` plus open `OWNER-COLLISION`.

An unmatched `RELEASE`/`EXPIRE` in a snapshot declared complete produces `CUSTODY-HISTORY-CONFLICT`. An incomplete custody or status inventory produces an explicit open blocker and can never manufacture an executable lane through absence.

## Downstream authority

Compilation calls the real merged `revenue.opportunity_portfolio.normalize_input()` and `compile_portfolio()` functions. The intake receipt binds the normalized source packet, folded owner/blocker projection, exact allocator input, and allocator receipt digest, then verifies by full recompilation.

The adapter is read-only. Every receipt fixes these to false: contact, send, submission, merge, spend, payment mutation, buyer acceptance, and revenue recognition authority. A portfolio `EXECUTE_NOW` result is still human execution review, exactly as defined by the downstream allocator; this package does not add provider authority.

## CLI

```bash
python -m revenue.opportunity_portfolio_intake.cli compile intake.json \
  --trusted-as-of 2026-09-14T01:00:00Z \
  --portfolio-input portfolio-input.json \
  --receipt intake-receipt.json

python -m revenue.opportunity_portfolio_intake.cli verify intake-receipt.json
```

Input reads are bounded, strict UTF-8/JSON, duplicate-key rejecting, no-follow regular-file reads. Outputs are create-exclusive and fsynced; existing files are never overwritten.
