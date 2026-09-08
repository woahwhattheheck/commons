# Full-game league consumer

`run_league.py --config /absolute/path/job.json` composes the existing official
evaluator with compressed transition records, complete call/RPC timing samples,
per-game checkpoints, and a read-only joint-action audit. Each game runs fresh
isolated actors. The initial eight cells complete before the remaining cells
launch. A cell is never retried automatically.

Configuration fields: `candidate`, `opponents` (label to callable path), `cells`
(objects with `id`, `seed`, `seat`, `opponent`), `engine`, `loader`, `evaluator`,
`output`, `rng_seed`, `action_timeout`, `startup_timeout`, `game_timeout`, `jobs`.
Use absolute paths, freeze the complete input closure, and keep generated records
in the designated private destination. Both seats are separate executions of the
same seed, not independent environment draws.

`duplicate_harvest_targets(observation, action)` reports co-located actors
assigned the same harvest target using the player's visible observation. It
does not mutate a route or estimate the value of another action.

Run the synthetic engine checks with:

```sh
python test_selected_action_audit.py --loader-path /path/loader.py --engine-dir /path/engine
python test_run_league.py
```

The existing engine and evaluator retain their upstream licenses. No competitor
source, recorded match data, or generated job configuration is included here.
