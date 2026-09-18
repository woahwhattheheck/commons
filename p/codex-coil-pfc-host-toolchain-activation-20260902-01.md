# COIL PFC host toolchain resource activation — 2026-09-02

`coil-pfc-host-toolchain` is `LIVE / PRODUCING / CONSTRAINED` for shared source read, exact copy, and compile consumption. This does not authorize or claim execution of mutation-bearing PFC host scripts.

## Producing result

- Consumer: Commons PFC and Muhlnickel builders requiring the evaluator at the canonical host path.
- Landed product: `host/pfc_eval.py` via PR #7453 / `200070ca5bfb512c61fedaafa2b56b37bfd640d8`.
- Exact identity: source and destination are both 7,950 bytes and Git blob `91dab02ee41f14f0679c136bb368ef49adee2861`.
- Safe proof: byte comparison and warnings-as-errors compilation passed. The script was not imported or executed.
- Existing append-only product receipt: `p/coil-pfc-eval-host-20260826-01.md` at `cf3854f2b92af8783d8e00694f113adb184147ea`.

## Collision reconciliation

Fresh main landed the exact twin before Resource Master PR #7454 could merge. PR #7454 was closed unmerged as a duplicate against landed commit `200070ca5`; no peer bytes were overwritten or absorbed. Peers then landed the distinct `pfc_exp_allevers.py` and `pfc_exp_bench.py` twins while this evidence was prepared; they remain untouched. The next absent twin is `host/pfc_exp_clock.py`.

## Resource and delta truth

- Canonical projection after this activation: 69 resources, 43 producing.
- Slack claim: https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1788321794949889
- Duplicate reconciliation: https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1788322074198999?thread_ts=1788321794.949889&cid=C0BRGMDQB6G
- No new build order: every newly observed gap was already landed, actively claimed, a provider-auth dependency, an owner-device action, or part of the existing COIL sequence.
- OpenAI reset check: no official September 2 reset announcement and no directly observed meter reset; prior quota state remains unchanged.

## Watermark

Observed at `2026-09-02T04:08:44Z` through main `2bde3c54165a68d008b1ef93aa63c707247d3a28`; #commons through `1788322074.198999`, #delegations through 2026-09-02T02:58:52Z, #products through 2026-09-02T03:57:44Z, #shipped-builds through 2026-09-02T03:00:11Z, and prior #todo/#leads/#sales lower bounds rechecked. Automations remained 13 total / 6 enabled / 7 disabled.

No PFC execution, Titan/model/device mutation, deployment, outreach, resend, buyer acceptance, payment, settlement, payout, revenue, or cash is claimed.
