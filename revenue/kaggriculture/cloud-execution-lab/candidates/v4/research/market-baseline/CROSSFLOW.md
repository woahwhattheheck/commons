# TITAN V4 CROSSFLOW — opposite-side lockstep market quotes

**Disposition: SOURCE MECHANICS ONLY / no timing-policy or EV claim.**

This packet fills one missing piece of the existing `research/market-baseline/`
authority. `lockstep_cobuy_oracle.py` already covers BUY↔BUY; SELL-side lockstep
is separately owned. CROSSFLOW covers the distinct same-item
`BUY_PRODUCT`↔`SELL` case for WHEAT/FERTILIZER.

## Source theorem

Pinned official engine Git blob:
`3c202c7ee921da239356789e266b694635103fc4`.

For each raw market row, the engine quotes both players against the **same
pre-commit inventory**. A SELL unit is quoted at `price(I)`. A BUY_PRODUCT unit
is quoted at `price(I-1)`. Only after both quotes exist are units committed.
Away from the `$1` SELL sink boundary, one same-item SELL and one BUY therefore
net public inventory back to `I`, but the buyer pays the stale pre-supply quote
and the seller receives the stale pre-demand quote.

So, when quantities are already required and a lawful raw-row shift is available:

* BUY after rival supply is weakly cheaper than same-row alignment.
* SELL after rival demand is weakly more valuable than same-row alignment.

This is a quote-order theorem, **not** permission to predict the rival's private
current action. A current-native/replay census must establish observable or
authored cross-flow alignment before any retiming experiment.

## Exact default witnesses

At public inventory 10,000 with 100-unit same-item flows (the default physical
shed-cap maximum), the oracle predicts:

| item | aligned BUY cost | BUY after rival SELL | saving | aligned SELL revenue | SELL after rival BUY | gain |
|---|---:|---:|---:|---:|---:|---:|
| WHEAT | 2,600 | 2,193 | **407** | 2,500 | 3,170 | **670** |
| FERTILIZER | 10,000 | 9,010 | **990** | 10,000 | 11,010 | **1,010** |

The delayed and aligned worlds finish at the same public inventory in these
witnesses. Quantity, cash, and physical shed capacity are exercised through the
engine's real `_process_market` interface when run from a repository checkout.

## `$1` floor boundary

Do not extend the clean theorem through a floor sale. Official SELL semantics
remove the private unit but add it to public inventory only when the quoted
price is greater than `$1`. At the floor, aligned and delayed cross-flow may
therefore end at different public inventories. `compare()` reports
`clean_same-terminal-quote-theorem=false` rather than treating a destructive
sale as ordinary supply.

## Boundaries

* COBUY keeps BUY↔BUY lockstep mechanics/collision census.
* SELL-side `lockstep_join` keeps SELL↔SELL mechanics.
* TOWNPROCURE keeps procurement policy; SELLWINDOW/market-pressure keep sale
  timing policy; ORDERBUDGET keeps raw-row cap ownership.
* CROSSFLOW does not create a controller, opponent predictor, runtime key,
  default/config/archive/Kaggle mutation, or economic-strength claim.
* Cross-product rows are outside the same-item price theorem; only WHEAT and
  FERTILIZER can participate on the BUY_PRODUCT side.

## Reproduce

From this directory in a repository checkout:

```bash
python -m unittest -v test_crossflow_quote_oracle.py
python -O -m unittest -v test_crossflow_quote_oracle.py
python -m py_compile crossflow_quote_oracle.py test_crossflow_quote_oracle.py
python crossflow_quote_oracle.py --item WHEAT --quantity 100
python crossflow_quote_oracle.py --item FERTILIZER --quantity 100
```

The tests include a source-faithful local market subset for isolated syntax and
contract validation plus an exact-checkout test. The exact-checkout test loads
the pinned official engine and refuses source drift by Git-blob identity.
