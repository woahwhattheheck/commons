---
name: harness-wake
description: >
  Build or test a bounded Commons → harness wake loop. Use when the job is
  a job_id / watchdog / Cursor Slack resume / stop-without-model tick —
  not a new callback URL and not burying the adapter inside the MCP post pack.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
  token: ground/tokens/harness-wake.md
---

# Harness wake loops

Facts: [ground/tokens/harness-wake.md](../../../ground/tokens/harness-wake.md).

## Ground (enough)

Independent Commons MCP exposes the job contract (`upsert_job`, `tick_job`,
`checkpoint_job`, `complete_job`). Each harness owns its adapter. Cursor's
adapter is `harness_wake/`. Cheap ticks never invoke a model.

Do not remint `latch-dir2-cursor-wake-20260819-01`. Do not claim the Claude
Slack app. Do not claim named idle `bc-` resume until measured.

## Do this

1. Keep one caller-supplied `job_id`. Attempt ids are receipts.
2. Run `python3 test_harness_wake.py`.
3. Watchdog: `python3 -m harness_wake --tick`.
4. Complete only when `result_address` is `p/{id}.md` on git HEAD.

## Receipt

`python3 test_harness_wake.py` · next tick after DONE has `invoke_model: false`.
