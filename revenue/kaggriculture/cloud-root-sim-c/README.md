# ROOT-SIM-C

`build_jobs.py` freezes the predeclared 384-game grid for operation
`titan-root-sim-c-20260908-1345`. It writes only configurations for the existing
`cloud-ultra-league/run_league.py`; it is not an evaluator or game harness.

`resume_failed.py` creates an explicit lower-concurrency continuation from an
existing job and checkpoint. Completed cells are excluded, failed attempts stay
in the original output, and replay cell IDs receive a visible suffix.

`analyze_results.py` requires one complete result for every controller ×
opponent × seed × seat cell. It reports W/D/L, final cash, paired margin and
seed-level deterministic bootstrap intervals. Raw trajectories and detailed
private observations are intentionally excluded.

See `RESULTS.md` and `RESULTS.json` for the completed shard.
