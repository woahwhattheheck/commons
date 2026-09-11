# #12390 raw-score custody reproduction

This is an **independent deterministic reproduction**, produced after the #12390 evidence review exposed that the parent PR preserved derived margins but not the raw evaluator score arrays. It is not represented as the publisher's original stdout.

`RAW-REPRO-20260911.json` binds the exact Slack package (`F0C18AXAL04`), outer/inner archive hashes, executed wrapper hash, package source hashes, and pinned engine hashes. It preserves the raw per-cell `[seed, candidate_seat, score0, score1]` arrays for:

- low seeds 101..108: L3 factor vs Arlene;
- exact V3.1 vs Arlene control on the same cells;
- L3 factor directly vs exact V3.1 on the same cells;
- frozen seeds 2611151001..2611151008: L3 vs Arlene and exact V3.1 control;
- exact V3.1 vs itself on seed101.

All source evaluator runs completed with no failures before these compact score records were extracted. A dedicated seed102 replay was then executed one candidate seat at a time so telemetry is durable per cell: each seat records 70 callback rows, 30 causally active suppressed reservations, 240 avoided SELL units, and 240 matching debt units. Together that reproduces the published 60 causal / 480 quantity claim without conflating matching action/debt bookkeeping as 960 economic units.

Run `python verify_raw_repro.py`. It derives seat-aware margins from the score arrays, computes paired ΔM for Arlene cells, recomputes every published cell and summary in `L3-OPPONENT-FLIP-20260911.json`, verifies the seed101 self-play tie, and verifies the per-seat seed102 telemetry aggregates.

No gameplay, overlay, default, package, evaluator, opponent, or Kaggle behavior is changed by these evidence files.
