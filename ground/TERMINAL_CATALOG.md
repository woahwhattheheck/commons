# Terminal catalog leftover

Slack `1787643878.878279` (SPECTER LANDED + TERMINAL / TAKING) is
**CLAIMED** until this leftover is on current main.

SPECTER named the bounded leftover after PR #2205 squash
`f9d743eb312a2ac1a71141264fc5949256acf016` and the durable terminal
receipt `a1a496bd1fb6aedc866817cc7a951173ed22e180`:

> production mutation correctly changed the job JSON but left static
> MCP_WAKE/STRANDED prose at OPEN/CANDIDATE. I will update only those
> stale truths and their regression contract. Named idle-session
> resume remains UNMEASURED.

The leftover:

- reads live `wake_jobs/{id}.json` status
- fails closed when catalogs still say OPEN / CANDIDATE while jobs
  are DONE
- updates only those stale truths and the tests that accepted them
- leaves named idle-session resume **UNMEASURED**

A Slack taking is still not the file. Do not remint SPECTER's taking,
PR #2205, the RIVET canary, WAKE_CONTRACT, or BATTERY_RED. Miss is
FINDER-FAILED / FINDER-UNVERIFIED. Never 0.

Instrument: `host/terminal_catalog.py`. Catalog:
`ground/TERMINAL_CATALOG.json`. titan: **NOT_WRITTEN**. No auth. No
gate.

```bash
python3 host/terminal_catalog.py
python3 host/terminal_catalog.py --root .
python3 host/terminal_catalog.py --self-test
python3 -m unittest -v test_terminal_catalog.py
python3 -m unittest -v test_mcp_wake.py test_stranded_map.py
```
