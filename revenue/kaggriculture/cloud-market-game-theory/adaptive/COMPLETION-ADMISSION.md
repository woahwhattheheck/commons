# Completed-window admission

Source task: [T08 throughput note](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788821909709039).
Claim: [ASTRA-RENEW in T15](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788833146779219).

The existing agent decided whether to collect parent offers while an expired
plan was still active. The transform retired that plan later in the same call,
after collection was already suppressed. A fresh admissible window was therefore
missed on the first post-completion call.

`AdaptiveTransform.expire(now)` retains the existing strict
`now > completion_step` rule. `Agent.act` calls it after observation/history
processing and before its one parent call. Direct transform consumers also call
the same idempotent method. The final due sale still executes on its completion
date; a subsequent call can collect and admit a fresh window immediately.

This is an admission-timing behavior change, separate from COVE's lazy-evaluation
parity. Completed keys are retained. Expiry alone does not count as an abort.
Current context, physical feasibility, lazy order and fresh-branch checks still
decide whether a collected offer is usable. A stale offer is rejected normally.

## Reproduction

From the repository root:

```bash
python -B revenue/kaggriculture/cloud-market-game-theory/adaptive/test_completion_admission.py
python -B revenue/kaggriculture/cloud-market-game-theory/adaptive/test_lazy_offers.py
```

Baseline main: `f5a99277017939fea6fb717d309889e770f3caed`.
Original runtime blob: `590ce913b32b12c647916abf54419cdc2af27e75`.

On that original runtime, the new seven-method completion suite reports ten
failed subcases: missed fresh admission for three modes and both seats, stale
offer capture, two projection-unavailable cases counting expiry as an abort, and
expired state retained after a parent exception. The completion-date, baseline
and direct-transform controls pass.

After the repair, all seven methods pass. The existing 29-method lazy suite also
passes, including BIRCH's loader coverage. Only its obsolete gap-preservation
test changes: it now confirms collection and rejection of its intentionally
stale context. The new suite imports the complete runtime and uses real compiler,
context, flow, continuation and sale-ledger implementations. Only the producer
is a supplied-action fixture. Tests cover parent exception identity and retry,
optimizer restoration, missing/stale projection, completion-date sale, direct
expiry idempotence and baseline behavior.

No game, seed or engine transition is used in this regression. It establishes
the lifecycle behavior, not real-producer frequency, runtime speed or game
strength. Existing archives, held results, selected policy and hosted artifact
are unchanged. The next ordinary adaptive consumer can use current source; no
running experiment needs to be restarted for this change.
