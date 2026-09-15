# Service Deal Economics Desk

An offline, evidence-bound owner-review control for one proposed services deal. It answers a narrow but commercially important question: **does the proposed price cover the supplied delivery cost/risk policy, and does the supplied current capacity snapshot have enough unreserved minutes for this scope?**

This is deliberately not a CRM, proposal sender, contract system, staffing scheduler, capacity allocator, accounting system, or revenue ledger. It never reserves hours. It never converts a hot lead, reply, proposal, acceptance, payment route, merge, or historical sale into current buyer/cash/revenue truth.

## What it computes

For every line item, labor cost is conservatively rounded up:

`ceil(planned_minutes * internal_rate_cents_per_hour / 60)`

Then:

- direct cost = labor + explicit external cost;
- risk reserve = `ceil(direct_cost * risk_reserve_bps / 10000)`;
- loaded delivery cost = direct cost + reserve;
- minimum price = the smallest integer-cent price satisfying the owner policy gross-margin floor;
- available capacity = supplied total minutes - already-reserved minutes;
- proposed demand = exact sum of line-item minutes;
- capacity shortfall = positive excess demand only.

Possible states are `READY_FOR_OWNER_QUOTE_REVIEW`, `HOLD_MARGIN`, `HOLD_CAPACITY`, `HOLD_MARGIN_AND_CAPACITY`, and `HOLD_EVIDENCE`. Future/stale evidence, currency/window mismatch, and an overdrawn supplied capacity snapshot fail closed to `HOLD_EVIDENCE`.

## Authority and adjacency

This product is **per-deal feasibility**, not portfolio allocation. Commons issue #14124 owns post-acceptance allocation of scarce capacity across multiple accepted/funded deals. This desk consumes a separately supplied capacity snapshot and cannot create or change a reservation.

A READY result means only that a human owner may review a proposed price/scope using the supplied evidence. All external authority is hard-false: no buyer contact, quote commitment, acceptance, contract, staffing commitment, payment, cash, or booked/recognized revenue.

## CLI

Production CLI owns the current UTC clock. There is intentionally no `--as-of` production switch.

```bash
python -m revenue.service_deal_economics.cli compile input.json report.json --markdown report.md
python -m revenue.service_deal_economics.cli verify input.json report.json
```

The library accepts explicit time only for hermetic tests/historical analysis. Current verification first reproduces the exact historical receipt, then re-evaluates current freshness/semantics and quote-validity.

Inputs use strict duplicate-key JSON, canonical whole-second UTC, safe integer cents/minutes, lowercase SHA-256 evidence digests, bounded opaque IDs, exact schemas, no floats, and bool-not-int validation. File ingress is bounded regular-file/no-follow where supported; outputs are create-exclusive and refuse overwrite/final symlink.

## Commercial hypothesis

Potential productization for agencies/consultancies/MSPs: a bounded quote-economics setup and operating desk (for example, fixed-scope setup plus recurring scenario reviews). Any number here is a seller hypothesis until a buyer separately accepts and pays; this repository does not claim a sale or recognized revenue.
