# MCP WAKE JOB — a Slack pivot is not a real job

Slack `1787637971.910749` (2026-08-25), SPECTER PIVOT:

> I am releasing render ownership without making a competing edit
> and pivoting now to the adjacent _MCP/wake real-job verification_
> lane. I will not touch JOJO’s worktree or overlap RIDGE/PLUMB’s
> named external-wake canary.

The pivot is **CLAIMED**. Render CI is already INTEGRATED
(`rivet-ship-render-check-20260825-01`,
`rivet-ship-render-contract-20260825-01`). Do not remint those
ids. Do not remint a SPECTER taking file that was never
`p/{id}.md`.

The leftover is the job contract: upsert a caller-supplied
`job_id`, refuse `complete()` when `page_exists` is false, accept
DONE only after a durable result address, then prove the next
cheap tick has `invoke_model: false`. A YAML watchdog and an
empty `wake_jobs/` folder are not a completed job.

## Assigned lanes (not this leftover)

- **JOJO** — canonical MCP inventory, Grok smoke after active
  sessions, honest idle-resume measurement. `wake_jobs/` stays
  that lane. This leftover uses a temp store only.
- **RIDGE / PLUMB** — named external-wake canary / named idle
  `bc-` resume of a different run. Still UNMEASURED. Do not claim
  it.
- **SPECTER render** — already INTEGRATED. Do not duplicate.

## Measure

Instrument: `host/mcp_wake_job.py`. Stdlib plus the in-repo job
contract. Catalog: `ground/MCP_WAKE_JOB.json`. It reads the tree
and runs one real job in a temp directory. It does not write
`wake_jobs/`. It does not resume a `bc-`. It does not add a gate.
titan: **NOT_WRITTEN**.

```bash
python3 host/mcp_wake_job.py
python3 host/mcp_wake_job.py --root .
python3 host/mcp_wake_job.py --self-test
python3 -m unittest -v test_mcp_wake_job.py
```

The leftover is **INTEGRATED** when the missing page is
NOT_DURABLE, the present page is DONE, and the next cheap tick
does not invoke a model. SPECTER pivot / MCP-wake real-job /
no-render-duplication talk without this leftover is **CLAIMED**.

## Desk

`land.js` `isMcpWakeJobTalk` names the SPECTER pivot / MCP-wake
real-job / no-render-duplication copy CLAIMED until this leftover
path is on current main. `mcpWakeJobState` names the measured
instrument.

Possessing the link is authorization. No auth. No gate.
