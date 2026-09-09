# v25 sim runner

Faithful sharded runner for the official Kaggriculture engine (1.32.7).
The upstream evaluator is never edited; each shard is an independent
evaluator process over a disjoint seed subset. Verified byte-identical
to serial execution (36/36 games, workers 1 vs 8).

    bash tools/v25_sims/setup.sh                      # once
    bash tools/v25_sims/run.sh <SEED_START> <COUNT> <OUTDIR>

Outputs `SUMMARY.json` (aggregate W/T/L + mean margin per opponent) and
`GAMES.jsonl` (one line per game) in OUTDIR.
