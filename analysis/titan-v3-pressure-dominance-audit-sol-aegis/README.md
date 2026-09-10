# TITAN V3 market-pressure dominance audit

This package is a read-only policy audit. It does **not** alter the canonical
agent, provider state, package pointers, or submission artifacts.

## Disposition

**HOLD every universal “strict-dominance” claim for the reviewed
positive-pressure-before-zero partition and for the first raw-state bounded
repair.** The empirical panels may still identify a useful heuristic, but the
ordering rule is not own-cash dominant under the pinned official market engine.

Three independent exact predecessors now close three different loopholes:

| failure class | parent own | candidate own | parent rival | candidate rival | own Δ | margin Δ |
|---|---:|---:|---:|---:|---:|---:|
| rounded proxy plateau | 229 | 226 | 117 | 120 | -3 | -6 |
| raw-state certificate ignores queue prefix | 1828 | 1827 | 2075 | 2076 | -1 | -2 |
| hidden rival BUY demand | 67 | 66 | 974 | 974 | -1 | -1 |

All rows execute through the pinned `mechanics._process_market` implementation,
including its quote-all/commit-all per-unit lockstep and post-buy
`BUY_PRODUCT` quote.

## Finding 1 — a same-sized proxy zero is not a certificate

At public inventories `TOMATO=9999`, `MILK=9999`:

- parent own queue: `SELL TOMATO 1`; `SELL MILK 1`
- rival queue: `SELL TOMATO 2`; blank
- same-sized proxy scores: TOMATO `0`, MILK `+9`
- reviewed partition: `SELL MILK 1`; `SELL TOMATO 1`

The candidate loses $3 of own cash and $6 of margin. Integer rounding creates a
one-unit local plateau for TOMATO, but the hidden two-unit rival lot crosses the
next price step.

The compact scan retained in `FINDING.json` finds **1,426** such local-zero /
bounded-positive cells across all nine canonical products, inventories
9950..10050, own quantities 1..8, and a 100-unit upward displacement. The
largest bounded miss in that scan is $460.

## Finding 2 — raw public inventory is the wrong certificate origin

A natural first repair is to call a lot safe when its receipt is invariant for
every contiguous rival-sale displacement `0..shedCapacity` from the public
inventory. That repair kills Finding 1 but is still false because earlier
executable rows move the actual inventory frontier.

At public inventories `WHEAT=10066`, `MILK=9999`:

- parent own queue: `SELL WHEAT 78`; `SELL WHEAT 1`; `SELL MILK 1`
- rival queue: blank; `SELL WHEAT 100`; blank
- raw scores: WHEAT78 `+2`, WHEAT1 `0`, MILK1 `+9`
- the middle WHEAT1 appears invariant at $21 for every raw displacement 0..100
- raw bounded partition: WHEAT78; MILK1; WHEAT1

Row 0 first advances WHEAT to 10144. In the parent, the middle lot executes
there for $21. In the candidate, the rival drains 100 WHEAT in row 1 and the
lot executes at 10244 for $20. The candidate loses $1 of own cash and $2 of
margin.

Any sale-supply certificate must be indexed to the lot's exact or conservative
**execution-prefix inventory envelope**, including prior same-product
executable own rows and feasible rival units in every crossed/intervening row.
Raw `observation.market.inventory` is insufficient.

## Finding 3 — hidden rival demand can reward the later sale

Even a prefix-correct certificate on the demoted lot does not prove universal
dominance. The promoted lot can lose price uplift from a hidden opponent buy.

At public inventories `EGG=10139`, `WHEAT=10000`:

- parent own queue: `SELL EGG 1`; `SELL WHEAT 1`
- candidate queue: `SELL WHEAT 1`; `SELL EGG 1`
- rival queue: `BUY_PRODUCT WHEAT 1`; blank
- rival begins with $1,000 and one free shed slot
- EGG is $41 and sale-delay-invariant through +100
- WHEAT has positive same-sized proxy `25 - 24 = +1`

The engine quotes a WHEAT purchase at post-buy inventory. In the parent, the
rival buys first for $26 and our later WHEAT sale receives $26. In the
candidate's simultaneous row, our sale is frozen at the precommit $25 while the
rival purchase is independently frozen at $26. EGG remains $41. Candidate own
cash falls from 67 to 66 while rival cash is unchanged at 974.

A universal crossing theorem must reason about **both lots** and both directions
of hidden market flow. WHEAT and FERTILIZER can be bought by the opponent, so
an earlier sale is not automatically weakly better. A sufficient invariant
needs a bidirectional inventory envelope (feasible opponent BUY and SELL
quantities, cash, shed room, active prefix, and quote-all/commit-all timing), or
the policy must preserve parent order.

## What the code proves

`pressure_dominance_audit.py` provides:

- exact official-engine executions for all three predecessors;
- the reviewed proxy partition;
- the explicitly named and disproved `raw_bounded_partition`;
- strict integer/finiteness validation;
- `bidirectional_flat_invariant`, a conservative quote-invariance primitive
  whose bounds remain a caller obligation;
- the deterministic 1,426-cell plateau scan.

It deliberately does **not** publish a replacement optimizer or a promotion
claim. A useful successor can be narrower than universal dominance, but it must
state and test its actual threat model.

## Minimum repair obligations

A production successor must, at minimum:

1. bind the exact active market prefix and official quote/commit semantics;
2. compute parent and candidate execution-prefix inventory envelopes;
3. cover feasible rival SELL supply for the demoted lot;
4. cover feasible rival BUY demand for the promoted WHEAT/FERTILIZER lot;
5. validate integer, finite, monotone/flat quote windows as its theorem needs;
6. preserve parent relative order on any malformed, nonfinite, unsupported, or
   ambiguous state;
7. retain all three predecessors as exact-engine regression tests;
8. rerun the original paired panels and gate own cash, margin, W/T/L, and
   opponent-by-seat tails rather than reusing the earlier headline.

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
