# B7 room guard — practice arm

## Hypothesis

Frozen V3.1 already protects two dynamic wheat-purchase paths from overflowing the 100-unit shed:
V226 increments `wheat_topup_capacity_declines` when projected stock plus its shortage would exceed
100, and V233 refuses its rescue purchase when projected stock plus shortage exceeds 100. V219's
optional late fertilizer path is different: after its budget/order-cap checks it appends
`BUY_PRODUCT FERTILIZER 10`, but it has no analogous room check.

B7 tests only that asymmetry. It does **not** add a generic purchase rewrite and does not assume
same-turn sale proceeds free capacity.

## Exact baseline custody

The experiment branches from canonical V3.1 base
`508b342fc46fa91e3d7cdc3f0b7e44934a187c14` and imports the frozen
`overlay/r04_full_router.py`. It changes no overlay, package, evaluator, opponent, submission,
manifest/config default, or Kaggle artifact.

`B7_ENABLED = False`; importing or packaging the experiment cannot alter the shipped V3.1 policy.

## Transform contract

`room_guard()` acts only if all of the following are proven from current own-state/source custody:

1. B7 is explicitly enabled for the experiment.
2. The configuration uses the frozen 100-unit shed capacity.
3. `_V219_STATES[player]['pending']` belongs to the current step and has `fertilizer=True`, proving
   V219 requested its optional fertilizer bundle on this callback.
4. The currently selected native route tape contains no identical
   `BUY_PRODUCT FERTILIZER 10` row.
5. The final parent action contains exactly one identical row, avoiding index/provenance ambiguity.
6. `projected_shed()` plus all *other* `BUY_PRODUCT`/`BUY_ANIMAL` units fits in 100 slots.
7. Adding V219's ten fertilizer units is the sole reason the conservative capacity accounting
   crosses 100.

When all seven hold, B7 replaces the V219 market row with `[]`. It never removes/compacts the row,
so every later parent order keeps the same market execution index. It does not credit same-turn
SELL rows; that matches the conservative room accounting already used by V233.

If route custody is missing, an identical native row exists, the final row is duplicated, another
purchase set already overflows, or the configuration differs, B7 returns the original action
object unchanged.

## Telemetry

The experiment records calls, seen V219 fertilizer requests, activations, guarded rows/units,
insufficient-room events, native/row ambiguity declines, other-overflow declines, and
configuration declines. No hidden rival state is read or inferred.

## Kill / promotion criteria

Kill on any source trace where B7 blanks a native/non-V219 row, changes a later market index,
acts without a same-step V219 fertilizer request, credits an unproven sale to capacity, or mutates
behavior while disabled.

Focused source tests establish only mechanics custody. Promotion requires OFF identity plus
activation census and paired-seat economics (`Δown`, `Δrival`, `ΔM`) under the project's pinned
sim-fidelity standard before any default/package/Kaggle mutation.
