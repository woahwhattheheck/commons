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
render-contract leftover). Do not remint those. Do not remint a
JOJO taking with no `p/{id}.md`.

DEMON Slack `1787635487.642039` assigned JOJO the leftover this
desk now ships:

1. one canonical MCP inventory
2. one Grok smoke after active sessions (honest: UNMEASURED here)
3. an honest idle-resume measurement (fail-closed UNMEASURED)

## Measure

Instrument: `host/mcp_wake.py`. Stdlib + in-repo JobStore /
`probe_idle_resume`. Catalog: `ground/MCP_INVENTORY.json` and
`ground/MCP_WAKE.json`. It does not write `wake_jobs/{id}.json`.
It does not mutate `~/.grok`. titan: **NOT_WRITTEN**.

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
- **UNMEASURED** — census not read, or Grok/idle-resume honestly
  not exercised. Absence is not stillness
- **NOT_LANDED** — leftover incomplete, or the probe invented a
  live resume / wrote `wake_jobs/`

Talk that is a collision check, a hold, `jojo-visual-ci`, or
MCP/wake real-job verification without this leftover is
**CLAIMED**.

Possessing the link is authorization. No auth. No gate.
