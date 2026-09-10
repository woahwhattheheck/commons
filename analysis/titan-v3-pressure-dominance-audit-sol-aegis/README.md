# TITAN V3 market-pressure dominance audit

This package is a read-only policy audit. It does **not** alter the canonical
agent, provider state, or submission artifacts.

## Finding

The reviewed `market_pressure` repair proposed a stable two-class partition:
keep every positive same-sized proxy score in parent order, then move all
zero-score lots behind them. The empirical panel attached to that proposal was
strong, but the partition is not strict dominance under the pinned official
market engine.

A same-sized proxy score of zero can mean only that integer-rounded prices are
flat across that one proxy delay. A larger feasible hidden rival sale can cross
the local plateau. Demoting the zero-scored lot then loses our receipt even when
the promoted lot gains nothing.

The exact predecessor killer in `FINDING.json` starts at public inventories
`TOMATO=9999`, `MILK=9999`:

| queue | own cash | rival cash | own delta | margin delta |
|---|---:|---:|---:|---:|
| parent: `TOMATO 1`, `MILK 1` | 229 | 117 | 0 | 0 |
| proxy partition: `MILK 1`, `TOMATO 1` | 226 | 120 | -3 | -6 |

The rival queue is `TOMATO 2`, then blank. The reviewed proxy scores are
TOMATO `0` and MILK `+9`, so the proposed rule performs exactly the losing
swap. The result is executed through the pinned `mechanics._process_market`,
which preserves the official per-unit lockstep quote/commit semantics.

This is not a one-cell curiosity. Across every canonical product, inventories
9950 through 10050, and own lot sizes 1 through 8, the audit finds **1,426**
local proxy-zero cells that have positive receipt loss within a 100-unit rival
bound. The largest bounded miss in that compact scan is $460.

## Sound bounded repair

A lot may be demoted only when its own receipt is invariant for **every**
integer rival quantity from zero through the public feasible upper bound. For
the standard configuration that bound is `shedCapacity=100`.

`bounded_demotion_safe` is the simple exhaustive reference predicate.
`certified_partition` preserves every non-certified lot in parent relative
order and moves it only across certified receipt-invariant lots. It leaves the
counterexample parent queue unchanged and therefore retains the parent result.

A production implementation need not call the quote function for every delay.
Under a verified nonincreasing quote window, equality between the zero-delay
receipt and the maximum-delay receipt proves equality at every intermediate
delay. The fail-closed obligations are:

1. derive the bound from validated public configuration;
2. validate every quote in the needed `quantity + bound` window;
3. validate that the window is nonincreasing;
4. classify a lot as demotable only when the maximum-delay receipt equals the
   current receipt;
5. preserve parent relative order among all non-certified lots and around all
   barriers.

The retained empirical candidate may still be useful, but its current theorem
and tail-safety claim are false until this distinction is enforced and the
corrected rule is rerun on the same exact panels.

## Reproduce

From the repository root:

```bash
cd analysis/titan-v3-pressure-dominance-audit-sol-aegis
python -B -m unittest -v
python -B pressure_dominance_audit.py
python -B pressure_dominance_audit.py --write /tmp/FINDING.json
diff -u FINDING.json /tmp/FINDING.json
```

The workflow also verifies all pinned Git blob IDs before executing the audit.
