# TITAN independent score-reuse validation

Date: 2026-09-08

This additive receipt records an independent latency validation of the existing selected SELL score implementation. It does not change TITAN policy, configuration, canonical runtime, archive pointers, evaluator behavior, or provider state.

## Source boundary

- Frozen executed archive: `0a47069838fb2ac5f3872b697fabf5b1bf74aff54a0bb154af2c2813b477cacb`
- Runtime manifest files verified before use: 80
- Existing implementation reused: `selected_sell_core.MarketPath.score`
- QUICKSTEP PR #10518 already owns the reusable integration direction; this result is corroborating evidence, not a second implementation.
- A separately observed later archive was not executed in this pass.

## Measurement

Across 36 retained observation-stream trials and 25,884 measured direct actor calls, representing 2,876 unique observations:

- tested actions matched across arms and repetitions;
- tracked semantic state matched;
- actor exceptions: 0;
- internal deadline fallbacks: 0;
- aggregate direct-entrypoint wall time: 38.8830 s -> 34.4817 s (`-11.32%`);
- p99 individual call: 22.379 ms -> 18.085 ms;
- median cold/first call: 77.851 ms -> 79.158 ms, so cold start did not improve.

Validation: 26 regression methods passed, including 1,800 randomized direct-score comparisons, 96 complete optimizer/report comparisons, and existing entry-clock/module-recovery/route-recovery/worker-deadline cases.

New full games: **0**. Do not add these trials to the fleet full-simulation count. This is not hosted-strength, rank, or cold-timeout evidence.

## Disposition

A faster scratch per-invocation timeline prototype was not proposed for integration because caller-boundary discriminator cases changed report semantics. It remains comparison-only. No percentages from this receipt should be added to QUICKSTEP or PULSE measurements.

Canonical consumer remains WIDEFIELD. No raw hosted replay material is stored here.

Slack handoff: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788868235732519?thread_ts=1788805908.915009&cid=C0C0Z8AHGP2

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
