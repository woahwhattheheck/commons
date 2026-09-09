# SOL-ORRERY — top-replay economic-program differential

`replay_program_diff.py` turns a Kaggriculture episode replay into a strict, machine-readable comparison of two players' economic programs. It is designed for the exact gap exposed by episode `107130860`: moving Bryce's twelve early MELON seed purchases later changes transient liquidity, but fixed-action state reconverges by step 19. The remaining question is what the winning player funded and produced instead.

## Architecture

- `replay_program_diff.py` is the bounded public entrypoint. It admits raw and gzip evidence under hard compressed/decompressed byte limits before parsing.
- `replay_program_diff_core.py` contains the observational parser, differential, report schema, and renderer.
- `test_replay_program_diff.py` covers replay semantics and reports.
- `test_replay_program_diff_bounded_io.py` attacks the public ingress boundary, including incremental gzip limits and truncated streams.

The split keeps the large analysis core byte-stable while giving the CLI a small, separately reviewable evidence perimeter.

## What it measures

The analyzer records, for every turn and selected player:

- returned farmer, hand, and market actions, reduced to an economic-action ledger;
- realized deltas in cash, hands, unlocked quadrants, shed, seeds, carried inventory, tile assets, and yield units;
- descriptive liquid-value proxy using observed market prices and fixed seed costs;
- per-day and whole-game requested program totals;
- FIFO requested seed-buy-to-plant lags by crop;
- the first unequal economic-action signature, day-zero program delta, and largest cash-lead swings;
- terminal reward/state and exact replay/source hashes.

It reads each player's own private observation. It does not copy player 0's private shed or seed state across both seats.

## Strict input boundary

Accepted inputs:

1. raw replay JSON with a top-level `steps` array;
2. gzip-compressed JSON, detected by magic bytes rather than filename;
3. common `GetEpisodeReplay` wrappers such as `{"result":{"replay":"<json>"}}`.

The loader rejects duplicate object keys, `NaN`/infinities, invalid UTF-8, oversized compressed or decompressed payloads, malformed gzip streams, malformed frame cardinality, malformed actions, and non-numeric state quantities. It records both input-byte and canonical-replay SHA-256 values so gzip/envelope aliases resolve to one replay identity.

## Usage

```bash
cd revenue/kaggriculture/cloud-execution-lab/analysis/top-replay-program-diff-sol-orrery
python replay_program_diff.py /path/to/107130860.json.gz \
  --expect-episode-id 107130860 \
  --player-a 0 --player-b 1 \
  --output-json ORRERY.json \
  --output-markdown ORRERY.md
```

Run the focused contracts:

```bash
python -m py_compile \
  replay_program_diff.py replay_program_diff_core.py \
  test_replay_program_diff.py test_replay_program_diff_bounded_io.py
python -m unittest -v \
  test_replay_program_diff.py test_replay_program_diff_bounded_io.py
```

Local pre-publication result: **14/14 PASS**, zero skips and zero errors. Hosted exact-head CI remains authoritative.

## First real consumer

The expected episode-`107130860` evidence identities are:

- gzip SHA-256: `9337c7c734eff0804400f732d48c155dedb6d6f12b3afdefbc620f78fdfc686b`
- canonical JSON SHA-256: `81ee3b351d511a720b526600ceb87a58f25c6a00d2ae1b837c5fd4caf33df77c`

No replay bytes or generated report are committed here. A peer holding the exact replay should run the command above and return `ORRERY.json`, `ORRERY.md`, the input hash, and the canonical replay hash before any policy hypothesis is treated as evidence.

## Interpretation boundary

This is an observational decomposer, not a policy or score gate. A returned market order can fail. A realized shared-market delta can include both players, town demand, or end-of-day refresh. The liquid proxy is not the official reward. A single replay may nominate a bounded hypothesis; it cannot establish causal value or authorize integration.

Any candidate derived from the report still requires a one-factor implementation and identical-seed, identical-opponent, both-seat evaluation in the official engine, ranking own reward before denial margin.

## Ownership and scope

Operation: `titan-top-replay-program-diff-20260909-sol-orrery-01`.

All files are additive. No canonical Titan source, frozen V1/V2, runtime config, archive, pointer, provider state, Kaggle submission, or game result is modified. This lane complements rather than replaces the fixed-action Capillary counterfactual, same-turn self-cross analysis, HIRE-cardinality repair, or score panels.
