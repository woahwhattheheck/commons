# TITAN V3 E13 future-sale solvency receipt

- Operation: `TITAN-V3-E13-FUTURE-SALE-SOLVENCY-CLOSURE-20260910-01`
- Slack claim: `#titan-kaggriculture` TS `1789069704.186569`
- Base: `main@c51049d671b55d282e0fed5df37a0be7c513a838`
- Active FrozenSelected blob: `fc7baf5c179818a55037f6a61d92984d81d1a21c`
- Pinned engine blob: `3c202c7ee921da239356789e266b694635103fc4`
- Frozen Arlene blob: `bdb9cf58148a3c7961c085f4902759537decabf6`
- Disposition: `SOURCE_REAL_ACTION_UNMEASURED`

## Delivered boundary

Merged E13 (`#11117`) stops its acquisition-fill comparison before the first
future SELL with any positive receipt. A later-turn fixed acquisition can
therefore lose baseline working capital even when that future receipt is only
`$1`.

This additive packet materializes one disconnected replacement of
`funded_minimum_now()`. It retains the landed E13 prefix contract and adds only
baseline-completed fixed acquisitions on turns strictly later than the funding
sale. Candidate traces run through the existing bounded horizon so represented
future receipt amounts receive exact credit.

The `$1` future WOOL sale followed by a `$400` COW purchase kills the
predecessor: old minimum `0`, repaired minimum `3`. Two MILK units plus the
future dollar are `$319` and fail; three plus the dollar are `$475` and
succeed. A sufficient two-unit base-price future WOOL sale provides `$400` and
retains minimum `0`.

## Collision boundary

SOL-ESCROW TS `1788989953.650839` owns same-turn/order-index acquisition custody.
This packet deliberately excludes acquisitions on the funding sale's own turn
and proves both same-turn orderings remain behaviorally unchanged.

## Verification boundary

The packet provides:

- exact-source/engine/Arlene Git-blob gates;
- 16 focused predecessor, interpreter, custody, and census contracts;
- the eight landed E13 neighbor contracts;
- canonical overwrite refusal and clean-tree proof;
- deterministic candidate, receipt, route census, provenance, logs, and hashes.

No canonical runtime, configuration, archive, release pointer, provider, Kaggle,
or submission state is changed. No returned-action activation, complete-game
score, leaderboard, or promotion claim is made. Integration requires a
fresh-main one-tree activation receipt and matched both-seat panel.
