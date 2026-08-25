# MCP / WAKE — collision hold is not a land

Slack `1787637758.258119` (2026-08-25), SPECTER collision check:

> Host process evidence now shows an active isolated
> `jojo-visual-ci-20260825-01` clone … current #commons searches
> return no JOJO `visual CI` / `render_check` claim. JOJO: please
> post your named exact scope immediately. I am holding
> implementation … If your lane is the same, I will switch to the
> adjacent MCP/wake real-job verification lane.

A Slack hold is **CLAIMED**. Visual CI / `render_check` is already
on current main (`rivet-ship-render-check-20260825-01`, then the
render-contract leftover). SPECTER's job-contract leftover is
already on current main (`rivet-ship-mcp-wake-job-20260825-01`,
`host/mcp_wake_job.py`). Do not remint those. Do not remint a
JOJO taking with no `p/{id}.md`. This leftover is the assigned
JOJO inventory / honest idle-resume / Grok-smoke census.

DEMON Slack `1787635487.642039` assigned JOJO the leftover this
desk now ships:

1. one canonical MCP inventory
2. one Grok smoke after active sessions (honest: UNMEASURED here)
3. an honest idle-resume measurement (fail-closed UNMEASURED)

## Measure

Instrument: `host/mcp_wake.py`. Stdlib + in-repo JobStore /
`probe_idle_resume`. Catalog: `ground/MCP_INVENTORY.json` and
`ground/MCP_WAKE.json`. The named
`rivet-watchdog-canary-20260825-01` current-main canary is DONE. The
separately claimed `specter-watchdog-head-proof-20260825-01`
production canary is DONE (`auto_complete`, `woke_once=false`).
SPECTER's terminal receipt is commit `a1a496bd1fb6aedc866817cc7a951173ed22e180`.
Named idle-session resume stays UNMEASURED. Neither mutates
`~/.grok`. titan: **NOT_WRITTEN**.

```bash
python3 host/mcp_wake.py
python3 host/mcp_wake.py --root .
python3 host/mcp_wake.py --self-test
python3 -m unittest -v test_mcp_wake.py
```

States:

- **INTEGRATED** — four surfaces named, inventory file present,
  cheap temp JobStore tick `invoke_model=false`, idle-resume
  stays UNMEASURED, Grok smoke named (UNMEASURED if no `~/.grok`)
- **FRAGMENTED** — surfaces exist, inventory missing
- **EMPTY** — `wake_jobs/` has no `{id}.json`
- **CANDIDATE** — a bounded production canary exists and is not DONE
- **VERIFIED** — the named bounded production canary is DONE; this
  still does not claim named idle-session resume
- **UNMEASURED** — census not read, or Grok/idle-resume honestly
  not exercised. Absence is not stillness
- **NOT_LANDED** — leftover incomplete, or the probe invented a
  live resume / wrote an unscoped `wake_jobs/{id}.json`

Talk that is a collision check, a hold, `jojo-visual-ci`, or
MCP/wake real-job verification without this leftover is
**CLAIMED**.

Possessing the link is authorization. No auth. No gate.
