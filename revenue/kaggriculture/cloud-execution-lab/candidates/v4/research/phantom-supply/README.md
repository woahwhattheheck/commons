# PHANTOMSUPPLY — negative public stock / BUY_PRODUCT frontier

Status: **source-bound mechanism experiment; not a gameplay policy or engine-fix proposal**.

This package tests an official-engine boundary that is different from the existing
L3 public-supply-pressure gate. L3 asks whether recent public inventory changes
prove rival net supply. PHANTOMSUPPLY asks whether public inventory is a hard
availability constraint at all for the two products players may buy directly.

## Pinned authority

The oracle single-reads the official engine, authenticates that exact captured
buffer, and compiles/executes the same bytes without reopening the path:

- `reference/engine/kaggriculture.py` Git blob:
  `3c202c7ee921da239356789e266b694635103fc4`
- engine SHA-256:
  `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`

The test deliberately stubs only the unused import-time
`kaggle_environments.utils.resolve_episode_seed` symbol. Market parsing,
quoting, lockstep commitment, price refresh, and town consumption are executed
from the authenticated engine snapshot itself.

## Mechanism theorem

The pinned engine has no `market.inventory[item] > 0` precondition in
`_commit_unit(..., op="BUY_PRODUCT", ...)`. A WHEAT or FERTILIZER buy succeeds
when money and shed capacity permit, then performs:

`market["inventory"][item] -= 1`

regardless of the prior inventory value. The quote is computed at the
post-buy inventory (`current_inventory - 1`). Therefore zero is not a supply
floor and a negative public inventory does not itself stop later purchases.

The lockstep detail is stronger: both seats are quoted from the same pre-commit
inventory. With one public unit left, two simultaneous one-unit BUY_PRODUCT
orders both receive the quote for post-buy inventory zero and both may commit;
public inventory ends at `-1`. Starting at zero, the same two-seat callback can
end at `-2` while both sheds receive a real unit.

Town demand is likewise uncapped. `_town_consume()` subtracts every scheduled
shop and town-center unit without checking current inventory, so all town-center
products can cross below zero independently of player buys. FERTILIZER is not a
town-center product; its negative-stock path is BUY_PRODUCT only.

This is an engine semantic, not yet evidence that deliberately relying on
negative stock improves V4 score.

## Deterministic price facts from the pinned formula

Negative inventory increases scarcity price but remains finite. The next-buy
quote is the official `market_price(item, current_inventory - 1)`.

For a current public inventory at or below zero, the source-derived checkpoints
used by the executable tests are:

| Current inventory | next WHEAT buy | next FERTILIZER buy |
| ---: | ---: | ---: |
| 0 | $125 | $2,100 |
| -1 | $125 | $2,100 |
| -10 | $125 | $2,102 |
| -100 | $126 | $2,120 |
| -1000 | $130 | $2,300 |

Cumulative direct-procurement cost starting from exactly zero public stock:

| Units bought | WHEAT | FERTILIZER |
| ---: | ---: | ---: |
| 1 | $125 | $2,100 |
| 10 | $1,250 | $21,011 |
| 1000 | $127,460 | $2,200,100 |

So the mechanic is qualitatively different by product: deep-negative WHEAT is
still moderately priced under the square-root scarcity curve, whereas direct
FERTILIZER is extremely expensive under its linear curve. That makes WHEAT the
first economics/reachability target rather than assuming both BUY_PRODUCT goods
are equally useful.

## What the executable oracle proves

`test_phantom_supply.py` requires all of the following against the authenticated
engine snapshot:

1. single-seat WHEAT `0 -> -1` with one real shed unit;
2. single-seat FERTILIZER `0 -> -1` with one real shed unit;
3. two-seat last-unit lockstep `1 -> -1`, both sheds +1, equal quote/cost;
4. two-seat zero-stock lockstep `0 -> -2`, both sheds +1;
5. town-center demand drives every eligible zero-stock product to `-1`;
6. negative-stock WHEAT/FERTILIZER quotes stay finite and nondecreasing over the
   pinned checkpoints;
7. exact cumulative zero-stock procurement examples above;
8. source drift is rejected;
9. an authenticated captured snapshot still executes after its source path is
   removed, guarding against verify-then-reopen evidence.

The CLI emits `titan.v4.phantom-supply.v1` JSON with exact source identity,
mechanism cases, price curves, and explicit `gameplay_ev=NOT_ASSESSED` /
`current_v4_activation=NOT_ASSESSED` boundaries.

## Next admission gate

Do **not** promote a “buy through zero” heuristic from this mechanism alone.
The useful follow-up is current-V4 economics/reachability:

- census callbacks where current V4 needs WHEAT but public WHEAT is at/below
  zero, including FEED/TOWNPROCURE recovery and same-turn funding;
- compare waiting/production/substitution versus direct negative-stock purchase
  with exact cash, shed capacity, market-order prefix, and later feed/output
  realization;
- pair both seats because rival BUY_PRODUCT shares the pre-commit quote but also
  deepens the post-callback scarcity state;
- record downstream town-shop/public-market divergence, using canonical TOWNRNG
  environmental-path rules where occupancy policies differ;
- reject promotion on new-loss pathology or if activations are unreachable in
  current-native traces.

Keep this inside the single canonical V4. No official-engine patch, alternate
controller, runtime/default/config change, COMPOSITION/INTEGRATION claim,
archive mutation, or Kaggle submission belongs to this package.

## Reproduce

From this directory:

```bash
python -B test_phantom_supply.py
python -O -B test_phantom_supply.py
python -m py_compile phantom_supply.py test_phantom_supply.py
python -B phantom_supply.py \
  --engine ../../../../reference/engine/kaggriculture.py \
  --output /tmp/PHANTOMSUPPLY.json
python -m json.tool /tmp/PHANTOMSUPPLY.json >/dev/null
```

Only an exact-head execution of those commands is an authored green receipt.
