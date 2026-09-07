# Producer arrival contract

Additive T08 interface work. Frozen selected SELL and all earlier branches remain
unchanged. This module contains no controller, optimizer, quote function or
simulation. It consumes current producer-owned plan facts, then emits contingent
capacity obligations and shared worker/target reservations.

```python
from arrival_contract import build_arrival_contract, pending_capacity

contract = build_arrival_contract(obs, cfg, selected_action, producer_snapshots)
extra_after_market = pending_capacity(contract, day_close_step, 'after_market')
```

Each producer supplies a complete snapshot for the current observation step:
`owner`, `observed_step`, and `plans`. Each plan supplies:

| Field | Contract |
|---|---|
| `errand_id` | Stable within producer; no duplicate IDs |
| `worker_index` | Farmer 0, hands 1 onward; exclusive while pending/carried |
| `target` | Observed board coordinates, exclusive while pending |
| `product` | Actual harvested product |
| `units_total` | Whole harvest competing for shed capacity |
| `units_incremental` | Genuinely incremental units; never substituted for capacity |
| `arrival_step`, `arrival_kind` | Producer's committed plan date; `eod_auto` or `worker_deposit` |
| `status` | `pending`, `carried`, or `aborted` |
| `observed_carried_units` | Producer-attributed realized stock, bounded by actual current inventory |
| `no_forced_sale_date` | Must be true; arriving goods do not require an immediate sale |
| `hire_order_index` | Required for a worker still contingent on a selected HIRE order |
| `deposit_action` | Explicit DROP or selective PLACE for worker-deposit plans |

Pending reservation is `units_total - observed_carried_units`. Carried stock is
already in the observation and is returned separately; it must not be added to
capacity a second time. A carried worker remains reserved while its producer
still owns its PASS-until-EOD plan. Abort releases the pending obligation; any
actual stock remains in the observation. Stale producer snapshots, overdue plans,
double-booked workers/targets and over-attributed carried stock are rejected.
The caller retains its safe selected action when a contract is unavailable or
invalid. The module does not authorize or fund HIRE; it checks references to
orders the authoritative action already selected.

EOD events are AFTER market on the current day-close step. Their first possible
sale is the next step; final-day EOD output has no usable sale window. A worker
deposit needs an explicit planned DROP/PLACE, not merely a path to shed access.
A current-step deposit must occur in the selected unit action. Future action
feasibility and stock attribution remain the producer's responsibility; this
interface cannot prove a false producer claim true.

Outputs include no sale lots, guaranteed future stock, prices, probabilities or
opponent data. Whole pending harvests remain contingent on successful execution.
The next SELL adapter must distinguish these obligations from observed post-unit
shed stock and must replan/cancel obligations on subsequent observations.

## Source and review boundary

Mechanics source: bundled exact Kaggle engine at
28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c, `_apply_unit_action` (MOVE/PASS do not
deposit; DROP and shed PLACE explicitly do). Producer sources: Claude cap
d39b989f842db7c51d06396998b0ccaea09cc305 and FLORA lost-production
46482481f5cec7fb1aa5165e89520f2240a0286b, `_eh_choose` and `_eh_action`.
FLORA's capacity requirement is `harvest_units`, while its valuation uses
`economic_units`; its held goods PASS until EOD.

Current contract follows root's T08 review at Slack1788809693.051589 and Claude's
proposed errand interface at1788809585.830569. Claude owns deposit/valuation
correction; this code does not duplicate it. Six synthetic interface tests cover
whole crop harvest, EOD phase, partial/full realization, abort, shared ownership,
stale inputs, contingent HIRE and final sale windows. These are not retained
midgame cap-plan replay evidence. That actual producer fixture was requested and
is still needed before a corrected integration panel. No new full games have
run for this contract. The generic author SELL API and corrected producer source
will be consumed additively when callable, with fresh unused dev/held seeds.
