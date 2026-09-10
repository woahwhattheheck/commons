# Provenance — first league panel

- Games played: 2026-09-10 ~19:06–19:13 UTC through the unmodified
  reference evaluator (`reference/evaluator/evaluate.py`) with the
  pinned official engine (`reference/engine/`, git-blob SHA-1 verified
  by the evaluator).
- Play wall time: ~384 s, 4 parallel evaluator shards
  (6 shards: 2 contestants x 3 seed subsets), 48/48 cells complete.
- Aggregation/ledger/alarms resumed at 2026-09-10 19:13:42 UTC from the
  saved shard reports (`run_league.py --resume`); `report.json`
  `wall_seconds` records the aggregation pass (0.0 s), not the play
  pass. Play timing above is the real match time.
- Field (reduced): 2 contestants (canonical v3-kestrel-capital-execution
  + registered challenger v3-final-crop-binding) x 4 opponents
  (official_pass, official_random, official_starter, soil_rain) x 3 seeds
  (2611031001-2611031003) x 2 seats, identical cells.
- Contestant bootstraps in `staging/` import the real candidate
  entrypoints by absolute path; candidate sources were not copied or
  edited. Fingerprints in `report.json`.
- Alarms: 0 (all joint (opponent, seat) own-cash strata nonnegative).
