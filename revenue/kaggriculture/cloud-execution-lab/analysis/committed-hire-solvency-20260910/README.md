# TITAN V3 committed-HIRE solvency candidate

**Status:** additive source candidate; not in the canonical archive and not a
Kaggle submission.

**Parent inspected:** `98a98108998efac9e53a8b045f0fb2c85a4b19e2`

## Why this lane exists

The retained V2 unit-route audit documents one submitted loss in which action row
25 entered with `$6`, requested four executable `HIRE` orders, completed three,
and left the fourth planned hand absent.  Rows 26–48 still carried four hand
commands, producing 23 unbound commands.  The audit correctly treats this as
historical external evidence because the four replay gzip files are manifest-bound
but not stored in Git.

The current funded-prefix implementation preserves acquisition rows that completed
in its own reference trace.  A failed HIRE therefore contributes zero to the
preserved requirement.  That behavior is right for speculative or physically
clipped purchases; it is incomplete for a HIRE whose resulting hand slot is
explicitly consumed by the already-selected route.

## Candidate contract

`committed_hire.py` patches `frozen_selected.funded_minimum_now` only when
`install()` is called.  The canonical source remains untouched.

A next-turn HIRE is committed only when all of these hold:

1. The next selected route row contains the HIRE inside
   `market[:maxMarketOrdersPerTurn]`.
2. A later row, before the first controller decision boundary and within the
   bounded use window, gives that new hand index a non-`PASS` command.
3. Every earlier HIRE needed to create the highest consumed hand slot is included.
4. The complete current executable market is SELL-only.
5. The next market prefix through the final committed HIRE is SELL/HIRE-only.

The final two conditions are intentionally strict.  They make the cash proof
monotone: extra current proceeds cannot unlock an intervening purchase that then
consumes the reserve.

The cash certificate:

- prices every physically fillable current sale at the engine hard floor (`$1`);
- credits no requested or future sale receipt;
- uses the exact Fibonacci HIRE costs and `farmHandCostMult`;
- honors the day reset of `hires_today`;
- preserves inherited market indexes through `materialize_sales`;
- may increase one current sale quantity only;
- excludes `WHEAT` and `FERTILIZER` from new liquidation; and
- leaves the legacy minimum byte-for-behavior unchanged on every unsupported
  or uncertified case.

The candidate entrypoint installs the patch before canonical `main` initializes,
then normalizes output to exactly one hand command per actor visible in the
observation.  Trimming surplus commands and padding omitted commands with `PASS`
is engine-semantics preserving.

## Exact synthetic witness

The contract suite constructs the documented cash/arity shape directly:

- observed step: 24
- cash: `$6`
- next market: `HIRE, HIRE, HIRE, HIRE`
- costs: `$1 + $1 + $2 + $3 = $7`
- next route row: four non-`PASS` hand commands
- physical non-operating stock: one `MILK`

The legacy funded-prefix trace preserves the three HIREs that already fill and
returns a current-sale minimum of zero.  The installed candidate closes over the
fourth consumed slot and returns a minimum of one.  Because one physical current
sale yields at least the `$1` price floor and no current spend follows, the fourth
HIRE is cash-solvent without future-receipt credit.

## Verification

Focused contracts:

```sh
cd revenue/kaggriculture/cloud-execution-lab
PYTHONPATH="$PWD:$PWD/../cloud-runtime-pulse:$PWD/../cloud-quickstep" \
python -B -m unittest -v \
  test_committed_hire \
  test_funded_prefix \
  test_e07_same_turn_funding \
  test_joint_market_slots
```

The dedicated Actions workflow also:

- imports the pinned MAIN route and binds its row-25 four-HIRE / row-26 hand-use
  shape;
- byte-binds `kaggle-environments==1.32.7`;
- runs both candidate seats on the historical loss seed and three retained
  comparison seeds against current canonical `main.py`; and
- uploads the complete matched report plus a SHA-256 receipt.

No leaderboard uplift or counterfactual win is claimed without the resulting
official matched evidence.  Promotion still requires source review, matched-game
interpretation, canonical rebuild, and an explicit submission decision.
