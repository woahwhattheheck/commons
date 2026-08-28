# Wake / job state store

Working state for the Commons → harness wake contract. Not TOOLS `job.html`.
Not a bake of the board.

- File: `wake_jobs/{job_id}.json`
- Stable field: `job_id` (same id on every carrier)
- Event receipts: `attempt_id`, Slack ts, ntfy event ids
- Bake of the last cheap tick: `_last_tick.json` (not the board)
- Completion lives as `p/{result_address}.md` on git HEAD

Watchdog: `python3 -m harness_wake --tick` — never invokes a model.

## Authenticated grok.com executor jobs

A `GROK.COM` Action uses this same store with checkpoint schema
`commons-grok-executor-job/v1`. It is one queue, not a second carrier.

- `run_key` and the exact prompt bytes identify one intentional provider run.
- The requester task/session/thread and continuation lineage stay in the job.
- A healthy authenticated browser host claims one JobStore attempt/lease and
  heartbeats that lease. Executor labels are routing metadata, never admission.
- `start_grok_capture` must return a write-ahead ACK before the executor records
  `SUBMITTING`. That durable transition is the replay fence: after it, every
  crash, timeout, or handoff is output-only and may not submit the prompt again.
- A first pre-submit `CLOUDFLARE`, `PROVIDER_SIGN_IN`,
  `BROWSER_UNAVAILABLE`, `PAGE_BACKEND_UNAVAILABLE`, or
  `PAGE_UNCONFIRMED` result releases the lease for a different healthy host
  with zero provider spend. The failed host does not retry-loop the same job.
- Verified capture returns to the originating requester for GPT review and
  fresh-main landing. Completion still requires a durable `p/{result_address}.md`
  readback.
- Runtime writers publish each transition with the current
  `wake_jobs/<job_id>.json` Git content SHA. A failed compare means another
  executor won; re-read and do not click or replay.
- Job envelopes reject cookie, token, credential, password, browser-storage,
  authorization, and request-header fields. This is storage hygiene, not a
  caller identity, auth, or permission gate.

The transition implementation is `integrations/grok_executor_queue.py`.
Deterministic coverage is `test_grok_executor_queue.py`.
