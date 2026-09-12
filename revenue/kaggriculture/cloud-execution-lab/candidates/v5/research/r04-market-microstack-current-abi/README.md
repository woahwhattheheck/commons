# V3.1 R04 market microstack on the current V5 ABI

This is the **single additive market carrier** for submitted-V3.1 R04 semantics recovered after the V4 policy-family cutover. It is research-only: no production runtime/default, `TITAN-CONFIG.json`, CURRENT archive/source pointer, release state, opponent, or Kaggle submission is changed here.

## Submitted score authority

Exact V3.1 authority: `a90d888f03987ef0b35cfd20ec3519c6144db08a`.

- `candidates/v3/overlay/r04_full_router.py` Git blob `a3e2fe87c717d128e43c9b65bae2265f40d1d76d`
- `candidates/v3/overlay/r04_no_late_sale_advance.py` Git blob `fb26e2ca9985cc65b1127f4eec654fb5cb2a3df0`
- `candidates/v3/overlay/r04_h4_strawberry.py` Git blob `d6e3ffb76856ff171dab2a45b4d3c1788f2b2cb8`
- H8 sale horizon **8**, E184 start **288**, L3 cutoff **648**
- sale-fertilizer: FERTILIZER eligible for H8 advancement; WHEAT excluded

Historical objects are resolved from Git history by the focused tests; no retyped donor file is accepted as provenance.

## Current authority, not legacy tape

The authorizing surface is `market_microstack_current_safe.R04MarketMicrostackCurrentABI`. `market_microstack_current.py` is theorem-donor mechanics only.

Future-route evidence is no longer an arbitrary `future_actions` argument. `market_route_authority.bind_market_route_authority(controller, observation)` consumes the merged canonical `current-route-witness/CurrentRouteWindow` from the installed `R[cur]`, then independently verifies:

- exact current step/index, public worker cardinality, route id/source/controller type;
- strict JSON bytes (`allow_nan=False`) and SHA-256 for the **entire installed route**;
- every bounded future row's exact step, action bytes/hash and worker cardinality;
- a market authority SHA-256 over the complete canonical window receipt plus queue authority.

The submitted router had a deferred worker-command queue. The current installed Arlene controller does not: its complete mutable instance state is exactly `R`, `cur`, `_fs`, `_fs_for`. That exact state-key set is bound as `installed-intact-arlene:no-separate-deferred-command-queue:v1`. Any new controller instance state fails closed until a canonical queue authority exists. An arbitrary empty list is not accepted as proof.

The first canonical current-route source authority is merged commit `d61e0333efe5697b56a867ed84a23e909195d3f4`, route-witness blob `987e8a52e4f5ab48aa8390bb5655aac23e6c2f39`, installed Arlene blob `bdb9cf58148a3c7961c085f4902759537decabf6`. Later compatible hotfixes may strengthen the shared witness; this carrier re-verifies the bytes it consumes itself.

## Recovered stages

`R04MarketMicrostackCurrentABI` owns the submitted H8/L3/H4 shared debt state and exposes three market stages:

1. `sale_window_transform(..., route_authority=...)`
   - native one-turn sale advancement before step 288;
   - E184 H8 reservations/debt from the authenticated current route;
   - FERTILIZER eligibility when `sale_fertilizer=True`;
   - L3: at step >=648, suppress **new** reservations only after the complete contiguous public opening certifies the rival OFF_TAPE; unknown/incomplete/on-tape evidence keeps incumbent H8; prior debt still settles;
   - submitted V224 positive-row sale-first ordering after step 144;
   - pre-existing dead/zero current rows and >10-row suffix ambiguity fail closed.
2. `strawberry_topup_transform(..., route_authority=...)`
   - submitted H4 is collapsed into this same carrier, not a sibling;
   - can only top up exactly one existing current STRAWBERRY SELL row;
   - must consume the exact same sale-window revision and market-route authority digest;
   - writes to the same `sale_window_debts`, so due H8/H4 debt settles upstream before any fresh top-up;
   - exact retries are idempotent; changed same-step evidence recomputes from the pre-H4 ledger.
3. `evening_flush_transform(...)`
   - after day 0 at hours 21/22/23, prepend remaining projected WOOL/MILK/STRAWBERRY/MELON stock with price >=2;
   - sort by current `price * quantity`, bounded to the ten executable market rows.

The score-facing combined row-order/row-shed theorem remains owned by #13399 and belongs between H4 and evening flush. Do **not** add a second standalone row-order stage: when both submitted flags are ON, the donor uses the combined `_row_order_shed(...)` callsite.

Intended current composition:

`selected action -> canonical CurrentRouteWindow/MarketRouteAuthority -> H8/L3/V224 -> H4 -> #13399 row_order_shed -> evening flush -> downstream current finalizers`

## Retry custody

Current V5 callbacks can retry a public step. The historical whole-route code treated same-step callbacks as reset; that is unsafe once the shared debt ledger is public. The authorizing adapter therefore stores immutable pre-step checkpoints:

- `step < previous_step`: true rewind/new stream;
- exact same-step + identical route/observation/action/projection receipt: return the cached result/report without touching live shared H8/H4 debt;
- same-step changed evidence or route digest: restore pre-step player/rival state and recompute;
- H4 has its own revision+authority-keyed transaction checkpoint.

This prevents same-step retries from erasing L3's opening certificate, losing future debt, double-reserving STRAWBERRY, or resurrecting a prior attempt after evidence changed.

## Contracts

Exact-PR-head CI runs Python 3.11/3.12, normal and `python -O`, with full Git history. Focused contracts cover donor object identity, canonical route/no-queue provenance, strict non-finite rejection anywhere in the full route, H8/debt/native pre-288 behavior, fertilizer, pickup/PLACE vetoes, L3 OFF_TAPE/on-tape/incomplete opening, 648 debt settlement, V224 ordering, retry transactions, shared H4 debt/retries/route matching, and evening timing/capacity.

```bash
python -B -m unittest -v \
  test_market_microstack_current.py test_retry_transactions.py \
  test_h4_shared_current.py test_route_authority.py test_source_authority.py
python -O -B -m unittest -v \
  test_market_microstack_current.py test_retry_transactions.py \
  test_h4_shared_current.py test_route_authority.py test_source_authority.py
```

Historical V3.1 score superiority is motivation, not current-V5 promotion authority. Runtime/default activation still requires the one composition gate plus matched both-seat current-V5 economics against the exact V3.1 authority under the shared release firewall.
