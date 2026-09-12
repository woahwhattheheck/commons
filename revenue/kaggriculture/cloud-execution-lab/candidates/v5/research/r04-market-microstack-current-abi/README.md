# V3.1 R04 market microstack on the current V5 ABI

This is the **single additive market carrier** for submitted-V3.1 R04 semantics recovered after the V4 policy-family cutover. It is research-only: no production runtime/default, `TITAN-CONFIG.json`, CURRENT archive/source pointer, release state, opponent, or Kaggle submission is changed here.

## Submitted score authority

Exact V3.1 authority: `a90d888f03987ef0b35cfd20ec3519c6144db08a`.

- `candidates/v3/overlay/r04_full_router.py` Git blob `a3e2fe87c717d128e43c9b65bae2265f40d1d76d`
- `candidates/v3/overlay/r04_no_late_sale_advance.py` Git blob `fb26e2ca9985cc65b1127f4eec654fb5cb2a3df0`
- `candidates/v3/overlay/r04_h4_strawberry.py` Git blob `d6e3ffb76856ff171dab2a45b4d3c1788f2b2cb8`
- H8 sale horizon **8**, E184 start **288**, L3 cutoff **648**
- sale-fertilizer: FERTILIZER eligible for H8 advancement; WHEAT excluded
- V216 day-one HIRE reserve: step 23, authenticated row 24 HIRE commitment, Fibonacci HIRE cost, one-WHEAT financing while preserving two projected WHEAT

Historical objects are resolved from Git history by focused tests; no retyped donor file is accepted as provenance.

## Canonical receipt-bound route authority

The authorizing surface is `market_microstack_current_safe.R04MarketMicrostackCurrentABI`; `market_microstack_current.py` remains theorem-donor mechanics only. V216 is implemented beside it in `v216_hire_reserve.py` and consumes the **same** `MarketRouteAuthority`; the old standalone #13435 duck-typed window is not an authority.

Future-route evidence is not accepted as an arbitrary caller mapping. `market_route_authority.bind_market_route_authority(...)` consumes the landed shared `CurrentRouteWindow` v3 from #13439 (`main@a451fb14ed5ff517ecf1a3a999ac75d03b8ec37b`, source blob `1c4ec677034f757b4e24f874d643a3b322cdb3c1`) plus the exact immutable producer receipt:

```text
{route_step, last_step, player, route}
```

For market authorization the receipt must describe the current selected-action callback exactly: `route_step == last_step == observation.step`, receipt player must equal observation player, and `receipt.route` must exist in the installed controller route table. A carried older receipt is continuity evidence only and cannot authorize H8/H4/V216 on the current selected action.

The canonical v3 window itself must carry matching `route_step`, `last_step`, `player`, `route_id`, `current_step`, and `current_index`. The market adapter then independently re-verifies:

- strict JSON bytes (`allow_nan=False`) and SHA-256 for the **entire** `R[receipt.route]`;
- exact controller type, current worker cardinality, requested lookahead, and canonical v3 route source;
- every bounded future row's exact step, action bytes/hash and worker cardinality;
- route-table/reference stability across serialization;
- one market authority SHA-256 over the complete canonical window receipt, the complete immutable producer receipt, and queue authority.

Raw `controller.cur` is deliberately not a trust root.

The submitted router also consulted a deferred worker-command queue. The current installed Arlene controller has no separate queue: its complete mutable instance state is exactly `R`, `cur`, `_fs`, `_fs_for`. That exact state-key set is bound as `installed-intact-arlene:no-separate-deferred-command-queue:v1`. Any additional instance state fails closed until a canonical queue authority exists; an arbitrary caller-provided empty list is not proof.

## Recovered stages and order

The one market carrier owns a single receipt authority and the submitted H8/L3/H4 shared debt state. Current composition is:

1. `v216_hire_reserve.transform(..., route_authority=...)` at step 23 only
   - selected market must be empty;
   - authenticated authored row 24 must contain 1..5 HIRE rows;
   - HIRE cost is Fibonacci `(1,1,2,3,5)` × `farmHandCostMult`;
   - when cash is short, projected WHEAT is at least three, and one WHEAT sale covers the whole deficit, emit exactly `SELL WHEAT 1` and preserve all other selected-action bytes;
   - PICKUP/DROP/PLACE shed projection and capacity ordering match the submitted theorem;
   - missing/tampered/non-canonical market authority fails closed.
2. `sale_window_transform(..., route_authority=...)`
   - native one-turn sale advancement before step 288;
   - E184 H8 reservations/debt from the authenticated current route;
   - FERTILIZER eligibility when `sale_fertilizer=True`;
   - L3: at step >=648, suppress **new** reservations only after the complete contiguous public opening certifies the rival OFF_TAPE; unknown/incomplete/on-tape evidence keeps incumbent H8; prior debt still settles;
   - submitted V224 positive-row sale-first ordering after step 144;
   - pre-existing dead/zero current rows and >10-row suffix ambiguity fail closed.
3. `strawberry_topup_transform(..., route_authority=...)`
   - submitted H4 is collapsed into this same carrier, not a sibling;
   - can only top up exactly one existing current STRAWBERRY SELL row;
   - must consume the exact same sale-window revision and market-route authority digest;
   - writes to the same `sale_window_debts`, so due H8/H4 debt settles upstream before fresh top-up;
   - exact retries are idempotent; changed same-step evidence recomputes from the pre-H4 ledger.
4. #13399 combined `row_order_shed` theorem.
5. `evening_flush_transform(...)`
   - after day 0 at hours 21/22/23, prepend remaining projected WOOL/MILK/STRAWBERRY/MELON stock with price >=2;
   - sort by current `price * quantity`, bounded to the ten executable market rows.

Do **not** add a second standalone row-order stage: when both submitted flags are ON, the donor uses the combined `_row_order_shed(...)` callsite.

## Retry custody

Current V5 callbacks can retry a public step. The authorizing adapter stores immutable pre-step checkpoints:

- `step < previous_step`: true rewind/new stream;
- exact same-step + identical observation/action/projection/route-authority receipt: return the cached result/report without touching live shared H8/H4 debt;
- same-step changed evidence or authority digest: restore pre-step player/rival state and recompute;
- H4 has its own sale-revision + authority-digest transaction checkpoint.

This prevents same-step retries from erasing L3's opening certificate, losing future debt, double-reserving STRAWBERRY, or resurrecting a prior attempt after evidence changed.

## Contracts

Exact-PR-head CI runs Python 3.11/3.12, normal and `python -O`, with full Git history. Focused contracts cover donor identity, canonical v3 receipt-window field matching, forged-window rejection, committed-route/no-queue provenance, carried/cross-player/wrong-route rejection, strict non-finite rejection anywhere in the full route, H8/debt/native pre-288 behavior, FERTILIZER, pickup/PLACE vetoes, L3 OFF_TAPE/on-tape/incomplete opening, step-648 debt settlement, V224 ordering, retry transactions, shared H4 debt/retries/route matching, evening timing/capacity, and the complete V216 financing theorem including missing/tampered authority.

Historical V3.1 score superiority is motivation, not current-V5 promotion authority. Runtime/default activation still requires the one V5 composition gate and matched both-seat current-V5 economics against exact V3.1 under the shared release firewall.
