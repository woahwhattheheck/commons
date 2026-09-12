# V3.1 R04 H8/L3/evening current-ABI recovery

This is an **additive research carrier** for the remaining submitted-V3.1 market semantics that were cut away by the V4 policy-family switch. It does not call a producer/controller and it does not change production runtime, `TITAN-CONFIG.json`, CURRENT source/archive pointers, release state, opponents, or Kaggle submission state.

## Submitted authority

The score-facing V3.1 authority is commit `a90d888f03987ef0b35cfd20ec3519c6144db08a`.

- `candidates/v3/overlay/r04_full_router.py` Git blob: `a3e2fe87c717d128e43c9b65bae2265f40d1d76d`
- `candidates/v3/overlay/r04_no_late_sale_advance.py` Git blob: `fb26e2ca9985cc65b1127f4eec654fb5cb2a3df0`
- submitted sale horizon: **8**
- E184 start: **288**
- submitted L3 cutoff: **648**
- submitted sale-fertilizer behavior: FERTILIZER is eligible for E184 advancement; WHEAT remains excluded.

`test_source_authority.py` resolves those exact historical Git objects from full repository history. No retyped historical file is accepted as provenance.

## Public surface

Use `market_microstack_current_safe.R04MarketMicrostackCurrentABI`.

`market_microstack_current.py` contains the recovered mechanics. The safe wrapper is the public current-ABI boundary: it rejects pre-existing zero/dead market rows and market suffix ambiguity, while still allowing the donor's V224 helper to remove a zero row created *inside this component* by authenticated debt settlement.

The component deliberately has **two** calls rather than one monolithic transform:

1. `sale_window_transform(...)`
   - preserves the submitted native one-turn sale advancement before step 288;
   - settles prior native/E184 reservation debt;
   - applies E184 H8 reservations from exact caller-authenticated future actions;
   - makes FERTILIZER eligible when `sale_fertilizer=True`;
   - preserves the submitted L3 gate: step >=648 suppresses **new** reservations only after the complete contiguous public opening certifies the rival OFF_TAPE; missing/ambiguous opening evidence fails closed to incumbent H8;
   - preserves the submitted positive-row V224 sale-first ordering after step 144.
2. `evening_flush_transform(...)`
   - is intentionally separate so the single V5 composition can insert the independently-owned H4 and row-shed stages first;
   - at hours 21-23 after day 0, prepends the remaining projected WOOL/MILK/STRAWBERRY/MELON stock, price >=2, sorted by current `price * quantity`, bounded to the ten-row executable market capacity.

The intended current-V5 order is therefore:

`current selected action -> this sale-window stage -> H4 owner -> row-shed owner (#13399) -> this evening-flush stage -> downstream current finalizers`

The canonical composition gate owns the eventual exact cross-component placement. This carrier does **not** duplicate H4 or row-shed source ownership.

## Explicit current evidence

The stale R04 router/tape is not transplanted. The caller must provide:

- `post_unit_shed`: complete current post-unit projected product stock;
- `future_actions`: exact authored future actions for every due step the H8/native window may inspect;
- `queued_commands`: explicit current pending worker commands for E184 pickup ownership.

Any missing/malformed evidence suppresses new reservation work rather than guessing. Standard engine cardinalities/configuration are bound fail-closed.

### Shared H4 debt

H8 and H4 historically share `sale_window_debts`. To prevent double-reserving the same future STRAWBERRY sale, the public component exposes:

- `reservation_debts(player)` -> detached snapshot;
- `replace_reservation_debts(player, debts)` -> validated H4-updated snapshot.

A composition wrapper must hand H4 this same ledger and write its resulting debts back before the next callback. Parallel private ledgers are not promotion-compatible.

## Contracts

Focused tests cover normal Python and `python -O`, Python 3.11/3.12, exact PR-head checkout, donor Git-object identity, H8 reservations/debt, native pre-288 debt, FERTILIZER eligibility, current/queued/future pickup vetoes, animal PLACE uncertainty, L3 OFF_TAPE/on-tape/incomplete-opening behavior, debt settlement at the 648 cutoff, shared H4 debt, V224 ordering, dead-input fail-closed behavior, evening timing/capacity, and the explicit H4/row-shed composition gap.

From this directory:

```bash
python -B -m unittest -v test_market_microstack_current.py test_source_authority.py
python -O -B -m unittest -v test_market_microstack_current.py test_source_authority.py
```

Historical V3.1 score superiority is motivation, not current-V5 promotion authority. Runtime/default integration requires matched both-seat current-V5 economics against the exact V3.1 baseline under the shared paired-economics release firewall.
