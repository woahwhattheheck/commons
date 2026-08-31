# Cursor harness adapter — quota hold

This is **not** the independent Commons MCP pack. The generic wake/job contract
remains testable, but owner resource routing now holds Slack @Cursor spawn,
ntfy Cursor mail, subscribe_timer, and issue 1316. Cheap ticks never invoke a
model. Named idle `bc-` resume of a *different* run stays UNMEASURED.

Sibling: host-neutral **peer wake bus** in `peer_wake/`. ChatGPT/Claude doorbells
are out of this land. Do not remint this adapter. Law: [ground/WAKE_LOOP.md](../ground/WAKE_LOOP.md).

## Claim

- from: RIDGE (lane) / SETH (live inbound)
- harness: Cursor / Grok Bot (`cursor-grokbot`)
- live inbound: `grokbot_seth` — desktop Cursor/Grok Bot Seth launches or
  replies to a named Cursor cloud agent (`bc-…`) for a named leftover. A leftover
  record on git HEAD is upserted into `wake_jobs/{job_id}.json` when missing so
  job-watchdog can tick it without Bryce re-pinging.
- historical inbound (held): `@Cursor` in #commons; `subscribe_timer` on this
  `bc-`; issue **#1316** desktop doorbell; ntfy Cursor mail.
- scheduler: `.github/workflows/job-watchdog.yml` (cheap Python tick; never a
  model). `python3 -m harness_wake --tick` now also ingests Cursor leftovers.
- state store: `wake_jobs/{job_id}.json`
- stop predicate: DONE / CANCELLED / deadline / budget / max attempts /
  NOT_DUE / LEASE_HELD / unchanged blocker / unchanged checkpoint backoff
- held paths: Slack Cursor app spawn, this-run timer follow-up, issue 1316
  desktop, and ntfy mail. The GH watchdog records `CURSOR_QUOTA_HOLD` without
  delivery. Do not lift those roads here.
- can_test: YES for contract + leftover ingest + STOP-without-model. Named idle
  `bc-` resume of a *different* run is UNMEASURED.
  `harness_wake.idle_resume.probe_idle_resume` fail-closes (STOP, no model).
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
