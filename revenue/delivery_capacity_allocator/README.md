# Delivery Capacity Allocator

`delivery-capacity-allocation/v1` is a buyer-neutral, offline post-acceptance capacity control for scarce service delivery windows.

Commons already tracks one deal truthfully and can prioritize pre-sale pursuits. This package solves a different problem: **multiple individually valid accepted/funded deals must not all be planned against the same bounded delivery capacity.** It consumes a capacity-policy generation, a deal-demand generation, and an active-reservation generation, conserves active reservations first, then deterministically proposes whole-slot allocations for owner review.

## Allocation contract

Only explicit `BUYER_ACCEPTED` and `FUNDED_TO_START` rows compete for new capacity. No outreach, proposal, configured payment route, or internal optimism is treated as acceptance. Existing active reservations consume slot units before new work is considered. A deal is never partially allocated: its requested units fit one compatible slot in the deal window or the result is `CAPACITY_HOLD`.

Priority is deterministic: `FUNDED_TO_START` before `BUYER_ACCEPTED`, then earliest deadline, earliest acceptance time, and stable deal ID. Input array order does not change the semantic allocation or `allocation_sha256`; the outer receipt remains bound to the exact retained source bytes and therefore changes when raw source bytes change.

Fail-closed conditions include stale/future source generations, reservation overdraw, unknown reservation slots, service mismatch, one deal with multiple active reservations, and reservation-to-deal identity rebinding. These conditions hold the global capacity state rather than guessing around corrupted custody.

## Trust boundary

The CLI requires the exact SHA-256 of policy, demand, and reservation bytes. Those roots are **host-retained inputs**; this package does not claim a caller-provided digest authenticates Gmail, Stripe, GitHub, a buyer, a scheduler, or another provider. Upstream integrations must acquire and retain those roots through their own trusted boundary.

`verify` first recompiles the exact historical receipt at its recorded evaluation instant, then independently reevaluates currentness using process UTC. A once-valid allocation does not remain current after any input snapshot ages out.

## Authority ceiling

Every receipt keeps these false: buyer contact, schedule commitment, provider send, payment mutation, contract acceptance, staffing commitment, deployment, and revenue recognition. `ALLOCATED_FOR_OWNER_REVIEW` means capacity exists under the supplied current generations; it is not a promise to a buyer and does not reserve an external calendar/provider by itself.

## CLI

```bash
python -m revenue.delivery_capacity_allocator.cli compile \
  --policy policy.json --demands demand.json --reservations reservations.json \
  --policy-sha <sha256> --demand-sha <sha256> --reservations-sha <sha256> \
  --out allocation.json

python -m revenue.delivery_capacity_allocator.cli verify \
  --policy policy.json --demands demand.json --reservations reservations.json \
  --policy-sha <sha256> --demand-sha <sha256> --reservations-sha <sha256> \
  --receipt allocation.json
```

Inputs are bounded strict UTF-8 JSON with duplicate/non-finite rejection. CLI reads only stable regular-file generations and writes create-exclusively without pathname cleanup that could delete foreign replacements.

## Validation

```bash
python -m py_compile revenue/delivery_capacity_allocator/*.py
python -m unittest -v revenue.delivery_capacity_allocator.test_engine
python -O -m unittest -v revenue.delivery_capacity_allocator.test_engine
```
