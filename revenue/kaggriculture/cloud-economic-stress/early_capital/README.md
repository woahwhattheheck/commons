# Early-capital retained-trace audit

This lane tests whether earlier or additional land actually repays its cash cost
before the episode ends. It replays retained authored action tapes through the
pinned official engine, changes only `BUY_LAND` timing, and verifies every
baseline terminal score against the retained game sidecar.

The 64 analyzed traces cover 16 seeds, both seats, and two opponent source
families. Moving the existing second land purchase about 15 turns earlier is
terminal-neutral throughout. An additional third land at step 266 is positive in
25/64 traces but loses $3,053.953125 on average, with outcomes from -$24,196 to
+$19,589. A hindsight choice among tested route-entry timings is positive in
36/64, demonstrating a real opportunity but not an implementable decision rule.

These are deliberate engine-valid fixed-action counterfactual fixtures, not
naturally generated games: later actions remain the retained baseline actions.
They establish that a static cash threshold or route identity is unsafe. Runtime
promotion requires an observable prospective certificate covering ordered-queue
affordability, needed inputs, finite worker turns, and receipts before the
remaining horizon.

Run `summarize.py` from the repository root to recheck all baseline identities
in the compressed raw result files and regenerate `summary.json`. No Kaggle
upload or hosted-strength claim is made.
