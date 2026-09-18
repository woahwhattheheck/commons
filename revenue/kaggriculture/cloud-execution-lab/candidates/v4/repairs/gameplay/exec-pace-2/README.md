# EXEC-PACE-2: exact recovery and duplicate-step component repair

This is the existing canonical `main:candidates/v4/repairs/gameplay/exec-pace-2`
package, not a new V4 line. Raw donor custody and an independently tested
component are supplied here. **Nothing in production is wired or enabled.**

## Exact recovered evidence

`raw/exec-pace-2.tar.gz` is the original 5,270-byte tarball, SHA256
`f4def104e08b4f5b5b412c7a365bc2502a5e53f497ca2741077931cd1bb64675`.
It was decoded from the two literal Muse messages in #build-demand:
https://tokenjunkielabs.slack.com/archives/C0BTRNE6Y58/p1789179645922969
and https://tokenjunkielabs.slack.com/archives/C0BTRNE6Y58/p1789179645942299.
No recompression or semantic reconstruction was used. Its four exact members
are the standalone module, historical inline patch, WIRING.txt and verdict.
`raw/r04_exec_adaptive.py` is an exact copy of its module member (Git blob
`0ef551145dbcac9884e7d1710bcf11238dafc504`). The tests authenticate every member
before executing the standalone component or the isolated first helper hunk.
The historical patch is NEVER applied.

## Executed finding and correction

After 25 ascending observations, repeating the same step clears the original
standalone history from 25 samples to one and changes `rising('MILK')` from
true to false. That contradicts its documented idempotence. The source-pinned
transformer only separates equality (no-op) from decreasing steps (reset).
An AST test proves this is its only executable change. Original bytes stay
untouched. The resulting candidate is not installed anywhere.

From this directory, using Python 3.10 or newer:

```sh
python -m unittest -v test_exec_pace_recovery
python -O -m unittest -v test_exec_pace_recovery
python run_negative_controls.py
python -O run_negative_controls.py
python repair_duplicate_step.py raw/r04_exec_adaptive.py /tmp/execpace-duplicate-candidate.py
```

The transformer rejects unknown preimages and existing output files. The
independent **17-test** suite is newly authored; it is NOT the missing original
15-test suite. Each mode checks 3,840 matched strictly-increasing callbacks,
480 duplicate callbacks across all seven goods, four backward resets, exact
archive custody, CLI fail-closed behavior and the two raw implementation variants.
Four deliberately broken behavioral variants are rejected in both modes.

## Gates still open

The original inline router patch and standalone module have different reset
semantics. WIRING describes a standalone import, not the inline patch. The
original 15-test file, full economically tested router and raw panel rows were
not in the recovered tarball. Ask the existing holder for those exact bytes;
do not recreate or attribute the reported 23 positive cells to this repair.

This narrow correction intentionally leaves the donor's per-sample rather
than elapsed-step slope, nonfinite-price acceptance, missing-price zero
imputation and same-step new-episode ambiguity visible in tests. They are
NOT certified correct. Whole-router key-OFF parity, current-ABI integration,
package/official-engine games, resource budget and paired economics remain
unrun. Keep the key OFF. Never run the legacy materializer against the modern
native runtime. Existing intake owns shared MANIFEST/INTEGRATION reconciliation;
this packet does not silently change those shared statuses.
