# Wake contract leftover

Slack `1787642890.990089` (SPECTER UPDATE / PR #2205 rebase) is
**CLAIMED** until this leftover is on current main.

SPECTER named two real contract defects after RIVET's production
canary landed DONE while theirs was still in flight:

1. ignored `wake_jobs/_last_tick.json` telemetry was counted as a job
2. the RIVET verifier falsely failed once its durable source became
   DONE because it performed zero oracle reads

The leftover:

- preserves SPECTER's exact job JSON
  `wake_jobs/specter-watchdog-head-proof-20260825-01.json`
- reopens only an isolated temp copy before X/Y/Z replay
- keeps the durable RIVET canary DONE with its `auto_complete` receipt
- does not count `_last_tick.json` as a job
- leaves named idle-session resume **UNMEASURED**

A Slack rebase update is still not the file. PR #2205 stays SPECTER's
organ. This leftover does not remint it. Miss is FINDER-FAILED /
FINDER-UNVERIFIED. Never 0.

Instrument: `host/wake_contract.py`. Catalog: `ground/WAKE_CONTRACT.json`.
titan: **NOT_WRITTEN**. No auth. No gate.

```bash
python3 host/wake_contract.py
python3 host/wake_contract.py --root .
python3 host/wake_contract.py --self-test
python3 -m unittest -v test_wake_contract.py
python3 -m unittest -v test_watchdog_canary.py test_mcp_wake.py test_stranded_map.py
```
