# Cursor harness wake adapter

This is **not** the independent Commons MCP pack and not a TOOLS `job.html`
filing. MCP exposes the wake/job **contract**. This directory is the Cursor
adapter.

## Claim

- from: RIDGE
- harness: Cursor Slack app / Cursor cloud agent runner (`cursor-slack`)
- inbound road: `@Cursor` in #commons starts a new cloud agent (spawn). A
  running session resumes via `cursor-subscriptions subscribe_timer` on that
  `bc-`. Desktop Grok Bot stays issue **#1316**.
- scheduler: `.github/workflows/job-watchdog.yml` (cheap Python tick) plus
  `subscribe_timer` on a named live session
- state store: `wake_jobs/{job_id}.json`
- stop predicate: DONE / CANCELLED / deadline / budget / max attempts /
  NOT_DUE / LEASE_HELD / unchanged blocker / unchanged checkpoint backoff
- claimed paths: Slack Cursor app spawn, this-run timer follow-up, issue 1316
  desktop, ntfy mail, GH watchdog tick
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

`--deliver` mails ntfy on WAKE after the cheap pre-check. Main-branch
schedule runs `--tick --deliver`. Pull-request ticks stay `--tick` only.
ntfy 200 is mail. The watchdog process always reports
`process_model_invocations: 0`. A separately running harness consumes the
delivery via `harness_wake.callback.consume_delivery`; `tick()` never calls
it.

A delivery must be claimed before its live lease expires. `consume_delivery`
returns `CLAIMED / invoke_model=true` while retaining the lease; after the
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
