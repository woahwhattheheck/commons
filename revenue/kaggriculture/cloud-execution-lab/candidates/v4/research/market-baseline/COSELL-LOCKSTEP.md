# COSELL lockstep market witness

`cosell_lockstep.py` is a **research-only** oracle for one official Kaggriculture market mechanic that is not covered by the existing COBUY witness: when both players have an executable `SELL` of the **same item in the same market-row slot**, `_process_market` quotes both active units from one shared pre-commit market state, then commits both, then refreshes prices. The second player therefore does not take an intra-pair quote penalty from the first player's same-round sale.

## Bound authority

The oracle pins both official interpreter inputs consumed at module load:

- `reference/engine/kaggriculture.py` Git blob `3c202c7ee921da239356789e266b694635103fc4`
- adjacent `kaggriculture.json` Git blob `b354d06b742fe48402513792253f1a5c29366b20`

Both files are captured once. The Python snapshot is compiled/executed from memory, and the authenticated JSON snapshot is served from memory when the engine opens its adjacent specification. The reported identities therefore describe the same bytes that execute.

## Counterfactual

For identical starting public inventory and identical terminal quantities, the oracle compares three worlds:

1. **aligned** — rival and TITAN sell the same item in market row 0, so their active units are quoted lockstep;
2. **misaligned same callback** — an engine-inert zero-quantity row occupies TITAN row 0, so the rival completes row 0 before TITAN row 1;
3. **wait** — the rival completes its sale in one callback and TITAN sells in the next.

The physical terminal state must be identical across all three worlds. `simultaneous_gain_vs_wait` is therefore a quote-order cash delta, not an inventory or quantity artifact. `misaligned_gain_vs_wait` should be zero.

For nonlinear glut curves the effect can be material over multiple shared units. The effect is especially worth measuring for `WOOL` and `MELON`, whose above-I0 curves are quadratic, but the oracle accepts every official market product and does not assume the sign or size of the effect in advance.

## Deliberate boundary

This package does **not** predict a rival's hidden current action, move a sell row, mutate a controller, add a runtime key, or authorize activation. A useful follow-on needs source-bound incidence evidence: canonical current-route coordinates and/or frozen replay coordinates where both executable same-item `SELL` units actually occupy the same market slot, followed by both-seat economics. A hypothetical collision is mechanism evidence only.

Malformed quantities, booleans masquerading as integers, unknown items, and quantities above the default physical shed capacity fail closed. Market-prefix/cap admission remains the responsibility of the caller supplying an actual executable collision coordinate.
