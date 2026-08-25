# Tokens — harness wake loops

Bryce 2026-08-22: stop making him wake, reassign, or re-ping work a peer already owns. Each harness builds a bounded inbound wake road from Commons into its own runtime.

**Contract (independent Commons MCP):** one caller-supplied `job_id`. Attempt ids / Slack ts are receipts. Durable job state: owner_claim, harness, objective, checkpoint, next_wake_at, backoff, deadline, max attempts, budget, completion predicate, result address. `tick_job` reads state first. STOP without a model when DONE, CANCELLED, deadline/budget exhausted, not due, lease held, or an unchanged external-authority blocker.

**Cursor adapter:** sibling `harness_wake/`, retained as historical provenance and mechanical containment. Slack spawn, subscription resume, ntfy, callbacks, model invocation, and desktop issue **#1316** are held. Cheap watchdog: `.github/workflows/job-watchdog.yml` — held before lease acquisition, never a model.

Named idle `bc-` resume of a different run is UNMEASURED. Claude Slack app is disconnected; do not claim it. Action Pad stays zero-auth.

Cite `ridge-cursor-wake-loop-20260822-01`. Do not remint `latch-dir2-cursor-wake-20260819-01`.
