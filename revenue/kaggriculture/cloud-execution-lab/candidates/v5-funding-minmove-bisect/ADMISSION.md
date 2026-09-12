# V5 funding minimum-move bisection

Operation: `ASTRA-V5-FUNDING-MINMOVE-BISECT`.

## Predecessor

This is a performance-only successor to merged V4 funding replay work #12733, whose scope explicitly excluded quantity search, and to V5 cash-rank activation #13237. The current root `fund_same_turn_acquisition()` probes `moved=1..available` and runs a deep-copy plus full prefix projection for every failed quantity before selecting the first success.

## Why first-success is monotone in the admitted production path

The target is the first fixed acquisition whose `completed < required` in the baseline prefix. Therefore every earlier projected fixed acquisition is already fully complete before any sale is moved. Moving more units from a SELL after the target to the last same-product SELL/empty slot before the target:

1. preserves total same-turn sale quantity;
2. cannot reduce physical units sold at that earlier location;
3. cannot reduce conservative own sale cash: every explicit market scenario adds a floor-admitting positive quote for each additional executed own unit, and the minimum of nondecreasing scenario receipts is nondecreasing;
4. cannot enable extra pre-target fixed spending because those acquisitions were already fully completed in the baseline;
5. can only weakly free shed capacity, so the target BUY_ANIMAL capacity condition is monotone as well;
6. never crosses BUY_PRODUCT, which is an existing hard barrier because its price is market-state dependent.

Thus target completion is a false-prefix/true-suffix predicate over `moved` for the admitted production inputs. The minimal successful movement can be found with first-true bisection.

## Callback compatibility boundary

`_market_prefix_state` accepts either a mapping or a callable rival quantity. A callable could be stateful, so changing its probe count/order would change observable callback behavior. The optimized path therefore runs **only** when `rival_quantity` is a mapping. Callable callers retain the predecessor linear scan byte-for-byte in behavior. `FrozenSelected.transform()` snapshots its existing pure `self.rival_supply(obs, product)` values once into a mapping and uses that mapping for same-turn funding projection.

## Contract

- No change to candidate set, order indexes, minimum moved units, cash-rank ordering, diagnostics, fixed-acquisition semantics, config/defaults, archive, or Kaggle behavior.
- Mapping path: O(log available) prefix projections per donor after one endpoint admission probe, plus the existing baseline.
- Callable path: predecessor O(available) linear probe order preserved.
- Focused tests compare mapping bisection output to the callable linear path over boundary/interior/no-solution cases, prove a 1024-unit witness cuts prefix projections by >50x, and exercise the real prefix projector on a first-failing BUY_ANIMAL case.
