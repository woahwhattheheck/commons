# Delivery Capacity Allocator

`delivery-capacity-allocation/v1` is a buyer-neutral, offline post-acceptance capacity control for scarce service delivery windows.

Commons already tracks one deal truthfully and can prioritize pre-sale pursuits. This package solves a different problem: **multiple individually valid accepted/funded deals must not all be planned against the same bounded delivery capacity.** It consumes a capacity-policy generation, a deal-demand generation, and an active-reservation generation, conserves active reservations first, then deterministically proposes whole-slot allocations for owner review.

## Allocation contract

Only explicit `BUYER_ACCEPTED` and `FUNDED_TO_START` rows can compete for new capacity. No outreach, proposal, configured payment route, or internal optimism is treated as acceptance. Existing active reservations consume slot units before new work is considered. A deal is never partially allocated: its requested units fit one compatible live slot in the deal window or the result is `CAPACITY_HOLD`.

Priority is deterministic: `FUNDED_TO_START` before `BUYER_ACCEPTED`, then earliest deadline, earliest acceptance time, and stable deal ID. Input array order does not change the semantic allocation or `allocation_sha256`; the outer receipt remains bound to the exact source bytes and therefore changes when raw source bytes change.

Temporal/current-state fences are strict. A capacity-eligible deal with a future `accepted_at` globally holds. New allocations cannot use a slot whose delivery window has already ended at the trusted evaluation instant. An ACTIVE reservation against an ended slot also holds current state. ACTIVE reservations whose deal lineage is missing still consume their claimed slot units and additionally emit `ACTIVE_RESERVATION_ORPHAN_DEAL`; unverifiable lineage never frees scarce capacity or leaves the allocator CURRENT.

Other fail-closed conditions include stale/future source generations, reservation overdraw, unknown reservation slots, service mismatch, one deal with multiple active reservations, and reservation-to-deal identity rebinding. These conditions hold the global capacity state rather than guessing around corrupted custody.

## Trust boundary

There are two deliberately different interfaces:

- `compile_bytes(...)`, `verify_historical_bytes(...)`, and the compatibility name `verify_current_bytes(...)` are **historical/test integrity primitives**. Their expected roots and optional clock originate with the caller. `compile_bytes(...)` therefore emits `HISTORICAL_INTEGRITY_ONLY` (or a historical hold), never `CURRENT`; `verify_current_bytes(...)` cannot return true under this caller-bound authority model. These APIs may prove byte self-consistency for replay/testing, but they cannot authorize scheduling, staffing, or a buyer commitment.
- The production CLI uses `compile_current_bytes(...)` / `verify_current_receipt_bytes(...)`. It owns current UTC and accepts **no caller-selected root as authority**.

This package does not yet have an independently retained root registry, signed upstream receipt store, or other trusted reacquisition path for the current policy/demand/reservation generations. Therefore the production-current boundary intentionally fails closed with `HOLD_RETAINED_ROOT_AUTHORITY` and `RETAINED_ROOT_AUTHORITY_UNAVAILABLE`. It will not relabel hashes computed from the same caller-supplied bytes as trusted roots. A future integration may remove that hold only by wiring an independent retained-root authority and hostile-testing that boundary.

Legacy `--policy-sha`, `--demand-sha`, and `--reservations-sha` CLI switches are accepted silently for compatibility with older callers but ignored by the production-current authority path.

## Authority ceiling

Every receipt keeps these false: buyer contact, schedule commitment, provider send, payment mutation, contract acceptance, staffing commitment, deployment, and revenue recognition. Even a historical/test `ALLOCATED_FOR_OWNER_REVIEW` means only that the supplied generations fit the modeled capacity constraints at that supplied evaluation instant. It is not a promise to a buyer and does not reserve an external calendar/provider by itself. The production CLI remains HOLD until independent retained-root authority exists.

## CLI

```bash
python -m revenue.delivery_capacity_allocator.cli compile \
  --policy policy.json --demands demand.json --reservations reservations.json \
  --out allocation.json

python -m revenue.delivery_capacity_allocator.cli verify \
  --policy policy.json --demands demand.json --reservations reservations.json \
  --receipt allocation.json
```

Inputs are bounded strict UTF-8 JSON with duplicate/non-finite rejection. CLI reads only stable regular-file generations and writes create-exclusively without pathname cleanup that could delete foreign replacements. `compile` returns exit 3 while retained-root authority is unavailable; `verify` likewise returns non-current rather than manufacturing authority.

## Validation

```bash
python -m py_compile revenue/delivery_capacity_allocator/*.py
python -m unittest -v \
  revenue.delivery_capacity_allocator.test_engine \
  revenue.delivery_capacity_allocator.test_authority_fix
python -O -m unittest -v \
  revenue.delivery_capacity_allocator.test_engine \
  revenue.delivery_capacity_allocator.test_authority_fix
```
