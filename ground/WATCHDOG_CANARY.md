# WATCHDOG CANARY — an empty wake_jobs folder is not utilization

Slack `1787639656.279039` (2026-08-25), SPECTER independent ship receipt:

> The production oracle is now real but remains unutilized by a
> durable job canary; do not call that a completed named-session
> resume.
>
> Direct non-search inventory: `wake_jobs/` contains only
> `.gitignore` + `README.md`, no real job JSON.

The HEAD oracle leftover is already **INTEGRATED**
(`rivet-ship-watchdog-oracle-20260825-01`, ancestor `80830403`).
Do not remint it. A YAML watchdog plus an empty `wake_jobs/`
folder is still not utilization. Named idle `bc-` resume stays
**UNMEASURED**.

## Assigned lanes (not this leftover)

- **SPECTER watchdog oracle** — already INTEGRATED. One lazy
  public `GitTruth` HEAD pin per watchdog run.
- **MCP/wake temp-store leftover** — already INTEGRATED
  (`rivet-ship-mcp-wake-job-20260825-01`). That leftover
  refuses to write `wake_jobs/`. This leftover is the missing
  durable file.
- **JOJO** — MCP inventory, Grok smoke, honest idle-resume.
  Do not take those.
- **RIDGE / PLUMB** — named external-wake canary / named idle
  `bc-` resume of a different run. Still UNMEASURED. Do not
  claim it.

## Measure

Instrument: `host/watchdog_canary.py`. Stdlib plus the in-repo
watchdog. Catalog: `ground/WATCHDOG_CANARY.json`. It reads the
tree and ticks a temp copy of the durable canary against a
SHA-pinned oracle. It does not resume a `bc-`. It does not add
a gate. titan: **NOT_WRITTEN**.

```bash
python3 host/watchdog_canary.py
python3 host/watchdog_canary.py --root .
python3 host/watchdog_canary.py --self-test
python3 -m unittest -v test_watchdog_canary.py
```

The leftover is **INTEGRATED** when `wake_jobs/` holds a real
job JSON, the known-present result is DONE / STOP / zero mail /
zero model on one SHA, and the unique known-absent control
stays runnable. SPECTER ship-receipt / unutilized-oracle /
no-real-job-JSON talk without this leftover is **CLAIMED**.

## Desk

`land.js` `isWatchdogCanaryTalk` names the SPECTER independent
ship receipt / unutilized durable job canary / no-real-job-JSON
copy CLAIMED until this leftover is on current main.
`watchdogCanaryState` names the measured instrument.

Possessing the link is authorization. No auth. No gate.
