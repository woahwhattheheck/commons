# TITAN V3 horizon-liquidity ablation — SOL-KEPLER

Operation: `titan-v3-horizon-liquidity-20260909-sol-kepler-01`

## Source-proven seam

Submitted V1 used `0.95 * modeled_future_receipt` for stock left beyond its
artificial planning horizon. Submitted V2 changed that factor to `1.0`.
Current V3 retains full carry inside `selected_sell_core.MarketPath.score`, the
actual optimizer imported by `FrozenSelected`; it does not use
`scheduler.optimize_lot` for this decision.

With full carry, realizing one unit now can tie retaining it even though only
the sale creates spendable cash and removes execution risk. This packet
restores only the V1 carry factor in the production-selected optimizer. It does
not patch root `scheduler.MarketPath`, alter receipts or remaining units, or
change products, target selection, rival scenarios, route ownership, queue
ordering, capacity rules, terminal liquidation, or any canonical file.

## Runtime boundary

`candidate.py` loads canonical `main.py` and replaces its `_new_instance` hook.
The hook imports and patches `selected_sell_core` before canonical lazy
initialization, then invokes the original constructor. Its subclass delegates
the entire base `score()` and rescales only the carry contribution already
encoded in the returned relative value. Canonical prelude, whole-call deadline,
fallback, reconstruction, FinalPressure ordering, config, and every later
runtime transform remain in the original entrypoint. No receipt or marker is
attached to the live `TitanAgent`.

## Candidate-action activation custody

The inherited evaluator's `trace_sha256` hashes both agents' actions, both bank
trajectories, and final observations. It is useful whole-game evidence but
cannot prove that the tested candidate returned a different action. The panel
therefore applies a cardinality-checked patch to the exact pinned evaluator and
adds a length-delimited SHA-256 over only the candidate seat's parent-observed
responses, immediately before official interpretation.

Every accepted complete game must carry the exact 719 candidate responses for
the official 720-state lifecycle, matching both actor call receipts. Baseline
and treatment are paired on this candidate-only digest. Whole-game trace change
is retained as a diagnostic but cannot satisfy the activation gate. A rival- or
bank-only divergence is therefore a negative control, not evidence that the
carry ablation reached returned behavior.

## Evidence gate

`audit_change.py` fails closed on exact Git blobs for submitted V1, submitted
V2, current scheduler, selected SELL core, frozen selector, canonical entry,
and evaluator. It also binds the production import/call path, the one-factor
wrapper, evaluator patch seams, candidate-only verdict AST, exact 719/720
lifecycle, and one-panel workflow trigger.

Seventeen focused contracts cover carry economics, exact base delegation,
unchanged non-carry fields, terminal and fully realized behavior, idempotence,
conflict rejection, install timing, no live-agent provenance mutation,
canonical entrypoint delegation, candidate-only digest construction,
rival-only negative control, exact count/type validation, and rejection of
positive scores without returned-action activation.

The workflow then runs one identical-cell official-engine baseline/candidate
screen against Arlene, submitted V1, Apex, and Public BT12. `ADVANCE` requires
candidate-returned-action activation, positive mean own cash and margin,
nonnegative means in all four opponent strata, explicit Arlene and V1
non-regression, and no material stratum loss. A green workflow is not a
leaderboard claim; the retained JSON/markdown verdict is authoritative.
