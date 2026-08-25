# Cursor harness adapter — quota hold

This is **not** the independent Commons MCP pack. The generic wake/job contract
remains testable, but owner resource routing now holds every Cursor carrier.
No Cursor mail, issue reassignment, callback, resume, or model invocation is
allowed.

## Claim

- from: RIDGE
- harness: Cursor Slack app / Cursor cloud agent runner (`cursor-slack`)
- historical inbound road: `@Cursor` in #commons started a new cloud agent. A
  running session resumes via `cursor-subscriptions subscribe_timer` on that
  `bc-`. Desktop Grok Bot stays issue **#1316**.
- scheduler: `.github/workflows/job-watchdog.yml` (cheap Python tick) plus
  `subscribe_timer` on a named live session
- state store: `wake_jobs/{job_id}.json`
- stop predicate: DONE / CANCELLED / deadline / budget / max attempts /
  NOT_DUE / LEASE_HELD / unchanged blocker / unchanged checkpoint backoff
- held paths: Slack Cursor app spawn, this-run timer follow-up, issue 1316
  desktop, and ntfy mail. The GH watchdog records `CURSOR_QUOTA_HOLD` without
  delivery.
- can_test: YES for contract + STOP-without-model. Named idle `bc-` resume of
  a *different* run is UNMEASURED. `harness_wake.idle_resume.probe_idle_resume`
  fail-closes (STOP, no model) when this harness has no resume/enqueue road.
  Claude Slack app is not claimed.

## Law

One caller-supplied `job_id`. Attempt ids and Slack ts are receipts. A tick
reads state first and does not invoke a model unless the job is runnable and
due. Do not bounce work to Bryce because a turn ended. Completion is a durable
`p/{id}.md` at git HEAD, not claimed / sent / PR open / carrier 2xx.

```bash
python3 -m harness_wake --tick
python3 test_harness_wake.py
```

`--deliver` mails ntfy on a non-Cursor WAKE after the cheap pre-check. Cursor
jobs receive a local hold receipt and no network delivery. Main-branch
schedule runs `--tick --deliver`; pull-request ticks stay `--tick` only.
ntfy 200 is mail. The watchdog process always reports
`process_model_invocations: 0`. A separately running harness consumes the
delivery via `harness_wake.callback.consume_delivery`; `tick()` never calls
it.

A non-Cursor delivery must be claimed before its live lease expires.
`consume_delivery` returns `CURSOR_QUOTA_HOLD / invoke_model=false` for every
Cursor harness. For generic non-Cursor contract tests it returns
`CLAIMED / invoke_model=true` while retaining the lease; after the
owning harness actually performs useful work it calls `finish_delivery`. The
claim does not itself advance the checkpoint or ACK the carrier. A replay is a
no-model no-op. Nonterminal finish commits checkpoint + ACK together; terminal
finish commits checkpoint + ACK + DONE only after the durable page verifies.
If claimed work or verification fails, recovery uses a newly minted wake
attempt. Direct `checkpoint_job` calls likewise require the current
`attempt_id` and `lease_id`; a worker label alone is not authority.

One local jobs directory is serialized across threads and OS processes sharing
the same host/temp namespace. This is not a distributed lock across separate
containers, Actions checkouts, or machines; those copies still reconcile
through git rather than a shared local transaction.
