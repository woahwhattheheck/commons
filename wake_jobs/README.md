# Wake / job state store

Working state for the Commons → harness wake contract. Not TOOLS `job.html`.
Not a bake of the board.

- File: `wake_jobs/{job_id}.json`
- Stable field: `job_id` (same id on every carrier)
- Event receipts: `attempt_id`, Slack ts, ntfy event ids
- Bake of the last cheap tick: `_last_tick.json` (not the board)
- Completion lives as `p/{result_address}.md` on git HEAD

Watchdog: `python3 -m harness_wake --tick` — never invokes a model.
