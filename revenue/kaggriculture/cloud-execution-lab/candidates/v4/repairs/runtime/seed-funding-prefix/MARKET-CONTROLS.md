# Independent seed-prefix market controls

This is additive evidence for the ONE repair in this directory. The source owner
is `repair_seed_funding_prefix.py`, exact Git blob
`a5c2c131fd83d83d6be822556abce5723b464a50`. This contribution includes no alternative
repair, runtime hook, feature, producer, archive, or activation code.

## Executed result

Python 3.13.5: **22/22 normal and 22/22 optimized**, zero failures, errors or skips,
against that exact owner's repair applied to the exact current full runtime
`b952c9c228ecbde592bf3d2df01638677abb0d24` (33,885 bytes). Its scratch output is
`cbeb7f09914c351a99cb5f0970c14a7bea7cb029`, 34,070 bytes; method SHA256
`2aef22adfe3dd46782b71f9c6fefb4f4c38b2d8a8671766ea8e395b1adebeab6`.

Each successful mode completes 432 suffix vectors, 720 positive-cap executable
prefix compatibility controls and 402 paired official-market state comparisons.
The exact predecessor produces 311 failed assertions/subcases plus one
TypeError on a malformed engine-dead suffix, in both modes. These are not 312
independent strategies or mutants. Result summaries and input/log hashes are in
`MARKET-CONTROLS-RECEIPT.json`.

The independent test object is Git blob
`1113688b90ff9c4d128d64dbdaff04f25cb08d26` (20,138 bytes).

## What is actually executed

The runner extracts the actual `_seed_selected` methods from separately supplied,
byte-pinned baseline/candidate files. It does NOT import or run the entire
TitanAgent class, its `act()` lifecycle, a producer, or a full-game evaluator.
The receiver is a test object and `scheduler.post_units` is an explicit PASS-only
projection double. SeedBudget, plant suffix construction, the funding certificate,
engine market parser, quotes and every market commit are the original pinned
functions. The only engine import shim is an unused `resolve_episode_seed` that
raises if called. These limits distinguish this packet from the complementary
whole-current-class/full-interpreter peer gate; neither should claim the other's
coverage.

Checks retain real in-cap HIRE funding veto/certification, future route and spatial
seed demand, observed seed stock, both seats, raw empty-slot positions, opaque dead
tail bytes, and input nonmutation. Cap 0 follows the engine's minimum one slot;
cap 12 keeps the genuinely executable eleventh/twelfth slots. No fixed-ten shortcut
or raw-row compaction is permitted.

One constructed market witness starts with $35 and no remaining route PLANT
requests. `BUY_SEED WHEAT 50` followed by nine empty rows and an engine-dead
`HIRE` causes the predecessor to retain its seed buy after conservative funding
rejection: $5 and three unneeded seeds remain. The repair leaves $35 and zero
seeds, with identical rival and other non-seed market state. Both seats reproduce
the $30 difference. This is immediate synthetic cash evidence, NOT natural
activation, whole-game EV, a leaderboard claim, or promotion authority.

## Reproduce with reviewed bytes

Materialize the exact baseline and the exact owner composer first. The current
baseline was recovered from GitHub Actions artifact **10123395668**, ZIP SHA256
`d11b9ca245dc8205dabd26523c2e431055feaa22afa3bc10866e4e3bae3db4ed`.
The checked archive inside it has SHA256
`e226706c8b0a3d4cde9db260363a1b51d45c6374aa49e01e6331324eb95ba704`.
The four unchanged dependency inputs below were recovered from the existing
`seed-retry-runtime/` directory in artifact **10285621024**. Its overall runtime
is historical: do NOT substitute it for the current full baseline in this receipt.
All dependency Git blobs are enforced by the runner before import.

From this same canonical directory, using new scratch output paths:

```bash
# CURRENT is the exact reviewed b952 runtime; BUNDLE is the recovered
# seed-retry-runtime directory. OUT must not already exist.
python repair_seed_funding_prefix.py "$CURRENT" "$OUT"
python check_seed_prefix_market_controls.py \
  --runtime "$CURRENT" --candidate "$OUT" \
  --candidate-git-blob cbeb7f09914c351a99cb5f0970c14a7bea7cb029 \
  --engine "$BUNDLE/checks/reference/engine/kaggriculture.py" \
  --budget "$BUNDLE/reference/integrated-selected/alder/seed_budget.py" \
  --funding "$BUNDLE/reference/titan-current/seed_funding.py" \
  --suffix "$BUNDLE/plant_suffix.py"
```

Repeat with `python -O`. Append `--predecessor` to either command to run the same
new expectations against the old method: exit 1 is expected. Missing or mismatched
pinned inputs exit 2 before testing; successful tests exit 0. A newer reviewed
whole-runtime composition may produce another candidate file hash: audit it
before updating `--candidate-git-blob`; do not change the fixed dependency or
baseline-method pins merely to obtain a green result.

The checker executes only a locally supplied reviewed candidate method. Its hash
argument is a reproducibility check, not a sandbox or substitute for source review.
There are no file writes, network calls or subprocesses in this checker. Canonical
placement alone does not wire or enable this repair in production.
